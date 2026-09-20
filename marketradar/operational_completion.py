from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .application import transition, record_revenue, verify_payment
from .goal_completion import authorize_action, execute_authorized, workflow_event
from .operations import source_application_gate


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


class OperationalError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    mode: str
    domains: tuple[str, ...]
    endpoint: str | None = None
    method: str = "POST"
    token_env: str | None = None
    headers: dict[str, str] | None = None
    body_template: dict[str, Any] | None = None
    expected_status: tuple[int, ...] = (200, 201, 202, 204)
    timeout: float = 20.0
    enabled: bool = False


class ProviderRegistry:
    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path
        self.providers: dict[str, ProviderConfig] = {}
        if config_path and config_path.exists():
            self.load(config_path)

    def load(self, path: Path):
        raw = json.loads(path.read_text(encoding="utf-8"))
        for item in raw.get("providers", []):
            p = ProviderConfig(
                name=item["name"], mode=item.get("mode", "GUIDED_BROWSER"),
                domains=tuple(x.lower() for x in item.get("domains", [])),
                endpoint=item.get("endpoint"), method=item.get("method", "POST").upper(),
                token_env=item.get("token_env"), headers=item.get("headers", {}),
                body_template=item.get("body_template", {}),
                expected_status=tuple(item.get("expected_status", [200,201,202,204])),
                timeout=float(item.get("timeout", 20)), enabled=bool(item.get("enabled", False)),
            )
            self.providers[p.name] = p

    def resolve(self, source: str, url: str) -> ProviderConfig | None:
        host = (urlparse(url).hostname or "").lower()
        if source in self.providers and self.providers[source].enabled:
            p = self.providers[source]
            if p.domains and not any(host == d or host.endswith("." + d) for d in p.domains):
                raise OperationalError("PROVIDER_SOURCE_DOMAIN_MISMATCH")
            return p
        for p in self.providers.values():
            if p.enabled and (not p.domains or any(host == d or host.endswith("." + d) for d in p.domains)):
                return p
        return None


class AuthorizedHttpExecutor:
    """Provider-neutral authorized API executor. No credential discovery and no bypass."""

    def __init__(self, provider: ProviderConfig):
        self.provider = provider

    @staticmethod
    def _render(value, context):
        if isinstance(value, dict):
            return {k: AuthorizedHttpExecutor._render(v, context) for k, v in value.items()}
        if isinstance(value, list):
            return [AuthorizedHttpExecutor._render(v, context) for v in value]
        if isinstance(value, str):
            return re.sub(r"\{\{([A-Za-z0-9_.-]+)\}\}", lambda m: str(_lookup(context, m.group(1))), value)
        return value

    def execute(self, opportunity: dict, profile: dict, proposal: str, approval_id: str | None = None):
        if not self.provider.endpoint:
            raise OperationalError("PROVIDER_ENDPOINT_NOT_CONFIGURED")
        endpoint = urlparse(self.provider.endpoint)
        if endpoint.scheme not in {"https", "http"} or not endpoint.hostname:
            raise OperationalError("PROVIDER_ENDPOINT_INVALID")
        if self.provider.domains:
            endpoint_host = endpoint.hostname.lower()
            if not any(endpoint_host == d or endpoint_host.endswith("." + d) for d in self.provider.domains):
                raise OperationalError("PROVIDER_ENDPOINT_DOMAIN_MISMATCH")
        token = os.getenv(self.provider.token_env) if self.provider.token_env else None
        if self.provider.token_env and not token:
            raise OperationalError("AUTHORIZED_CREDENTIAL_NOT_CONFIGURED")
        context = {"opportunity": opportunity, "profile": profile, "proposal": proposal, "approval_id": approval_id or ""}
        body = self._render(self.provider.body_template or {"proposal": proposal}, context)
        headers = {"Content-Type": "application/json", **(self.provider.headers or {})}
        if token:
            headers.setdefault("Authorization", f"Bearer {token}")
        headers["Idempotency-Key"] = sha([self.provider.name, opportunity.get("id"), proposal])[:48]
        req = Request(self.provider.endpoint, data=json.dumps(body, ensure_ascii=False).encode(), headers=headers, method=self.provider.method)
        try:
            with urlopen(req, timeout=self.provider.timeout) as resp:
                payload = resp.read(2_000_000)
                status = int(resp.status)
                if status not in self.provider.expected_status:
                    raise OperationalError(f"UNEXPECTED_HTTP_STATUS:{status}")
                return {"status": "SUBMITTED", "provider": self.provider.name, "http_status": status,
                        "response_sha256": hashlib.sha256(payload).hexdigest(), "response_bytes": len(payload)}
        except HTTPError as exc:
            raise OperationalError(f"HTTP_ERROR:{exc.code}") from exc
        except URLError as exc:
            raise OperationalError(f"NETWORK_ERROR:{exc.reason}") from exc


def _lookup(context: dict, path: str):
    cur: Any = context
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part, "")
        else:
            return ""
    return cur


def prepare_browser_action(opportunity: dict, profile: dict, proposal: str) -> dict:
    """Prepare a human-approved browser action. It never submits silently."""
    return {
        "mode": "GUIDED_BROWSER",
        "url": opportunity["url"],
        "fields": {"proposal": proposal, "profile": profile},
        "requires_user_submit": True,
        "credential_source": "user_browser_session",
    }


def record_submission(c, opportunity_id: int, provider: str, result: dict, actor="system", workflow_state="SUBMITTED"):
    workflow_id = f"opportunity-{opportunity_id}"
    workflow_event(c, workflow_id, opportunity_id, "SUBMISSION_RESULT", workflow_state, result, attempt=int(result.get("attempt", 1)))
    c.execute("INSERT INTO operational_action_log(opportunity_id,provider,mode,status,external_ref,response_sha256,created_at) VALUES(?,?,?,?,?,?,?)",
              (opportunity_id, provider, result.get("mode", "API"), result.get("status", "UNKNOWN"), result.get("external_ref"), result.get("response_sha256"), utcnow()))
    c.commit()
    return result


def submit_with_approval(c, opportunity: dict, profile: dict, proposal: str, evidence_ids: list[int], policy_version="v6", actor="human", provider: ProviderConfig | None = None):
    target = opportunity["url"]
    gate = source_application_gate(c, opportunity.get("source"), int(opportunity["id"]))
    if not gate.get("allowed"):
        raise OperationalError(f"SOURCE_APPLICATION_LIMIT:{gate.get('reason')}:{gate.get('detail','')}")
    if opportunity.get("state") != "APPROVAL_PENDING":
        raise OperationalError("SUBMISSION_REQUIRES_APPROVAL_PENDING")
    action = "SUBMIT_APPLICATION"
    parameters = {"opportunity_id": int(opportunity["id"]), "provider": provider.name if provider else "GUIDED_BROWSER", "proposal_sha256": sha(proposal)}
    approval_id = authorize_action(c, action, target, parameters, evidence_ids, policy_version, actor, ttl_seconds=900)

    if provider and provider.mode == "AUTHORIZED_API":
        executor = AuthorizedHttpExecutor(provider)
        result = execute_authorized(c, approval_id, action, target, parameters, evidence_ids,
                                     lambda: executor.execute(opportunity, profile, proposal, approval_id))
        result["mode"] = "AUTHORIZED_API"
        result["provider"] = provider.name
        transition(c, int(opportunity["id"]), "SUBMITTED", actor="authorized_api")
        record_submission(c, int(opportunity["id"]), provider.name, result, workflow_state="SUBMITTED")
        return result

    result = execute_authorized(c, approval_id, action, target, parameters, evidence_ids,
                                lambda: prepare_browser_action(opportunity, profile, proposal))
    result["status"] = "READY_FOR_USER_SUBMIT"
    record_submission(c, int(opportunity["id"]), "browser", result, workflow_state="APPROVAL_PENDING")
    return result


def record_delivery(c, opportunity_id: int, artifact_path: str, checksum: str | None = None, evidence_url: str | None = None, actor="human"):
    p = Path(artifact_path)
    if not p.exists() or not p.is_file():
        raise OperationalError("DELIVERY_ARTIFACT_NOT_FOUND")
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    if checksum is not None and checksum.lower() != digest:
        raise OperationalError("DELIVERY_CHECKSUM_MISMATCH")
    row = c.execute("SELECT state FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
    if not row or row[0] != "IN_PROGRESS":
        raise OperationalError("DELIVERY_REQUIRES_IN_PROGRESS")
    try:
        c.execute("INSERT INTO delivery_evidence(opportunity_id,artifact_path,artifact_sha256,evidence_url,observed_at,actor) VALUES(?,?,?,?,?,?)",
                  (opportunity_id, str(p), digest, evidence_url, utcnow(), actor))
        transition(c, opportunity_id, "DELIVERED", actor=actor, commit=False)
        c.commit()
    except Exception:
        c.rollback()
        raise
    return {"status": "DELIVERED", "artifact_sha256": digest}


def record_payment(c, opportunity_id: int, amount: float, currency: str, payment_ref: str, network: str | None = None, txid: str | None = None, actor="human"):
    try:
        result = record_revenue(c, opportunity_id, amount, currency, utcnow(), payment_ref, network=network, txid=txid, verification_state="RECORDED_UNVERIFIED", commit=False)
        c.execute("INSERT INTO payment_verification(opportunity_id,payment_ref,status,network,txid,checked_at,actor) VALUES(?,?,?,?,?,?,?)",
                  (opportunity_id, payment_ref, "PENDING", network, txid, utcnow(), actor))
        c.commit()
    except Exception:
        c.rollback(); raise
    return {"status":"RECORDED_UNVERIFIED","digest":result}


def operational_gate(c, provider_registry: ProviderRegistry | None = None):
    provider_registry = provider_registry or ProviderRegistry()
    counts = {}
    for state in ("DISCOVERED","ELIGIBILITY_CHECK","RECOMMENDED","APPROVAL_PENDING","SUBMITTED","ACCEPTED","IN_PROGRESS","DELIVERED","PAID","REJECTED","EXPIRED","CANCELLED"):
        counts[state] = c.execute("SELECT COUNT(*) FROM opportunities WHERE state=?", (state,)).fetchone()[0]
    evidence = c.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
    live_sources = c.execute("SELECT COUNT(*) FROM sources WHERE verification_state='verified' AND source_verification_state='LIVE_CONFIRMED'").fetchone()[0]
    ready = c.execute("""SELECT COUNT(*) FROM opportunities o
                         WHERE o.application_ready=1 AND o.eligibility='EXECUTE'
                           AND o.state='APPROVAL_PENDING'
                           AND EXISTS (SELECT 1 FROM evidence e WHERE e.opportunity_id=o.id AND e.confidence>0 AND e.source<>'' AND e.url<>'' AND e.finding<>'')
                      """).fetchone()[0]
    providers = [p.name for p in provider_registry.providers.values() if p.enabled]
    return {
        "workflow_counts": counts,
        "evidence_records": evidence,
        "live_verified_sources": live_sources,
        "execution_ready_opportunities": ready,
        "configured_authorized_providers": providers,
        "external_runtime_gates": {
            "internet": "REQUIRES_REAL_RUNTIME",
            "provider_credentials": "REQUIRES_USER_AUTHORIZATION",
            "human_approval": "REQUIRED_FOR_ACTION",
            "delivery_artifact": "REQUIRED_FOR_DELIVERED",
            "payment_verification": "REQUIRES_EXTERNAL_EVIDENCE",
            "windows_execution": "REQUIRES_WINDOWS_HOST",
        },
    }

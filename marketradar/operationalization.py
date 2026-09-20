from __future__ import annotations

import hashlib
import json
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .application import record_revenue, transition, verify_payment
from .db import connect, sync_source_contracts
from .goal_completion import ensure_schema as ensure_goal_schema, run_goal_completion
from .economic_loop import ensure_schema as ensure_economic_schema, ensure_payment_poll_schema
from .pipeline import AcquisitionAttestation, Pipeline
from .source_registry import load_source_records


DISCOVERY_POOL_REFERENCE_TARGET = 500
LOCAL_FIXTURE_OPPORTUNITY_COUNT = 1000
FINAL_TOP_TARGET = 7
VISIBLE_DEFAULT_TARGET = 3


def _now():
    return datetime.now(timezone.utc).isoformat()


def _network_preflight(hosts=("remoteok.com", "weworkremotely.com", "www.python.org")):
    results = []
    for host in hosts:
        try:
            socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            results.append({"host": host, "dns": "OK"})
        except Exception as exc:
            results.append({"host": host, "dns": "ERROR", "error": type(exc).__name__ + ": " + str(exc)})
    return results


def _source_counts(c):
    rows = c.execute("SELECT source_verification_state, COUNT(*) n FROM sources GROUP BY source_verification_state").fetchall()
    return {str(r[0] or "UNKNOWN"): int(r[1]) for r in rows}


def _build_fixture_items(count: int):
    families = [
        ("Python automation", "python automation API integration small workflow", "python,automation,api"),
        ("Excel automation", "excel spreadsheet automation data cleaning", "excel,automation,data cleaning"),
        ("API integration", "REST API integration webhook automation", "api,automation,python"),
        ("Data pipeline", "ETL data pipeline python data cleaning", "data pipeline,python,data cleaning"),
        ("Web scraping", "web scraping data extraction python", "scraping,python,automation"),
        ("Business automation", "business automation workflow database", "automation,api,python"),
        ("Python debugging", "python bug debugging traceback quick fix", "python,debugging"),
        ("Security engineering", "authorized security audit automation", "security,python,automation"),
    ]
    items = []
    for i in range(count):
        title, desc, skills = families[i % len(families)]
        budget = 120 + (i % 12) * 75
        url = f"https://operationalization.local/opportunity/{i + 1}"
        items.append({
            "title": f"{title} #{i + 1}",
            "url": url,
            "description": f"{desc}; budget USDT {budget}; apply now; small project.",
            "budget": budget,
            "currency": "USDT",
            "skills": skills,
            "country": "Global",
            "iran_access": "UNKNOWN",
            "evidence": [{"kind": "listing", "url": url, "finding": "replayable operational acceptance fixture", "confidence": 0.95}],
        })
    return items


def run_local_operationalization_lab(count: int = LOCAL_FIXTURE_OPPORTUNITY_COUNT):
    """Replay a real acquisition->processing->ranking->decision->learning path.

    This is deliberately isolated in a temporary DB. It proves the executable
    product path without contaminating the user's production database and does
    not claim that fixture data is live market data.
    """
    if count < LOCAL_FIXTURE_OPPORTUNITY_COUNT:
        raise ValueError("OPERATIONALIZATION_REQUIRES_1000_PLUS_OPPORTUNITIES")
    with tempfile.TemporaryDirectory(prefix="marketradar-operationalization-") as td:
        db_path = Path(td) / "lab.db"
        c = connect(db_path)
        ensure_goal_schema(c)
        ensure_economic_schema(c)
        ensure_payment_poll_schema(c)
        source = {
            "name": "OPERATIONALIZATION_FIXTURE",
            "base_url": "https://operationalization.local/feed.json",
            "adapter": "json",
            "status": "active",
            "allow_hosts": ["operationalization.local"],
            "access_scope": "local",
            "terms_status": "allowed",
            "iran_status": "ALLOW",
            "kyc_status": "ALLOW",
            "payment_status": "USDT",
            "source_family": "job_marketplace",
            "source_role": "job_marketplace",
            "policy_lane": "DAILY_PROJECT_SCAN",
            "daily_scan": True,
            "execution_ready": True,
        }
        sync_source_contracts(c, [source])
        payload = json.dumps(_build_fixture_items(count), ensure_ascii=False, separators=(",", ":")).encode()
        digest = hashlib.sha256(payload).hexdigest()
        observed = _now()
        c.execute(
            "INSERT INTO raw_observations(source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind) VALUES(?,?,?,?,?,?,?,?)",
            (source["name"], source["base_url"], observed, payload, digest, 200, "application/json", "source_response"),
        )
        p = Pipeline(c, settings={"profile": {"learning": {"level": 3, "tracks": ["software_engineering"], "stretch": True}, "skills": ["python", "automation", "api", "data cleaning"]}})
        attestation = AcquisitionAttestation(source["name"], source["base_url"], digest, 200)
        items = json.loads(payload.decode())
        for item in items:
            p.ingest(source, item, acquisition_attested=attestation)
        c.commit()
        run_goal_completion(c, profile=p.profile)
        center = run_goal_completion(c, profile=p.profile)
        opportunity_count = c.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        evidence_count = c.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        top7 = center["top7"]
        do_now = center["do_now"]
        # Exercise one complete economic loop using the canonical transition and
        # payment-verification rules. This is a local acceptance proof, not an
        # external settlement claim.
        lifecycle = None
        if top7:
            oid = int(top7[0]["id"])
            for state in ("ELIGIBILITY_CHECK", "RECOMMENDED", "APPROVAL_PENDING", "SUBMITTED", "MESSAGE_RECEIVED", "NEGOTIATION", "ACCEPTED", "IN_PROGRESS", "DELIVERED"):
                transition(c, oid, state, "operationalization-lab", commit=False)
            c.commit()
            payment_ref = "OP-LAB-PAYMENT-0001"
            received_at = _now()
            record_revenue(c, oid, float(top7[0]["budget"] or 250), "USDT", received_at, payment_ref, network="TRON", txid=None, verification_state="RECORDED_UNVERIFIED", commit=False)
            c.commit()
            state_after_claim = c.execute("SELECT state FROM opportunities WHERE id=?", (oid,)).fetchone()[0]
            verify_payment(c, oid, payment_ref, status="VERIFIED", network="TRON", actor="operationalization-lab", commit=True)
            final_state = c.execute("SELECT state FROM opportunities WHERE id=?", (oid,)).fetchone()[0]
            lifecycle = {"opportunity_id": oid, "state_after_claim": state_after_claim, "final_state": final_state}
        result = {
            "pass": opportunity_count >= LOCAL_FIXTURE_OPPORTUNITY_COUNT and len(top7) == FINAL_TOP_TARGET and len(do_now) == VISIBLE_DEFAULT_TARGET and evidence_count >= opportunity_count and lifecycle and lifecycle["state_after_claim"] == "DELIVERED" and lifecycle["final_state"] == "PAID",
            "mode": "LOCAL_REPLAYABLE_OPERATIONAL_ACCEPTANCE",
            "opportunities": opportunity_count,
            "evidence": evidence_count,
            "top7": len(top7),
            "do_now": len(do_now),
            "lifecycle": lifecycle,
            "market_signals": c.execute("SELECT COUNT(*) FROM market_signals").fetchone()[0],
            "demand_clusters": c.execute("SELECT COUNT(*) FROM demand_clusters").fetchone()[0],
            "product_recommendations": c.execute("SELECT COUNT(*) FROM product_recommendations").fetchone()[0],
            "skill_gaps": c.execute("SELECT COUNT(*) FROM skill_gaps").fetchone()[0],
            "portfolio_recommendations": c.execute("SELECT COUNT(*) FROM portfolio_recommendations").fetchone()[0],
            "fixture_warning": "Fixture data proves executable integration only; it is not live market evidence.",
        }
        c.close()
        return result


def run_operationalization(c, root: Path, perform_live_checks=False):
    source_records = load_source_records(root / "config" / "sources.json")
    sync_source_contracts(c, source_records)
    source_counts = _source_counts(c)
    network = _network_preflight()
    live_result = {"attempted": False, "checked": 0, "live": 0, "errors": 0, "note": "Live verification was not executed by default."}
    if perform_live_checks:
        from .source_verification import SourceVerificationEngine
        from .source_search import WebSearchProvider
        eng = SourceVerificationEngine(c, source_records, timeout=5, max_workers=12, max_policy_pages=2, search_provider=WebSearchProvider(timeout=5))
        results = eng.verify([r["name"] for r in source_records if r.get("status") == "active"])
        eng.persist(results)
        live_result = {"attempted": True, "checked": len(results), "live": sum(x.get("source_verification_state") == "LIVE_CONFIRMED" for x in results), "errors": sum(1 for x in results if x.get("source_verification_state") != "LIVE_CONFIRMED"), "note": "Only actual network responses can promote a source to LIVE_CONFIRMED."}
    lab = run_local_operationalization_lab()
    result = {
        "version": "15.1.0",
        "generated_at": _now(),
        "pass": bool(lab["pass"]),
        "targets": {"discovery_pool_reference_target": DISCOVERY_POOL_REFERENCE_TARGET, "local_fixture_opportunity_count": LOCAL_FIXTURE_OPPORTUNITY_COUNT, "top7_target": FINAL_TOP_TARGET, "visible_default_target": VISIBLE_DEFAULT_TARGET},
        "registered_sources": len(source_records),
        "source_state_counts_before_live_gate": source_counts,
        "network_preflight": network,
        "live_source_check": live_result,
        "local_market_operationalization": lab,
        "external_evidence_gates": {
            "execution_sources": "REQUIRES_REAL_NETWORK_AND_SOURCE_EVIDENCE; no fixed execution-source count",
            "real_market_recommendations": "REQUIRES_REAL_MARKET_DATA; local replay validates 7 overall / 3 visible behaviour",
            "external_application": "REQUIRES_CONFIGURED_AUTHORIZED_PROVIDER_AND_HUMAN_APPROVAL",
            "external_payment_settlement": "REQUIRES_EXTERNAL_VERIFIER",
            "windows_exe_installer": "REQUIRES_WINDOWS_HOST",
        },
    }
    report = root / "reports" / "OPERATIONALIZATION_15.1.0.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

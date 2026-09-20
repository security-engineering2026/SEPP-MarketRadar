from __future__ import annotations
"""Final release hardening and operational integrity gates.

This module is intentionally deterministic and local: it never claims that an
external provider, Windows runner, or payment network is healthy without
runtime evidence from that environment.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

from .source_onboarding import audit_registry, PLACEHOLDER_HOSTS
from .source_registry import load_source_records
from .paths import app_root, data_root


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat()


def _check_json(path: Path):
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return None
    except Exception as exc:
        return f"INVALID_JSON:{path.relative_to(app_root())}:{type(exc).__name__}"


def config_gate(root=None):
    root = Path(root or app_root())
    errors, warnings = [], []
    settings_path = root / "config" / "settings.json"
    sources_path = root / "config" / "sources.json"
    for p in (settings_path, sources_path):
        if not p.exists():
            errors.append(f"MISSING_CONFIG:{p.relative_to(root)}")
        else:
            err = _check_json(p)
            if err: errors.append(err)
    if errors:
        return {"errors": errors, "warnings": warnings, "pass": False}
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    timeout = settings.get("http_timeout", 10)
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 120:
        errors.append("HTTP_TIMEOUT_OUT_OF_BOUNDS")
    automation = settings.get("automation", {})
    if automation.get("captcha_bypass") is True:
        errors.append("CAPTCHA_BYPASS_MUST_REMAIN_DISABLED")
    if automation.get("credential_exfiltration") is True:
        errors.append("CREDENTIAL_EXFILTRATION_MUST_REMAIN_DISABLED")
    if automation.get("auto_submit_requires_approval") is not True:
        errors.append("AUTO_SUBMIT_APPROVAL_GATE_REQUIRED")
    records = load_source_records(sources_path)
    audit = audit_registry(records)
    errors.extend(f"SOURCE_REGISTRY:{x.name}:{e}" for x in audit["results"] for e in x.errors)
    names = [x.get("name") for x in records]
    if len(names) != len(set(names)):
        errors.append("DUPLICATE_SOURCE_NAMES")
    hosts = {}
    for r in records:
        host = urlparse(str(r.get("base_url", ""))).hostname
        if host:
            hosts.setdefault(host.lower().rstrip("."), []).append(r.get("name"))
        if str(r.get("status", "candidate")) == "active" and host in PLACEHOLDER_HOSTS:
            errors.append(f"ACTIVE_PLACEHOLDER_HOST:{r.get('name')}")
    duplicate_hosts = {h: n for h, n in hosts.items() if len(n) > 1}
    if duplicate_hosts:
        warnings.append("DUPLICATE_SOURCE_HOSTS:" + ",".join(sorted(duplicate_hosts)))
    unique_host_count = len(hosts)
    if unique_host_count < 500:
        warnings.append(f"DISCOVERY_POOL_UNIQUE_HOSTS_LT_500:{unique_host_count}")
    return {"errors": errors, "warnings": warnings, "pass": not errors,
            "source_count": len(records), "unique_host_count": unique_host_count, "promotable": len(audit["promotable"]),
            "duplicate_hosts": duplicate_hosts}


def database_gate(path=None):
    path = Path(path or (data_root() / "marketradar.db"))
    errors, warnings = [], []
    if not path.exists():
        return {"errors": ["DATABASE_MISSING"], "warnings": [], "pass": False}
    c = sqlite3.connect(path, timeout=15)
    c.row_factory = sqlite3.Row
    try:
        integrity = c.execute("PRAGMA integrity_check").fetchall()
        if not integrity or integrity[0][0] != "ok":
            errors.append("SQLITE_INTEGRITY_CHECK_FAILED")
        fk = c.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            errors.append(f"FOREIGN_KEY_VIOLATIONS:{len(fk)}")
        # The application intentionally uses soft references in several tables;
        # verify the important ones explicitly so corruption cannot hide behind
        # SQLite's partial foreign-key coverage.
        orphan_checks = [
            ("evidence", "opportunities", "opportunity_id"),
            ("application_events", "opportunities", "opportunity_id"),
            ("revenue", "opportunities", "opportunity_id"),
            ("opportunity_sources", "opportunities", "opportunity_id"),
            ("application_tracking", "opportunities", "opportunity_id"),
            ("project_contracts", "opportunities", "opportunity_id"),
        ]
        for child, parent, key in orphan_checks:
            try:
                n = c.execute(f"SELECT COUNT(*) FROM {child} x WHERE NOT EXISTS (SELECT 1 FROM {parent} p WHERE p.id=x.{key})").fetchone()[0]
                if n: errors.append(f"ORPHAN_ROWS:{child}:{n}")
            except sqlite3.OperationalError:
                # A legacy optional table may not exist; schema gate handles it.
                warnings.append(f"OPTIONAL_TABLE_MISSING:{child}")
        invalid_states = c.execute("SELECT COUNT(*) FROM opportunities WHERE state NOT IN ('DISCOVERED','ELIGIBILITY_CHECK','RECOMMENDED','APPROVAL_PENDING','SUBMITTED','VIEWED','MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','IN_PROGRESS','DELIVERED','PAID','REJECTED','EXPIRED','CANCELLED')").fetchone()[0]
        if invalid_states: errors.append(f"INVALID_OPPORTUNITY_STATES:{invalid_states}")
        paid_without_revenue = c.execute("SELECT COUNT(*) FROM opportunities o WHERE o.state='PAID' AND NOT EXISTS (SELECT 1 FROM revenue r WHERE r.opportunity_id=o.id)").fetchone()[0]
        if paid_without_revenue: errors.append(f"PAID_WITHOUT_REVENUE:{paid_without_revenue}")
        expired_approvals = c.execute("SELECT COUNT(*) FROM approvals WHERE used_at IS NULL AND expires_at < ?", (int(_now().timestamp()),)).fetchone()[0]
        if expired_approvals: warnings.append(f"EXPIRED_UNUSED_APPROVALS:{expired_approvals}")
        stuck = c.execute("SELECT COUNT(*) FROM opportunities WHERE state IN ('APPROVAL_PENDING','SUBMITTED','NEGOTIATION','IN_PROGRESS') AND last_seen < ?", (_iso(_now()-timedelta(days=30)),)).fetchone()[0]
        if stuck: warnings.append(f"STALE_ACTIVE_WORKFLOWS:{stuck}")
        return {"errors": errors, "warnings": warnings, "pass": not errors,
                "integrity": integrity[0][0] if integrity else "unknown",
                "database_bytes": path.stat().st_size}
    finally:
        c.close()


def filesystem_gate(root=None):
    root = Path(root or app_root())
    errors, warnings = [], []
    required = [root/"config"/"settings.json", root/"config"/"sources.json", root/"packaging"/"installer.iss", root/"packaging"/"build_windows_release.ps1"]
    for p in required:
        if not p.exists(): errors.append(f"RELEASE_FILE_MISSING:{p.relative_to(root)}")
    forbidden = [".pytest_cache", "__pycache__", ".coverage"]
    for name in forbidden:
        if (root/name).exists(): warnings.append(f"BUILD_ARTIFACT_PRESENT:{name}")
    # Secrets must never be shipped in config.
    secret_tokens = ("password", "secret", "private_key", "access_token", "refresh_token")
    for p in root.glob("config/*.json"):
        try:
            text = p.read_text(encoding="utf-8").lower()
        except Exception:
            continue
        for token in secret_tokens:
            if f'"{token}"' in text:
                warnings.append(f"CONFIG_SECRET_FIELD_REVIEW:{p.name}:{token}")
    return {"errors": errors, "warnings": warnings, "pass": not errors}


def run_release_hardening():
    config = config_gate()
    database = database_gate()
    filesystem = filesystem_gate()
    result = {
        "generated_at": _iso(_now()),
        "config": config,
        "database": database,
        "filesystem": filesystem,
    }
    result["pass"] = all(x["pass"] for x in (config, database, filesystem))
    result["blocking_errors"] = sum(len(x["errors"]) for x in (config, database, filesystem))
    result["warnings"] = sum(len(x["warnings"]) for x in (config, database, filesystem))
    return result

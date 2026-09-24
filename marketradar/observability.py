from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone

STATUSES = ("ATTEMPTED", "SUCCESSFUL", "FAILED", "SKIPPED", "UNKNOWN", "NOT_CONFIGURED")

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _digest(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()

def ensure_schema(c):
    c.execute("""CREATE TABLE IF NOT EXISTS observability_events(
        id INTEGER PRIMARY KEY, stage TEXT NOT NULL, status TEXT NOT NULL,
        observed_at TEXT NOT NULL, duration_ms INTEGER, error TEXT,
        retry_count INTEGER NOT NULL DEFAULT 0, health TEXT NOT NULL DEFAULT 'UNKNOWN',
        details_json TEXT NOT NULL DEFAULT '{}', details_sha256 TEXT NOT NULL,
        UNIQUE(stage, observed_at, details_sha256))""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_observability_stage_time ON observability_events(stage, observed_at DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_observability_status ON observability_events(status)")
    c.execute("""CREATE TRIGGER IF NOT EXISTS observability_events_no_update
        BEFORE UPDATE ON observability_events BEGIN
        SELECT RAISE(ABORT,'observability events are immutable'); END""")
    c.execute("""CREATE TRIGGER IF NOT EXISTS observability_events_no_delete
        BEFORE DELETE ON observability_events BEGIN
        SELECT RAISE(ABORT,'observability events are immutable'); END""")

def record_event(c, stage: str, status: str, *, duration_ms=None, error=None,
                 retry_count=0, health="UNKNOWN", details=None, observed_at=None) -> str:
    status = str(status).upper()
    if status not in STATUSES:
        raise ValueError("INVALID_OBSERVABILITY_STATUS")
    if int(retry_count) < 0:
        raise ValueError("INVALID_RETRY_COUNT")
    details = dict(details or {})
    digest = _digest(details)
    observed_at = observed_at or _now()
    c.execute("""INSERT INTO observability_events
        (stage,status,observed_at,duration_ms,error,retry_count,health,details_json,details_sha256)
        VALUES(?,?,?,?,?,?,?,?,?)""",
        (stage, status, observed_at, duration_ms, error, int(retry_count),
         str(health).upper(), json.dumps(details, sort_keys=True, default=str), digest))
    return digest

def summarize(c, stage=None):
    if stage is None:
        rows = c.execute("SELECT status, COUNT(*) AS count FROM observability_events GROUP BY status ORDER BY status").fetchall()
    else:
        rows = c.execute("SELECT status, COUNT(*) AS count FROM observability_events WHERE stage=? GROUP BY status ORDER BY status", (stage,)).fetchall()
    return {row["status"]: row["count"] for row in rows}

def latest(c, stage):
    row = c.execute("""SELECT stage,status,observed_at,duration_ms,error,retry_count,health,
        details_json,details_sha256 FROM observability_events WHERE stage=? ORDER BY id DESC LIMIT 1""", (stage,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["details"] = json.loads(result.pop("details_json"))
    return result

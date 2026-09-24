import sqlite3
from marketradar.observability import ensure_schema, record_event, summarize, latest

def test_r048_observability_records_required_statuses_and_digest():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    try:
        ensure_schema(c)
        digest = record_event(c, "source-discovery", "failed", duration_ms=125, error="timeout",
            retry_count=2, health="degraded", details={"source":"example","attempt":3},
            observed_at="2026-09-24T08:00:00+00:00")
        assert len(digest) == 64
        record_event(c, "source-discovery", "successful", details={"source":"example"}, observed_at="2026-09-24T08:01:00+00:00")
        record_event(c, "source-discovery", "skipped", details={"reason":"policy"}, observed_at="2026-09-24T08:02:00+00:00")
        record_event(c, "source-discovery", "unknown", details={"reason":"provider"}, observed_at="2026-09-24T08:03:00+00:00")
        record_event(c, "source-discovery", "not_configured", details={"provider":"searxng"}, observed_at="2026-09-24T08:04:00+00:00")
        record_event(c, "source-discovery", "attempted", details={"source":"example"}, observed_at="2026-09-24T08:05:00+00:00")
        assert summarize(c, "source-discovery") == {"ATTEMPTED":1,"FAILED":1,"NOT_CONFIGURED":1,"SKIPPED":1,"SUCCESSFUL":1,"UNKNOWN":1}
        last = latest(c, "source-discovery")
        assert last["status"] == "ATTEMPTED"
        assert last["details"]["source"] == "example"
    finally:
        c.close()

def test_r048_observability_rejects_invalid_status_and_negative_retry():
    c = sqlite3.connect(":memory:")
    try:
        ensure_schema(c)
        try: record_event(c, "x", "done")
        except ValueError as exc: assert str(exc) == "INVALID_OBSERVABILITY_STATUS"
        else: raise AssertionError("invalid status accepted")
        try: record_event(c, "x", "failed", retry_count=-1)
        except ValueError as exc: assert str(exc) == "INVALID_RETRY_COUNT"
        else: raise AssertionError("negative retry accepted")
    finally:
        c.close()

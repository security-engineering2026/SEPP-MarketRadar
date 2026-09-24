from datetime import datetime, timedelta, timezone

from marketradar.db import connect
from marketradar.scheduler import ScanScheduler


def test_scheduler_runs_are_durable_resumable_and_backoff_aware(tmp_path):
    c = connect(tmp_path / "scheduler.db")
    now = datetime(2026, 9, 24, 5, 0, tzinfo=timezone.utc)
    try:
        run_id = ScanScheduler.enqueue(
            c, "project_scan", scheduled_at=now, max_attempts=3, timeout_seconds=60, now=now
        )
        claimed = ScanScheduler.claim_due(c, "project_scan", worker_id="worker-a", now=now)
        assert claimed["id"] == run_id
        assert claimed["status"] == "RUNNING"
        assert claimed["attempt"] == 1

        assert ScanScheduler.claim_due(c, "project_scan", worker_id="worker-b", now=now) is None

        failed = ScanScheduler.fail(c, run_id, "provider timeout", now=now, backoff_seconds=120)
        assert failed["status"] == "RETRY"
        assert failed["attempt"] == 1
        assert failed["last_error"] == "provider timeout"
        assert failed["next_run_at"] == (now + timedelta(seconds=120)).isoformat()

        retry = ScanScheduler.claim_due(
            c, "project_scan", worker_id="worker-b",
            now=now + timedelta(seconds=121),
        )
        assert retry["status"] == "RUNNING"
        assert retry["attempt"] == 2

        done = ScanScheduler.complete(c, run_id, {"processed": 7}, now=now + timedelta(seconds=122))
        assert done["status"] == "SUCCEEDED"
        assert done["finished_at"] == (now + timedelta(seconds=122)).isoformat()

        persisted = ScanScheduler.get_run(c, run_id)
        assert persisted["status"] == "SUCCEEDED"
        assert persisted["worker_id"] == "worker-b"
    finally:
        c.close()


def test_scheduler_recovers_stale_running_work_without_duplicate_runs(tmp_path):
    c = connect(tmp_path / "scheduler.db")
    now = datetime(2026, 9, 24, 5, 0, tzinfo=timezone.utc)
    try:
        run_id = ScanScheduler.enqueue(
            c, "intelligence_scan", scheduled_at=now, max_attempts=2, timeout_seconds=30, now=now
        )
        claimed = ScanScheduler.claim_due(c, "intelligence_scan", worker_id="worker-a", now=now)
        assert claimed["status"] == "RUNNING"

        stale = now + timedelta(seconds=31)
        recovered = ScanScheduler.recover_stale(c, stale)
        assert recovered == [run_id]
        state = ScanScheduler.get_run(c, run_id)
        assert state["status"] == "RETRY"
        assert state["recovery_count"] == 1
        assert state["last_error"] == "STALE_RUN_RECOVERED"

        reclaimed = ScanScheduler.claim_due(c, "intelligence_scan", worker_id="worker-b", now=stale)
        assert reclaimed["id"] == run_id
        assert reclaimed["attempt"] == 2
        assert reclaimed["status"] == "RUNNING"

        final = ScanScheduler.fail(c, run_id, "second failure", now=stale, backoff_seconds=60)
        assert final["status"] == "FAILED"
        assert final["next_run_at"] is None
    finally:
        c.close()

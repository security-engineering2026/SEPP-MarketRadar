from __future__ import annotations
from datetime import datetime, timedelta


class ScanScheduler:
    """Schedule project discovery hourly and market intelligence twice daily."""
    def __init__(self, project_interval_minutes=60, intelligence_times=('08:00', '20:00')):
        self._legacy_fixed_times = isinstance(project_interval_minutes, (tuple, list))
        if self._legacy_fixed_times:
            intelligence_times = tuple(project_interval_minutes)
            project_interval_minutes = 60
        self.project_interval_minutes = int(project_interval_minutes)
        self.intelligence_times = tuple(int(x.split(':')[0]) * 60 + int(x.split(':')[1]) for x in intelligence_times)

    def project_due(self, last_run, now=None):
        now = now or datetime.now().astimezone()
        if not last_run:
            return True
        return now - last_run >= timedelta(minutes=self.project_interval_minutes)

    def intelligence_due(self, last_run, now=None):
        now = now or datetime.now().astimezone()
        if last_run and now - last_run < timedelta(hours=12):
            return False
        minute_of_day = now.hour * 60 + now.minute
        return any(abs(minute_of_day - target) <= 30 for target in self.intelligence_times)

    def next_runs(self, now=None, count=6):
        now = now or datetime.now().astimezone()
        if self._legacy_fixed_times:
            out=[]
            day=now.date()
            for offset in range(0, 8):
                d=day + timedelta(days=offset)
                for minutes in self.intelligence_times:
                    candidate=now.replace(year=d.year,month=d.month,day=d.day,hour=minutes//60,minute=minutes%60,second=0,microsecond=0)
                    if candidate>now: out.append(candidate)
                if len(out)>=count: return out[:count]
            return out[:count]
        return [now + timedelta(minutes=self.project_interval_minutes*i) for i in range(1,count+1)]


    @staticmethod
    def ensure_schema(c):
        c.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name TEXT NOT NULL,
                status TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                heartbeat_at TEXT,
                attempt INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                timeout_seconds INTEGER NOT NULL DEFAULT 900,
                next_run_at TEXT,
                last_error TEXT,
                recovery_count INTEGER NOT NULL DEFAULT 0,
                worker_id TEXT,
                result_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_scheduler_due ON scheduler_runs(status, next_run_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_scheduler_running ON scheduler_runs(status, heartbeat_at)")
        c.commit()

    @staticmethod
    def _iso(value):
        if isinstance(value, datetime):
            return value.astimezone().isoformat()
        return str(value)

    @classmethod
    def enqueue(cls, c, job_name, scheduled_at=None, max_attempts=3, timeout_seconds=900, now=None):
        cls.ensure_schema(c)
        now = now or datetime.now().astimezone()
        scheduled_at = scheduled_at or now
        stamp = cls._iso(now)
        due = cls._iso(scheduled_at)
        cur = c.execute(
            """INSERT INTO scheduler_runs
               (job_name,status,scheduled_at,next_run_at,max_attempts,timeout_seconds,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (str(job_name), "SCHEDULED", due, due, int(max_attempts), int(timeout_seconds), stamp, stamp),
        )
        c.commit()
        return int(cur.lastrowid)

    @classmethod
    def recover_stale(cls, c, now=None):
        cls.ensure_schema(c)
        now = now or datetime.now().astimezone()
        stamp = cls._iso(now)
        rows = c.execute(
            """SELECT id,attempt,max_attempts,timeout_seconds
               FROM scheduler_runs
               WHERE status='RUNNING' AND heartbeat_at IS NOT NULL"""
        ).fetchall()
        recovered = []
        for row in rows:
            try:
                heartbeat = datetime.fromisoformat(row["heartbeat_at"])
                age = (now - heartbeat).total_seconds()
            except (TypeError, ValueError):
                age = row["timeout_seconds"] + 1
            if age <= int(row["timeout_seconds"]):
                continue
            next_status = "RETRY" if int(row["attempt"]) < int(row["max_attempts"]) else "FAILED"
            c.execute(
                """UPDATE scheduler_runs
                   SET status=?, next_run_at=?, recovery_count=recovery_count+1,
                       last_error=?, updated_at=?, finished_at=CASE WHEN ?='FAILED' THEN ? ELSE finished_at END
                   WHERE id=? AND status='RUNNING'""",
                (
                    next_status, stamp,
                    "STALE_RUN_RECOVERED" if next_status == "RETRY" else "STALE_RUN_MAX_ATTEMPTS",
                    stamp, next_status, stamp, int(row["id"])
                ),
            )
            if next_status == "RETRY":
                recovered.append(int(row["id"]))
        c.commit()
        return recovered

    @classmethod
    def claim_due(cls, c, job_name=None, worker_id="local", now=None):
        cls.ensure_schema(c)
        now = now or datetime.now().astimezone()
        cls.recover_stale(c, now)
        stamp = cls._iso(now)
        where = "status IN ('SCHEDULED','RETRY') AND next_run_at <= ?"
        params = [stamp]
        if job_name is not None:
            where += " AND job_name=?"
            params.append(str(job_name))
        row = c.execute(
            f"""SELECT * FROM scheduler_runs
                WHERE {where}
                ORDER BY next_run_at,id
                LIMIT 1""",
            tuple(params),
        ).fetchone()
        if not row:
            return None
        attempt = int(row["attempt"]) + 1
        c.execute(
            """UPDATE scheduler_runs
               SET status='RUNNING', attempt=?, started_at=COALESCE(started_at,?),
                   heartbeat_at=?, worker_id=?, updated_at=?, last_error=NULL
               WHERE id=? AND status IN ('SCHEDULED','RETRY')""",
            (attempt, stamp, stamp, str(worker_id), stamp, int(row["id"])),
        )
        if c.execute("SELECT changes()").fetchone()[0] != 1:
            c.rollback()
            return None
        c.commit()
        return dict(c.execute("SELECT * FROM scheduler_runs WHERE id=?", (int(row["id"]),)).fetchone())

    @classmethod
    def heartbeat(cls, c, run_id, now=None):
        cls.ensure_schema(c)
        stamp = cls._iso(now or datetime.now().astimezone())
        cur = c.execute(
            "UPDATE scheduler_runs SET heartbeat_at=?,updated_at=? WHERE id=? AND status='RUNNING'",
            (stamp, stamp, int(run_id)),
        )
        c.commit()
        return cur.rowcount == 1

    @classmethod
    def complete(cls, c, run_id, result=None, now=None):
        import json
        cls.ensure_schema(c)
        stamp = cls._iso(now or datetime.now().astimezone())
        cur = c.execute(
            """UPDATE scheduler_runs
               SET status='SUCCEEDED',finished_at=?,heartbeat_at=?,result_json=?,updated_at=?
               WHERE id=? AND status='RUNNING'""",
            (stamp, stamp, json.dumps(result, ensure_ascii=False, sort_keys=True) if result is not None else None, stamp, int(run_id)),
        )
        c.commit()
        if cur.rowcount != 1:
            raise ValueError("SCHEDULER_RUN_NOT_RUNNING")
        return dict(c.execute("SELECT * FROM scheduler_runs WHERE id=?", (int(run_id),)).fetchone())

    @classmethod
    def fail(cls, c, run_id, error, now=None, backoff_seconds=None):
        cls.ensure_schema(c)
        now = now or datetime.now().astimezone()
        stamp = cls._iso(now)
        row = c.execute("SELECT attempt,max_attempts FROM scheduler_runs WHERE id=? AND status='RUNNING'", (int(run_id),)).fetchone()
        if not row:
            raise ValueError("SCHEDULER_RUN_NOT_RUNNING")
        attempt = int(row["attempt"])
        if attempt >= int(row["max_attempts"]):
            status = "FAILED"
            next_run = None
        else:
            status = "RETRY"
            delay = int(backoff_seconds if backoff_seconds is not None else min(3600, 30 * (2 ** max(0, attempt - 1))))
            next_run = cls._iso(now + timedelta(seconds=delay))
        c.execute(
            """UPDATE scheduler_runs
               SET status=?,next_run_at=?,last_error=?,finished_at=CASE WHEN ?='FAILED' THEN ? ELSE finished_at END,
                   heartbeat_at=?,updated_at=?
               WHERE id=? AND status='RUNNING'""",
            (status, next_run, str(error)[:2000], status, stamp, stamp, stamp, int(run_id)),
        )
        c.commit()
        return dict(c.execute("SELECT * FROM scheduler_runs WHERE id=?", (int(run_id),)).fetchone())

    @classmethod
    def get_run(cls, c, run_id):
        cls.ensure_schema(c)
        row = c.execute("SELECT * FROM scheduler_runs WHERE id=?", (int(run_id),)).fetchone()
        return dict(row) if row else None

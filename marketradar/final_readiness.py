from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .application import transition, verify_payment
from .db import connect
from .paths import app_root, data_root

REQUIRED_TABLES = {
    'opportunities','source_contracts','entities','parties','claims','claim_evidence',
    'workflow_events','action_authorizations','action_attempts','project_contracts',
    'followup_schedule','operation_reminders','application_tracking',
    'application_status_observations','project_milestones','project_communications',
    'payment_verification_attempts','payment_checks','payment_verification_sources',
    'source_constraints','source_review_queue','source_scan_state','source_blacklist_archive','opportunity_blacklist_archive',
    'provider_registry','daily_recommendations','product_build_specs',
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_schema(c) -> list[str]:
    found = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return sorted(REQUIRED_TABLES - found)


def _local_lifecycle(c) -> dict:
    """Run the complete economic state machine on an isolated in-memory database."""
    from .db import connect as db_connect
    from .operations import record_contract
    from .economic_loop import add_milestone, complete_milestone, record_payment_check
    from .application import record_revenue

    tmp = db_connect(':memory:')
    try:
        oid = 9100001
        tmp.execute('''INSERT INTO opportunities
            (id,title,description,source,state,first_seen,last_seen)
            VALUES(?,?,?,?,?,?,?)''',
            (oid,'FINAL-E2E','local final release lifecycle','LOCAL_SIMULATOR','DISCOVERED',_now(),_now()))
        tmp.commit()
        transition(tmp, oid, 'ELIGIBILITY_CHECK', 'final-e2e')
        transition(tmp, oid, 'RECOMMENDED', 'final-e2e')
        transition(tmp, oid, 'APPROVAL_PENDING', 'final-e2e')
        transition(tmp, oid, 'SUBMITTED', 'final-e2e')
        ts = _now()
        tmp.execute("INSERT INTO application_tracking(opportunity_id,source,external_ref,tracking_mode,enabled,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (oid,'LOCAL_SIMULATOR','FINAL-APP-1','MANUAL_EVIDENCE',1,ts,ts)); tmp.commit()
        transition(tmp, oid, 'MESSAGE_RECEIVED', 'final-e2e')
        transition(tmp, oid, 'NEGOTIATION', 'final-e2e')
        transition(tmp, oid, 'ACCEPTED', 'final-e2e')
        transition(tmp, oid, 'IN_PROGRESS', 'final-e2e')
        record_contract(tmp, oid, accepted_at=_now(), started_at=_now(), deadline_at=_now(), agreed_amount=100, currency='USD')
        mid = add_milestone(tmp, oid, 'Final delivery')
        complete_milestone(tmp, mid, evidence_ref='sha256:local-final-artifact')
        transition(tmp, oid, 'DELIVERED', 'final-e2e')
        record_revenue(tmp, oid, 100, 'USD', _now(), 'FINAL-REF')
        state_after_claim = tmp.execute('SELECT state FROM opportunities WHERE id=?',(oid,)).fetchone()[0]
        if state_after_claim != 'DELIVERED':
            raise AssertionError(f'payment claim changed state: {state_after_claim}')
        record_payment_check(tmp, oid, 'FINAL-REF', 'LOCAL_SIMULATOR', 'VERIFIED', 100, 'USD', 'local://settlement')
        verify_payment(tmp, oid, 'FINAL-REF', 'VERIFIED', actor='final-e2e')
        final_state = tmp.execute('SELECT state FROM opportunities WHERE id=?',(oid,)).fetchone()[0]
        if final_state != 'PAID':
            raise AssertionError(f'verified payment did not reach PAID: {final_state}')
        return {'opportunity_id': oid, 'state_after_claim': state_after_claim, 'final_state': final_state}
    finally:
        tmp.close()


def _check_backup_restore() -> dict:
    """Exercise SQLite backup/restore on the current schema without touching user data."""
    with tempfile.TemporaryDirectory(prefix='marketradar-final-') as td:
        src = Path(td) / 'source.db'
        dst = Path(td) / 'restored.db'
        c = connect(src)
        try:
            c.execute("CREATE TABLE IF NOT EXISTS _final_probe(value TEXT NOT NULL)")
            c.execute("INSERT INTO _final_probe(value) VALUES('ok')")
            c.commit()
            c.execute("VACUUM")
        finally:
            c.close()
        shutil.copy2(src, dst)
        r = connect(dst)
        try:
            value = r.execute("SELECT value FROM _final_probe").fetchone()[0]
        finally:
            r.close()
        return {'restored_value': value, 'sha256': hashlib.sha256(dst.read_bytes()).hexdigest()}


def run_final_verification() -> dict:
    root = app_root()
    from .release_hardening import run_release_hardening
    hardening = run_release_hardening()
    c = connect(data_root() / 'marketradar.db')
    try:
        missing = _check_schema(c)
        source_count = c.execute('SELECT COUNT(*) FROM source_contracts').fetchone()[0]
        unique_hosts = c.execute("SELECT COUNT(DISTINCT lower(replace(replace(base_url,'https://',''),'http://',''))) FROM sources WHERE base_url IS NOT NULL").fetchone()[0]
        source_lanes = {str(r[0] or 'UNKNOWN'): int(r[1]) for r in c.execute('SELECT source_lane,COUNT(*) FROM sources GROUP BY source_lane').fetchall()}
        opportunity_count = c.execute('SELECT COUNT(*) FROM opportunities').fetchone()[0]
        backup = _check_backup_restore()
        lifecycle = _local_lifecycle(c)
        version_files = {
            'package': root / 'marketradar' / '__init__.py',
            'android': root / 'android-companion' / 'app' / 'build.gradle.kts',
            'snapshot': root / 'reports' / 'release_snapshot.json',
        }
        return {
            'version': __version__,
            'generated_at': _now(),
            'schema_missing': missing,
            'source_contracts': source_count,
            'unique_source_hosts': unique_hosts,
            'source_lanes': source_lanes,
            'opportunities': opportunity_count,
            'backup_restore': backup,
            'economic_lifecycle': lifecycle,
            'version_files_present': {k: p.exists() for k,p in version_files.items()},
            'release_hardening': hardening,
            'pass': not missing and lifecycle['final_state'] == 'PAID' and hardening['pass'],
        }
    finally:
        c.close()

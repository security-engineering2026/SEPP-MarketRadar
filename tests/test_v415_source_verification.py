import json
from pathlib import Path
from marketradar.source_registry import load_source_records
from marketradar.source_onboarding import audit_registry
from marketradar import __version__

ROOT=Path(__file__).parents[1]

def test_registry_has_explicit_verification_fields():
    rows=load_source_records(ROOT/'config/sources.json')
    required={'source_verification_state','iran_eligibility','kyc_requirement','evidence_confidence','market_intelligence_value','execution_ready','discovery_basis'}
    assert all(required.issubset(r) for r in rows)

def test_daily_execution_gate_is_strict():
    rows=load_source_records(ROOT/'config/sources.json')
    bad=[r['name'] for r in rows if r.get('policy_lane')=='DAILY_PROJECT_SCAN' and r.get('execution_ready') and (r.get('iran_eligibility')!='ALLOW' or r.get('source_verification_state')!='LIVE_CONFIRMED')]
    assert not bad

def test_blocked_sources_never_execution_ready():
    rows=load_source_records(ROOT/'config/sources.json')
    assert not [r['name'] for r in rows if r.get('policy_lane')=='BLOCKED_IRAN' and r.get('execution_ready')]

def test_release_snapshot_matches_registry():
    rows=load_source_records(ROOT/'config/sources.json')
    snap=json.loads((ROOT/'reports/release_snapshot.json').read_text())
    assert snap['version']==__version__
    assert snap['sources']==len(rows)
    assert snap['active']==sum(r.get('status')=='active' for r in rows)
    assert snap['daily_execution_ready']==sum(r.get('policy_lane')=='DAILY_PROJECT_SCAN' and r.get('execution_ready') for r in rows)

def test_explicit_iran_restrictions_are_blocked():
    rows={r['name']:r for r in load_source_records(ROOT/'config/sources.json')}
    for name in ('Kwork','Mostaql','Khamsat'):
        assert rows[name]['policy_lane']=='BLOCKED_IRAN'
        assert rows[name]['iran_eligibility']=='BLOCK'
        assert rows[name]['terms_status']=='blocked'
        assert rows[name]['iran_policy_url']

def test_source_audit_has_no_invalid_records():
    report=audit_registry(load_source_records(ROOT/'config/sources.json'))
    assert report['invalid']==0

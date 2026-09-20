import json
from pathlib import Path
from collections import Counter
from marketradar.country_policy import apply_blacklist
from marketradar.market_intelligence import distribution_targets
from marketradar.source_registry import load_source_records
from marketradar.db import connect, sync_source_contracts

ROOT=Path(__file__).parents[1]

def records(): return load_source_records(ROOT/'config'/'sources.json')

def test_source_federation_has_real_breadth_and_lanes():
    rows=records(); assert len(rows)>=100
    assert sum(x.get('country')=='Iran' for x in rows)>=10
    assert sum(x.get('source_role')=='bug_bounty' for x in rows)>=10
    assert sum(x.get('source_role') in {'freelance_marketplace','job_marketplace'} for x in rows)>=30
    lanes=Counter(x.get('policy_lane') for x in rows)
    assert lanes['DAILY_PROJECT_SCAN']>=10
    assert lanes['GLOBAL_DISCOVERY']>=5
    assert lanes['NEEDS_ANALYSIS']>=40
    assert lanes['BLOCKED_IRAN']>=3

def test_social_families_are_explicit():
    families={x.get('source_family') for x in records()}
    assert {'telegram','instagram','x','linkedin','reddit','bale','eitaa','soroush'} <= families

def test_iranian_sources_are_in_daily_discovery_lane():
    iran=[x for x in records() if x.get('country')=='Iran']
    assert len(iran)>=10
    assert all(x.get('policy_lane')=='DAILY_PROJECT_SCAN' for x in iran)

def test_known_iran_blocked_platforms_are_not_daily():
    rows={x['name']:x for x in records()}
    for name in ('Upwork','Freelancer','Fiverr','HackerOne','Bugcrowd','Synack'):
        assert rows[name]['iran_status']=='BLOCK'
        assert rows[name]['policy_lane']=='BLOCKED_IRAN'
        assert not rows[name]['daily_scan']

def test_blacklist_does_not_trigger_on_irrelevant_text_mentions():
    assert apply_blacklist({'title':'Python role','description':'The team has no operations in Israel and welcomes global applicants'}, ['Iran','Israel']) == []
    assert apply_blacklist({'country':'Israel','title':'Developer'}, ['Iran','Israel']) == ['Israel']

def test_distribution_returns_actual_registered_sites():
    rows=[x for x in records() if x.get('policy_lane')=='DAILY_PROJECT_SCAN']
    result=distribution_targets('python_debugging', rows)
    names={x['name'] for x in result['recommended_sites']}
    assert 'Jobinja_Iran' in names
    assert result['daily_project_sites']
    assert result['recommended_sites']
    assert 'global_discovery_sites' in result

def test_lane_metadata_persists_to_database():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        c=connect(Path(d)/'mr.db')
        try:
            sync_source_contracts(c,records())
            assert c.execute("SELECT COUNT(*) FROM sources WHERE policy_lane='DAILY_PROJECT_SCAN'").fetchone()[0] >= 10
            assert c.execute("SELECT COUNT(*) FROM sources WHERE policy_lane='BLOCKED_IRAN'").fetchone()[0] >= 3
            assert c.execute("SELECT COUNT(*) FROM source_contracts WHERE source_role='bug_bounty'").fetchone()[0] >= 10
        finally:
            c.close()


def test_active_daily_sources_are_explicitly_iran_compatible():
    rows=records()
    active_daily=[x for x in rows if x.get('status')=='active' and x.get('policy_lane')=='DAILY_PROJECT_SCAN']
    assert active_daily
    assert all(x.get('iran_status')=='ALLOW' for x in active_daily)

def test_global_discovery_sources_are_not_mislabeled_as_iran_allow():
    rows=records()
    global_rows=[x for x in rows if x.get('policy_lane')=='GLOBAL_DISCOVERY']
    assert global_rows
    assert all(x.get('iran_status')!='BLOCK' for x in global_rows)

def test_iran_source_does_not_get_blocked_as_employer_country():
    from marketradar.policy import eligibility
    state,_=eligibility({'iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}, True, {'country':'Iran'}, {'execution_blacklist_countries':['Israel']})
    assert state=='EXECUTE'

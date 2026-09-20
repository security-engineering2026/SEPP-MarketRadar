from marketradar.social_connectors import CONTRACTS, build_request
from marketradar.source_discovery import classify_source_lanes, discovery_candidates

def test_all_requested_social_connectors_have_explicit_contracts():
    assert {'telegram','instagram','x','linkedin','reddit','bale','eitaa','soroush'} <= set(CONTRACTS)
    assert all(c.authorization_required for c in CONTRACTS.values())

def test_social_credentials_are_referenced_not_embedded():
    r=build_request('telegram','TELEGRAM_BOT_TOKEN','https://api.telegram.org/bot/getUpdates')
    assert r['credential_env']=='TELEGRAM_BOT_TOKEN'
    for bad in ('123456:ABCDEF','Bearer secret','https://secret'):
        try: build_request('telegram',bad,'https://api.telegram.org/bot/getUpdates')
        except ValueError: pass
        else: raise AssertionError('embedded credential accepted')

def test_source_discovery_separates_candidate_lanes():
    rows=[{'status':'candidate','policy_lane':'NEEDS_ANALYSIS','name':'A','base_url':'https://a.test'}, {'status':'active','policy_lane':'DAILY_PROJECT_SCAN','name':'B','base_url':'https://b.test'}, {'status':'candidate','policy_lane':'BLOCKED_IRAN','name':'C','base_url':'https://c.test'}]
    assert classify_source_lanes(rows)['NEEDS_ANALYSIS']==1
    assert [x['name'] for x in discovery_candidates(rows)]==['A']

def test_engine_scan_only_runs_daily_project_lane():
    rows=[
      {'name':'A','status':'active','policy_lane':'DAILY_PROJECT_SCAN','daily_scan':True},
      {'name':'B','status':'active','policy_lane':'NEEDS_ANALYSIS','daily_scan':False},
      {'name':'C','status':'candidate','policy_lane':'DAILY_PROJECT_SCAN','daily_scan':True},
    ]
    selected=[r['name'] for r in rows if r.get('status')=='active' and r.get('policy_lane')=='DAILY_PROJECT_SCAN' and r.get('daily_scan')]
    assert selected==['A']

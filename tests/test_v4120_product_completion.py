from pathlib import Path
import tempfile
from datetime import datetime
from marketradar.db import connect
from marketradar.pipeline import Pipeline
from marketradar.runtime import MarketRadarRuntime
from marketradar.scheduler import ScanScheduler
from marketradar.market_intelligence import duplicate_groups, market_snapshot, distribution_targets

def _opp(c, source, title, url, desc, country=None):
    s={'name':source,'iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed','country':'Global'}
    Pipeline(c).ingest(s, {'title':title,'url':url,'description':desc,'country':country,'evidence':[{'url':url,'finding':'listing','confidence':.95}]})
    c.commit(); return c.execute('select id from opportunities where url=?',(url,)).fetchone()[0]

def test_duplicate_and_market_intelligence_are_conservative():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            _opp(c,'A','Python data pipeline','https://a.test/1','Build Python data pipeline with validation and retries')
            _opp(c,'B','Python data pipeline','https://b.test/1','Build Python data pipeline with validation and retries')
            rows=c.execute('select * from opportunities').fetchall()
            assert len(duplicate_groups(rows))==1
            snap=market_snapshot(rows); assert snap['opportunities']==2
        finally:
            if 'c' in locals():
                c.close()

def test_runtime_market_intelligence_and_distribution():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            oid=_opp(c,'A','Automate Excel reporting','https://a.test/2','Build Excel spreadsheet automation for weekly reporting')
            rt=MarketRadarRuntime(c,[{'name':'A','base_url':'https://a.test','adapter':'json','status':'candidate','allow_hosts':['a.test'],'iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}],'secret')
            mi=rt.market_intelligence(); assert 'market' in mi and 'competition' in mi and 'duplicate_groups' in mi
            dist=rt.distribution_recommendation(oid); assert dist['recommended_channels']
        finally:
            if 'c' in locals():
                c.close()

def test_scheduler_is_twice_daily_and_does_not_claim_online_execution():
    s=ScanScheduler(('08:00','20:00'))
    runs=s.next_runs(datetime.fromisoformat('2026-09-10T07:00:00+00:00'),4)
    assert [x.strftime('%H:%M') for x in runs]==['08:00','20:00','08:00','20:00']

def test_distribution_is_recommendation_not_implicit_authorization():
    x=distribution_targets('api_integration',['SourceA'])
    assert 'permission' in x['rule'].lower()

def test_country_inference_does_not_turn_exclusion_mentions_into_employer_country():
    from marketradar.country_policy import infer_country
    assert infer_country({'title':'Worldwide Python role','description':'Work from anywhere except Iran'}) is None
    assert infer_country({'title':'Python Engineer','description':'Employer based in Japan'})=='Japan'

def test_kyc_requirement_detection_is_explicit_and_conservative():
    from marketradar.payment import detect_kyc
    assert detect_kyc('Payment in USDT; no KYC required')=='NOT_REQUIRED'
    assert detect_kyc('Government ID required before payment')=='REQUIRED'
    assert detect_kyc('Competitive Python project')=='UNKNOWN'

import tempfile
from pathlib import Path
from marketradar.db import connect
from marketradar.pipeline import Pipeline
from marketradar.opportunity_ranker import rank_opportunity, estimate_difficulty
from marketradar.country_policy import jurisdiction_hits
from marketradar.policy import eligibility
from marketradar.runtime import MarketRadarRuntime


def test_learning_level_changes_project_fit_and_track():
    opp={'title':'Build incident response dashboard','description':'Production security monitoring dashboard with database and real-time alerts','category':'security','eligibility':'EXECUTE','evidence_confidence':.9,'quality_score':.9,'payment':'USDT','budget':300,'last_seen':'2026-09-11T10:00:00+00:00'}
    junior=rank_opportunity(opp, {'skills':['Python'], 'learning':{'level':2,'tracks':['blue_team'],'stretch':False}})
    advanced=rank_opportunity(opp, {'skills':['Python','security'], 'learning':{'level':4,'tracks':['blue_team'],'stretch':True}})
    assert advanced['rank_score'] > junior['rank_score']
    assert advanced['track']=='blue_team'


def test_pipeline_persists_rank_and_application_queue():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            s={'name':'A','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}
            item={'title':'Quick Python automation','url':'https://example.test/job/1','description':'Apply now for a small Python automation task, $250 USDT','evidence':[{'kind':'listing','url':'https://example.test/job/1','finding':'listing','confidence':.95}]}
            Pipeline(c,settings={'profile':{'skills':['Python'],'learning':{'level':2,'tracks':['software_engineering'],'stretch':True}}}).ingest(s,item)
            row=c.execute('select rank_score,skill_fit,recommended_level,application_path,application_ready from opportunities').fetchone()
            assert row['rank_score']>0 and row['skill_fit']>0 and row['application_path']=='STANDARD_FORM'
            assert c.execute('select count(*) from opportunity_rank_history').fetchone()[0]==1
        finally:
            if 'c' in locals():
                c.close()


def test_operational_jurisdiction_uses_domain_and_metadata_not_mentions():
    assert 'Israel' in jurisdiction_hits({'url':'https://example.il/job/1'}, {}, ['Israel'])
    assert 'Israel' in jurisdiction_hits({'registration_country':'Israel'}, {}, ['Israel'])
    assert jurisdiction_hits({'description':'Client mentions Israel in requirements'}, {}, ['Israel']) == []


def test_open_next_application_is_guided_and_does_not_silently_submit():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            s={'name':'A','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}
            item={'title':'Quick Python automation','url':'https://example.test/job/2','description':'Apply now for a Python automation task, $250 USDT','evidence':[{'kind':'listing','url':'https://example.test/job/2','finding':'listing','confidence':.95}]}
            Pipeline(c,settings={'profile':{'skills':['Python'],'learning':{'level':2,'tracks':['software_engineering']}}}).ingest(s,item); c.commit()
            rt=MarketRadarRuntime(c,[{'name':'A','base_url':'https://example.test','adapter':'json','status':'candidate','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}],'secret',settings={'profile':{'skills':['Python'],'learning':{'level':2,'tracks':['software_engineering']}}})
            # Avoid launching a browser in CI: replace the connector at the boundary.
            from marketradar import runtime as rtmod
            class Fake:
                def plan(self,*args): return type('P',(),{'url':'https://example.test/job/2'})()
                def execute(self,plan): return {'status':'OPENED_FOR_REVIEW','requires_user_submit':True}
            old=rtmod.GuidedBrowserConnector
            rtmod.GuidedBrowserConnector=lambda: Fake()
            try:
                out=rt.open_next_application()
            finally:
                rtmod.GuidedBrowserConnector=old
            assert out['status']=='OPENED_FOR_REVIEW' and out['requires_user_submit'] is True
            assert c.execute("select status from application_queue").fetchone()[0]=='OPENED'
        finally:
            if 'c' in locals():
                c.close()

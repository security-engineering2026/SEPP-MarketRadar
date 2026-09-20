import tempfile
from pathlib import Path
from marketradar.db import connect
from marketradar.opportunity_signals import extract_signals
from marketradar.opportunity_ranker import rank_opportunity
from marketradar.outcome_learning import record_outcome, update_learning_snapshot
from marketradar.application_adapters import AdapterRegistry, SourceApplicationAdapter
from marketradar.browser_recovery import BrowserRecovery


def test_deadline_and_proposal_extraction():
    s=extract_signals({'title':'urgent Python task','description':'finish by 2026-09-20, 7 proposals'})
    assert s['deadline_at'].startswith('2026-09-20')
    assert s['proposal_count']==7 and s['deadline_confidence']>0.8


def test_client_reputation_is_evidence_weighted():
    s=extract_signals({'description':'client rating 4.8/5, 120 reviews','client_rating':4.8,'client_reviews':120,'hire_rate':92,'payment_verified':True})
    assert s['client_reputation_score']>0.85


def test_acceptance_and_revenue_change_rank():
    base={'title':'Python automation','description':'small automation apply now','category':'python_debugging','eligibility':'EXECUTE','evidence_confidence':.95,'quality_score':.95,'budget':1000,'last_seen':'2026-09-11T10:00:00+00:00'}
    low=rank_opportunity({**base,'acceptance_probability':.2,'expected_value':200},{'skills':['Python'],'learning':{'level':2,'tracks':['software_engineering'],'stretch':True}})
    high=rank_opportunity({**base,'acceptance_probability':.9,'expected_value':900},{'skills':['Python'],'learning':{'level':2,'tracks':['software_engineering'],'stretch':True}})
    assert high['rank_score']>low['rank_score']


def test_outcome_learning_uses_source_and_category_priors():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            c.execute("INSERT INTO opportunities(source,title,url,description,category,eligibility,state,budget) VALUES('A','a','https://a/1','x','python_debugging','EXECUTE','DISCOVERED',100)")
            oid=c.execute('select id from opportunities').fetchone()[0]
            # Build historical outcome for same source/category.
            c.execute("INSERT INTO opportunities(source,title,url,description,category,eligibility,state,budget) VALUES('A','b','https://a/2','x','python_debugging','EXECUTE','DISCOVERED',100)")
            oid2=c.execute('select max(id) from opportunities').fetchone()[0]
            for _ in range(3): record_outcome(c,oid2,'ACCEPTED')
            c.commit()
            snap=update_learning_snapshot(c,oid)
            assert snap['acceptance_probability']>0.6 and snap['expected_value']>60
        finally:
            if 'c' in locals():
                c.close()


def test_source_specific_adapter_registry_and_browser_recovery():
    class Flaky(SourceApplicationAdapter):
        def __init__(self): self.n=0; self.source_key='flaky'
        def execute(self,plan):
            self.n+=1
            if self.n==1: raise RuntimeError('temporary browser failure')
            return {'status':'OPENED_FOR_REVIEW','requires_user_submit':True}
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            c.execute("INSERT INTO opportunities(source,title,url,description,category,eligibility,state,budget) VALUES('A','a','https://a/1','x','general_software','EXECUTE','DISCOVERED',100)")
            oid=c.execute('select id from opportunities').fetchone()[0]
            reg=AdapterRegistry(); reg.register_source('A',Flaky)
            adapter=reg.resolve('A','https://a/1')
            plan=adapter.plan({'id':oid,'url':'https://a/1'},{},'proposal')
            result=BrowserRecovery(c,base_delay=0).execute(oid,adapter,plan)
            assert result['attempts']==2 and result['recovered'] is True
            assert c.execute('select count(*) from application_attempts').fetchone()[0]==2
        finally:
            if 'c' in locals():
                c.close()

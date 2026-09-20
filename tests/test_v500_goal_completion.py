import sqlite3, sys
from datetime import datetime, timezone
sys.path.insert(0,'.')
from marketradar.db import connect
from marketradar.goal_completion import (
    resolve_entity, link_party, analyze_reviews, build_demand_clusters,
    calculate_ttm, decision_center, authorize_action, execute_authorized,
    record_financial, refresh_revenue_intelligence, product_engine,
    workflow_event, VERSION,
)


def seed(c):
    now=datetime.now(timezone.utc).isoformat()
    rows=[
        ('s1','Python Excel Automation','https://a.example/1','automate Excel with Python', 'excel_automation',500,'USD','USDT',.95, .9,'EXECUTE',80,30,'DISCOVERED',now,now,'US',None,'EXECUTE'),
        ('s2','Python Excel Automation','https://b.example/1','clean Excel data with Python', 'data_cleaning',600,'USD','USDT',.9,.88,'EXECUTE',78,28,'DISCOVERED',now,now,'US',None,'EXECUTE'),
        ('s3','RFP automation','https://c.example/1','RFP procurement automation', 'business_automation',2000,'USD','FIAT/UNKNOWN',.8,.8,'REVIEW',50,96,'DISCOVERED',now,now,'DE',None,'REVIEW'),
    ]
    for x in rows:
        c.execute('''INSERT INTO opportunities(source,title,url,description,category,budget,currency,payment,evidence_confidence,quality_score,eligibility,score,time_to_money,state,first_seen,last_seen,country,rejection_reason,application_ready) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',x[:-1]+(1 if x[-1]=='EXECUTE' else 0,))
    c.commit()


def test_goal_completion_and_identity_review_demand_ttm():
    c=connect(':memory:'); seed(c)
    e1=resolve_entity(c,'Client','Acme Labs',domain='acme.example',country='US')
    e2=resolve_entity(c,'Client','Acme Labs',domain='acme.example',country='US')
    assert e1==e2
    link_party(c,e1,'Client',behavior={'reputation_score':.9})
    now=datetime.now(timezone.utc).isoformat()
    for i in range(5):
        c.execute('INSERT INTO reviews(party_entity_id,source,author_key,text,rating,observed_at,provenance_root,verified) VALUES(?,?,?,?,?,?,?,?)',(e1,'review','a'+str(i),'Great service',5,now,'same-root',1))
    review=analyze_reviews(c,e1)
    assert review['independent_provenance_count']==1
    assert 'PROVENANCE_CONCENTRATION' in review['flags'] or 'COPY_PASTE' in review['flags']
    rows=[dict(r) for r in c.execute('select * from opportunities')]
    clusters=build_demand_clusters(c,rows)
    assert clusters
    pred=calculate_ttm(c,1)
    assert pred['expected_hours']>0 and pred['p_paid']>0


def test_bound_authorization_is_one_time_and_workflow_is_idempotent():
    c=connect(':memory:'); seed(c)
    c.execute('insert into evidence(opportunity_id,kind,source,url,finding,confidence,provenance_root,observed_at,evidence_hash) values(?,?,?,?,?,?,?,?,?)',(1,'listing','s1','https://a.example/1','verified',.9,'s1',datetime.now(timezone.utc).isoformat(),'e1'))
    aid=authorize_action(c,'OPEN_APPLICATION','https://a.example/1',{'opportunity_id':1},[1],'policy-v5','human',ttl_seconds=60)
    result=execute_authorized(c,aid,'OPEN_APPLICATION','https://a.example/1',{'opportunity_id':1},[1],lambda:{'ok':True})
    assert result['ok'] is True
    try:
        execute_authorized(c,aid,'OPEN_APPLICATION','https://a.example/1',{'opportunity_id':1},[1],lambda:{'ok':True})
        assert False
    except ValueError as e:
        assert str(e)=='AUTH_ALREADY_USED'
    k1=workflow_event(c,'wf-1',1,'SUBMIT','SUBMITTED',{'x':1},attempt=1)
    k2=workflow_event(c,'wf-1',1,'SUBMIT','SUBMITTED',{'x':1},attempt=1)
    assert k1==k2
    assert c.execute("select count(*) from workflow_events where workflow_id='wf-1'").fetchone()[0]==1


def test_finance_product_and_decision_outputs():
    c=connect(':memory:'); seed(c)
    record_financial(c,1,500,'USD',fees=50,work_hours=5,source='test')
    refresh_revenue_intelligence(c)
    ri=c.execute("select * from revenue_intelligence where dimension='source' and dimension_key='s1'").fetchone()
    assert ri and ri['net']==450 and ri['net_per_hour']==90
    build_demand_clusters(c,[dict(r) for r in c.execute('select * from opportunities')])
    recs=product_engine(c)
    assert recs
    dc=decision_center(c)
    assert len(dc['top7'])==3
    from marketradar import __version__
    assert VERSION==__version__

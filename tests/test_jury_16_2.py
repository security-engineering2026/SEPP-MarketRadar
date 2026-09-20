from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone
import json
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from marketradar.db import connect, sync_source_contracts
from marketradar.operations import ensure_schema as ensure_operations_schema, record_contract, project_report
from marketradar.application import transition
from marketradar.email_service import ensure_schema as ensure_email_schema, add_account, create_draft, approve, process_inbox_messages
from marketradar.discovery_intelligence import QueryPlanner
from marketradar.android_gateway import AndroidGateway, _Handler


def make_db():
    td=TemporaryDirectory(); c=connect(Path(td.name)/'x.db'); ensure_operations_schema(c); ensure_email_schema(c)
    src={'name':'Iran_Platform','base_url':'https://iran.example','adapter':'html','status':'active','allow_hosts':['iran.example'],'country':'Iran','region':'Iran','language':'fa','source_lane':'EXECUTION_ELIGIBLE','policy_lane':'EXECUTION_ELIGIBLE','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'IRR','execution_ready':True}
    sync_source_contracts(c,[src])
    now=datetime.now(timezone.utc).isoformat()
    c.execute("INSERT INTO opportunities(id,source,title,url,description,budget,currency,eligibility,state,first_seen,last_seen,category,task_type,work_domain) VALUES(1,'Iran_Platform','Excel project','https://iran.example/1','Excel',15000000,'IRR','EXECUTE','SUBMITTED',?,?,?,?,?)",(now,now,'services','excel_cleaning','data_processing'))
    c.commit()
    return td,c


def test_email_reply_updates_application_lifecycle_and_communication():
    td,c=make_db()
    try:
        add_account(c,'main','user@example.test',password_env='X')
        aid=c.execute('SELECT id FROM email_accounts WHERE name="main"').fetchone()['id']
        did=create_draft(c,'client@example.test','Excel project','Proposal',1,aid)
        # Simulate sent-thread Message-ID without touching SMTP.
        mid='<sent-1@marketradar.test>'
        c.execute('UPDATE email_drafts SET status="SENT",message_id=? WHERE id=?',(mid,did)); c.commit()
        r=process_inbox_messages(c,aid,[{'message_id':'<reply-1@test>','in_reply_to':mid,'references':mid,'from':'client@example.test','subject':'Re: Excel project - Congratulations','body':'You are selected.','date':'2026-09-18T10:00:00+00:00'}])
        assert r[0]['opportunity_id']==1 and r[0]['transitioned'] is True
        assert c.execute('SELECT state FROM opportunities WHERE id=1').fetchone()['state']=='ACCEPTED'
        assert c.execute('SELECT COUNT(*) n FROM project_communications WHERE opportunity_id=1').fetchone()['n']==1
    finally: td.cleanup()


def test_email_reply_rejection_is_tracked():
    td,c=make_db()
    try:
        add_account(c,'main','user@example.test',password_env='X'); aid=c.execute('SELECT id FROM email_accounts').fetchone()['id']
        did=create_draft(c,'client@example.test','Excel project','Proposal',1,aid); mid='<sent-2@marketradar.test>'
        c.execute('UPDATE email_drafts SET status="SENT",message_id=? WHERE id=?',(mid,did)); c.commit()
        r=process_inbox_messages(c,aid,[{'message_id':'<reply-2@test>','in_reply_to':mid,'references':mid,'from':'client@example.test','subject':'Re: Excel project - Not selected','body':'We declined the proposal.','date':'2026-09-18T10:00:00+00:00'}])
        assert r[0]['intent']=='REJECTED' and r[0]['transitioned'] is True
        assert c.execute('SELECT state FROM opportunities WHERE id=1').fetchone()['state']=='REJECTED'
    finally: td.cleanup()


def test_priority_query_planner_puts_iran_in_high_priority_bucket():
    cfg={'priority_queries':[{'id':'iran_priority','country':'Iran','region':'Iran','language':'fa','family':'freelance','q':'Iran freelance services'}], 'priority_regions':[{'country':'Iran','priority_boost':5.0}], 'queries':[{'id':'global','country':'Global','region':'Global','language':'multi','family':'community','q':'global forum'}], 'country_templates':[], 'community_domains':[]}
    plans=QueryPlanner(cfg).plan(max_queries=2)
    assert plans[0]['country']=='Iran' and plans[0]['operator_score']>plans[1]['operator_score']


def test_android_gateway_rejects_bad_token():
    td,c=make_db()
    try:
        class R:
            def operation_dashboard(self): return {}
            def issue_submission_approval(self,*a,**k): raise AssertionError
        g=AndroidGateway(c,R(),'secret')
        assert g.token_ok('secret') is True and g.token_ok('wrong') is False
    finally: td.cleanup()

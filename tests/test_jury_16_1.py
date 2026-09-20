import json, tempfile, zipfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from marketradar.db import connect, sync_source_contracts
from marketradar.finance import add_account, route_source_account, record_payment_to_account, period_report, export_report
from marketradar.operations import ensure_schema as ensure_operations_schema, record_contract, operation_tick, project_report, source_application_gate
from marketradar.notifications import unread
from marketradar.email_service import add_account as add_email_account, create_draft, approve, send
from marketradar.application import transition
from marketradar.application_package import build_application_package
from marketradar.android_bridge import AndroidBridge
from marketradar.recommendation_engine import _eligible_rows
from marketradar.source_verification import SourceVerificationEngine


def base_db():
    td=tempfile.TemporaryDirectory(); c=connect(Path(td.name)/'x.db'); ensure_operations_schema(c)
    source={'name':'Iran_Platform','base_url':'https://iran.example','adapter':'html','status':'active','allow_hosts':['iran.example'],'source_lane':'EXECUTION_ELIGIBLE','policy_lane':'DAILY_PROJECT_SCAN','country':'Iran','region':'Iran','language':'fa','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'IRR','access_scope':'public','source_family':'freelance','source_role':'freelance','verification_state':'verified','terms_status':'reviewed','execution_ready':True}
    sync_source_contracts(c,[source])
    c.execute("INSERT INTO opportunities(id,source,title,url,description,budget,currency,eligibility,state,first_seen,last_seen,category,task_type,work_domain) VALUES(1,'Iran_Platform','پروژه Excel','https://iran.example/1','Excel cleaning job',15000000,'IRR','EXECUTE','DISCOVERED',?,?, 'excel_automation','excel_cleaning','data_processing')",(datetime.now(timezone.utc).isoformat(),datetime.now(timezone.utc).isoformat()))
    c.commit(); return td,c


def test_finance_accounts_routing_reports_and_project_report():
    td,c=base_db()
    try:
        a1=add_account(c,'IRR Main','IRR',institution='Local Bank',iban='IR123'); a2=add_account(c,'USD Crypto','USDT',account_type='WALLET',wallet='ignored')
        route_source_account(c,'Iran_Platform',a1['id'],'local payout route')
        record_contract(c,1,accepted_at='2026-09-18T10:00:00+00:00',started_at='2026-09-18T11:00:00+00:00',deadline_at='2026-09-20T10:00:00+00:00',agreed_amount=15000000,currency='IRR')
        transition(c,1,'ELIGIBILITY_CHECK','system'); transition(c,1,'RECOMMENDED','system'); transition(c,1,'APPROVAL_PENDING','system'); transition(c,1,'SUBMITTED','human'); transition(c,1,'VIEWED','system'); transition(c,1,'MESSAGE_RECEIVED','system'); transition(c,1,'NEGOTIATION','system'); transition(c,1,'ACCEPTED','human'); transition(c,1,'IN_PROGRESS','human'); transition(c,1,'DELIVERED','human')
        record_payment_to_account(c,1,15000000,'IRR','BANK-1',account_id=a1['id'],client='Client A',project='Excel',source='Iran_Platform',received_at='2026-09-19T09:00:00+00:00')
        report=project_report(c,1)
        assert report['finance_entries'][0]['account_name']=='IRR Main'
        assert any(x['payment_ref']=='BANK-1' for x in report['finance_entries'])
        r=period_report(c,'monthly'); assert r['revenue'][0]['currency']=='IRR'
        out=Path(td.name)/'reports'; files=export_report(c,r,out)
        for ext in ('json','md','csv','xlsx','html','pdf'): assert Path(files[ext]).exists()
        assert '@page{size:A4' in Path(files['html']).read_text(encoding='utf-8')
        with zipfile.ZipFile(files['xlsx']) as z: assert 'xl/workbook.xml' in z.namelist()
        assert Path(files['pdf']).read_bytes().startswith(b'%PDF-1.4')
    finally:
        c.close()
        td.cleanup()


def test_source_constraints_are_persisted_and_gate_recommendations():
    td,c=base_db()
    try:
        eng=SourceVerificationEngine(c,[{'name':'Iran_Platform','base_url':'https://iran.example','adapter':'html','status':'active','allow_hosts':['iran.example'],'policy_lane':'DAILY_PROJECT_SCAN'}])
        result={'source':'Iran_Platform','source_constraints':[{'key':'max_pending_applications','value_int':1,'value_text':'Only 1 active proposal at a time','confidence':0.95,'evidence_url':'https://iran.example/terms'}], 'source_verification_state':'LIVE_CONFIRMED','status':'active','iran_eligibility':'ALLOW','kyc_requirement':'NOT_REQUIRED','payment_capabilities':['FIAT_OR_PLATFORM_PAYOUT'],'payout_evidence_url':'https://iran.example/pay','kyc_evidence_url':None,'terms_evidence_url':'https://iran.example/terms','evidence_confidence':.95,'evidence_urls':['https://iran.example/terms'],'execution_ready':True,'source_lane':'EXECUTION_ELIGIBLE','policy_lane':'DAILY_PROJECT_SCAN','verification_state':'verified','terms_status':'reviewed','last_verified_at':datetime.now(timezone.utc).isoformat()}
        eng.persist([result])
        c.execute("UPDATE opportunities SET state='SUBMITTED' WHERE id=1") if False else None
        gate=source_application_gate(c,'Iran_Platform')
        # at zero pending, it stays allowed
        assert gate['allowed']
        c.execute("INSERT INTO opportunities(id,source,title,url,eligibility,state,first_seen,last_seen,task_type,work_domain) VALUES(2,'Iran_Platform','open','https://iran.example/2','EXECUTE','SUBMITTED',?,?, 'excel_cleaning','data_processing')",(datetime.now(timezone.utc).isoformat(),datetime.now(timezone.utc).isoformat()))
        c.commit(); gate2=source_application_gate(c,'Iran_Platform')
        assert gate2['allowed'] is False and gate2['reason']=='PENDING_APPLICATION_LIMIT'
        assert _eligible_rows(c)==[]
    finally:
        c.close()
        td.cleanup()


def test_notifications_deadline_and_email_approval_gate():
    td,c=base_db()
    try:
        record_contract(c,1,deadline_at=(datetime.now(timezone.utc)+timedelta(hours=4)).isoformat())
        transition(c,1,'ELIGIBILITY_CHECK','system')
        transition(c,1,'RECOMMENDED','system')
        transition(c,1,'APPROVAL_PENDING','system')
        transition(c,1,'SUBMITTED','human')
        operation_tick(c)
        assert any(x['kind']=='DEADLINE' for x in unread(c))
        add_email_account(c,'main','user@example.test',smtp_host='smtp.example.test',password_env='MR_SMTP_PASSWORD')
        account=c.execute('SELECT id FROM email_accounts WHERE name="main"').fetchone()['id']
        draft=create_draft(c,'client@example.test','Project update','Ready.',1,account)
        try: send(c,draft)
        except PermissionError: pass
        else: raise AssertionError('EMAIL_SEND_MUST_REQUIRE_APPROVAL')
        approve(c,draft)
        row=c.execute('SELECT status FROM email_drafts WHERE id=?',(draft,)).fetchone(); assert row['status']=='APPROVED'
    finally:
        c.close()
        td.cleanup()


def test_profile_package_localized_and_android_device_binding():
    td,c=base_db()
    try:
        p={'name':'User','skills':['Excel','Python'],'summary':'automation','projects':['Excel automation'],'portfolio':['repo://demo']}
        item=dict(c.execute('SELECT * FROM opportunities WHERE id=1').fetchone())
        pack=build_application_package(p,item,language='fa',target_amount=12000000,target_currency='IRR')
        assert 'proposal' in pack and 'resume' in pack
        assert 'بودجه پیشنهادی' in pack['proposal'] and 'IRR' in pack['proposal']
        b=AndroidBridge('secret',c); b.bind_device('phone-1','device-token'); assert b.authorize_device('phone-1','device-token') is True; assert b.authorize_device('phone-1','wrong') is False
    finally:
        c.close()
        td.cleanup()

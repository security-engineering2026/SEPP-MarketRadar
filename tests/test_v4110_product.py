import json, subprocess, sys, tempfile
from pathlib import Path

from marketradar.country_policy import apply_blacklist, evaluate_iran_access
from marketradar.payment import detect_payment, validate_crypto_payment
from marketradar.policy import eligibility
from marketradar.opportunity_intelligence import analyze_need
from marketradar.resume import tailored_resume
from marketradar.proposal import generate_proposal
from marketradar.db import connect
from marketradar.pipeline import Pipeline
from marketradar.runtime import MarketRadarRuntime
from marketradar.application_connectors import AuthorizedApiConnector

ROOT=Path(__file__).parents[1]

def test_country_policy_blocks_iran_and_israel_and_does_not_guess_iran_access():
    assert 'Israel' in apply_blacklist({'country':'Israel'}, ['Iran','Israel'])
    assert 'Iran' not in apply_blacklist({'country':'Iran'}, ['Israel'])
    assert evaluate_iran_access({'title':'Worldwide role'}, {'iran_status':'UNKNOWN'})[0]=='UNKNOWN'
    assert eligibility({'iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}, True, {'country':'Israel'}, {'execution_blacklist_countries':['Israel']})[0]=='BLOCK'
    assert eligibility({'country':'Israel','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}, True, {}, {'execution_blacklist_countries':['Israel']})[0]=='BLOCK'

def test_crypto_payment_is_structured_not_just_a_currency_string():
    p=detect_payment('Pay 250 USDT on TRC20')
    assert p['method']=='CRYPTO' and p['asset']=='USDT' and p['network']=='TRC20' and p['verified'] is False
    assert validate_crypto_payment('USDT','TRC20',None,250)[0]
    assert not validate_crypto_payment('NOPE',None,None,1)[0]

def test_need_analysis_tool_proposal_resume_and_proposal_are_real_capabilities():
    opp={'id':1,'title':'Automate Excel reporting','description':'Build a Python automation that cleans spreadsheets and creates a weekly report.'}
    n=analyze_need(opp)
    assert n['tool_name']=='Spreadsheet Automation Tool'
    profile={'name':'Candidate','skills':['Python','Pandas'],'projects':['AssetWatch']}
    assert 'TARGETED SKILLS' in tailored_resume(profile,opp)
    assert 'Spreadsheet Automation Tool' in generate_proposal(profile,opp)

def test_runtime_persists_tool_proposal_and_manual_submission_plan():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            s={'name':'A','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}
            Pipeline(c).ingest(s,{'title':'Business automation','url':'https://example.test/job/1','description':'Build a small automation workflow for $100 USDT','evidence':[{'kind':'listing','url':'https://example.test/job/1','finding':'listing','confidence':.9}]})
            c.commit(); oid=c.execute('select id from opportunities').fetchone()[0]
            rt=MarketRadarRuntime(c,[{'name':'A','base_url':'https://example.test','adapter':'json','status':'candidate','allow_hosts':['example.test'],'iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}],'secret')
            result=rt.analyze_opportunity(oid); assert result['tool_name']=='Business Workflow Tool'
            plan=rt.create_submission_plan(oid,{'name':'Candidate','skills':['Python']})
            assert plan.mode=='MANUAL' and plan.authorization_required
            assert c.execute('select count(*) from tool_proposals').fetchone()[0]==1
            assert c.execute('select count(*) from application_plans').fetchone()[0]==1
        finally:
            if 'c' in locals():
                c.close()

def test_crypto_revenue_records_network_and_unverified_state():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/t','DELIVERED')"); c.commit(); oid=c.execute('select id from opportunities').fetchone()[0]
            from marketradar.application import record_revenue
            record_revenue(c,oid,25,'USDT','2026-09-10T10:00:00Z','invoice-1',network='TRC20')
            row=c.execute('select currency,payment_network,verification_state from revenue').fetchone()
            assert tuple(row)==('USDT','TRC20','RECORDED_UNVERIFIED')
        finally:
            if 'c' in locals():
                c.close()

def test_product_audit_reports_cross_region_and_platform_coverage():
    out=subprocess.run([sys.executable,'tools/product_audit.py'],cwd=ROOT,text=True,capture_output=True,check=True)
    data=json.loads(out.stdout)
    assert data['sources']>=20
    assert {'Middle East','East Asia','Eastern Europe','Caucasus'} <= set(data['regions'])
    assert {'telegram','reddit','x','linkedin'} <= set(data['families'])


def test_authorized_submission_requires_explicit_connector_capability_and_can_execute_with_injected_sender():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); s={'name':'A','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}
            Pipeline(c).ingest(s,{'title':'Python automation','url':'https://example.test/job/2','description':'Build business automation for $100 USDT','evidence':[{'kind':'listing','url':'https://example.test/job/2','finding':'listing','confidence':.9}]}); c.commit(); oid=c.execute('select id from opportunities').fetchone()[0]
            rt=MarketRadarRuntime(c,[{'name':'A','base_url':'https://example.test','adapter':'json','status':'candidate','allow_hosts':['example.test'],'iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed','execution_capability':'authorized_api'}],'secret')
            sent=[]
            connector=AuthorizedApiConnector(lambda fields: sent.append(fields) or {'status':'SUBMITTED'})
            result=rt.execute_submission_plan(oid,connector,{'name':'Candidate','skills':['Python']})
            assert result['status']=='SUBMITTED' and sent
        finally:
            if 'c' in locals():
                c.close()


def test_regional_and_platform_parsers_handle_structured_inputs():
    from marketradar.source_parsers import parse_hh, parse_html_jobs, parse_telegram_bot
    hh=b'{"items":[{"name":"Python Engineer","alternate_url":"https://hh.ru/vacancy/1","area":{"name":"Moscow"},"salary":{"from":100000,"currency":"RUR"}}]}'
    assert parse_hh(hh,'https://api.hh.ru/vacancies')[0]['title']=='Python Engineer'
    html=b'<html><a href="https://example.test/job/1">Python automation job</a></html>'
    assert parse_html_jobs(html,'https://example.test/jobs')[0]['url']=='https://example.test/job/1'
    tg=b'{"ok":true,"result":[{"channel_post":{"message_id":7,"text":"Python automation opportunity","chat":{"username":"publicchannel"}}}]}'
    assert parse_telegram_bot(tg,'https://api.telegram.org')[0]['url']=='https://t.me/publicchannel/7'

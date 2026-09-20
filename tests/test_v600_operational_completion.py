import json
from datetime import datetime, timezone
from pathlib import Path

from marketradar.db import connect
from marketradar.operational_completion import ProviderConfig, AuthorizedHttpExecutor, prepare_browser_action, record_delivery, operational_gate
from marketradar.application import transition


def seed(c, state='IN_PROGRESS'):
    now=datetime.now(timezone.utc).isoformat()
    c.execute('''INSERT INTO opportunities(source,title,url,description,category,budget,currency,payment,evidence_confidence,quality_score,eligibility,score,time_to_money,state,first_seen,last_seen,application_ready) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              ('s','Test','https://example.test/1','x','test',100,'USD','USD',.9,.9,'EXECUTE',.9,10,state,now,now,1))
    c.commit()


def test_delivery_requires_real_artifact_and_moves_state(tmp_path):
    c=connect(':memory:'); seed(c)
    artifact=tmp_path/'deliverable.txt'; artifact.write_text('hello',encoding='utf-8')
    result=record_delivery(c,1,str(artifact))
    assert result['status']=='DELIVERED'
    assert c.execute('select state from opportunities where id=1').fetchone()[0]=='DELIVERED'
    assert c.execute('select count(*) from delivery_evidence').fetchone()[0]==1


def test_browser_action_is_prepare_only():
    payload=prepare_browser_action({'id':1,'url':'https://example.test'}, {'name':'x'}, 'proposal')
    assert payload['requires_user_submit'] is True
    assert payload['mode']=='GUIDED_BROWSER'


def test_http_executor_requires_explicit_endpoint_and_token():
    p=ProviderConfig('p','AUTHORIZED_API',(),endpoint=None,token_env='TOKEN',enabled=True)
    try:
        AuthorizedHttpExecutor(p).execute({'id':1},{},'x')
        assert False
    except Exception as exc:
        assert 'ENDPOINT' in str(exc)


def test_operational_gate_reports_external_runtime_gates():
    c=connect(':memory:'); seed(c)
    gate=operational_gate(c)
    assert 'external_runtime_gates' in gate
    assert gate['external_runtime_gates']['human_approval']=='REQUIRED_FOR_ACTION'


def test_full_operational_lifecycle_with_local_authorized_provider(tmp_path):
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from marketradar.operational_completion import submit_with_approval, record_payment

    received=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            n=int(self.headers.get('Content-Length','0')); received.append(self.rfile.read(n)); self.send_response(201); self.end_headers(); self.wfile.write(b'{"accepted":true}')
        def log_message(self,*args): pass
    server=HTTPServer(('127.0.0.1',0),Handler); threading.Thread(target=server.serve_forever,daemon=True).start()
    c=connect(':memory:'); seed(c,state='APPROVAL_PENDING')
    now=datetime.now(timezone.utc).isoformat()
    c.execute('INSERT INTO evidence(opportunity_id,kind,source,url,finding,confidence,provenance_root,observed_at,evidence_hash) VALUES(?,?,?,?,?,?,?,?,?)',(1,'listing','s','https://example.test/1','live listing',.95,'s',now,'ev1')); c.commit()
    provider=ProviderConfig('local','AUTHORIZED_API',(),endpoint=f'http://127.0.0.1:{server.server_port}/submit',enabled=True)
    result=submit_with_approval(c,dict(c.execute('select * from opportunities where id=1').fetchone()),{},'proposal',[1],provider=provider)
    assert result['status']=='SUBMITTED' and received
    transition(c,1,'MESSAGE_RECEIVED','client'); transition(c,1,'NEGOTIATION','client'); transition(c,1,'ACCEPTED','client'); transition(c,1,'IN_PROGRESS','human')
    artifact=tmp_path/'out.txt'; artifact.write_text('done',encoding='utf-8'); record_delivery(c,1,str(artifact))
    transition_state=c.execute('select state from opportunities where id=1').fetchone()[0]; assert transition_state=='DELIVERED'
    pay=record_payment(c,1,100,'USD','PAY-LOCAL')
    assert pay['status']=='RECORDED_UNVERIFIED'
    assert c.execute('select state from opportunities where id=1').fetchone()[0]=='DELIVERED'
    from marketradar.application import verify_payment
    verify_payment(c,1,'PAY-LOCAL','VERIFIED')
    assert c.execute('select state from opportunities where id=1').fetchone()[0]=='PAID'
    server.shutdown()

def test_authorization_rejects_missing_or_foreign_evidence():
    from marketradar.goal_completion import authorize_action
    c=connect(':memory:'); seed(c,state='APPROVAL_PENDING')
    try:
        authorize_action(c,'SUBMIT_APPLICATION','https://example.test/1',{'opportunity_id':1},[999],'v6','human')
        assert False
    except ValueError as exc:
        assert str(exc)=='AUTH_EVIDENCE_NOT_FOUND'
    now=datetime.now(timezone.utc).isoformat()
    c.execute('''INSERT INTO opportunities(source,title,url,description,category,budget,currency,payment,evidence_confidence,quality_score,eligibility,score,time_to_money,state,first_seen,last_seen,application_ready) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',('s','Other','https://example.test/2','x','test',100,'USD','USD',.9,.9,'EXECUTE',.9,10,'APPROVAL_PENDING',now,now,1))
    c.execute('INSERT INTO evidence(opportunity_id,kind,source,url,finding,confidence,provenance_root,observed_at,evidence_hash) VALUES(?,?,?,?,?,?,?,?,?)',(2,'listing','s','https://example.test/2','other',.9,'s',now,'foreign-ev')); c.commit()
    try:
        authorize_action(c,'SUBMIT_APPLICATION','https://example.test/1',{'opportunity_id':1},[1],'v6','human')
        assert False
    except ValueError as exc:
        assert str(exc)=='AUTH_EVIDENCE_TARGET_MISMATCH'
    c.close()

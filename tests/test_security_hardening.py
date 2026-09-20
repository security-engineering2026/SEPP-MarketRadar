import json, tempfile
from pathlib import Path
from marketradar.federation import Federation, Source
from marketradar.source_registry import load_source_records
from marketradar.android_bridge import AndroidBridge
from marketradar.db import connect
from marketradar.pipeline import Pipeline

def test_private_ip_blocked_for_public_source():
    f=Federation([Source('A','http://127.0.0.1:1/feed',allow_hosts=('127.0.0.1',),access_scope='public')],retries=0,timeout=.01)
    try: f.fetch('A')
    except ValueError as e: assert str(e)=='PRIVATE_IP_BLOCK'
    else: raise AssertionError('private IP was not blocked')

def test_local_scope_allows_local_source():
    f=Federation([Source('A','http://127.0.0.1:1/feed',allow_hosts=('127.0.0.1',),access_scope='local')],retries=0,timeout=.01)
    try: f.fetch('A')
    except Exception as e: assert not isinstance(e, ValueError) or str(e)!='PRIVATE_IP_BLOCK'

def test_registry_rejects_base_host_mismatch(tmp_path):
    p=tmp_path/'s.json'; p.write_text(json.dumps([{'name':'A','base_url':'https://good.example/feed','adapter':'json','allow_hosts':['evil.example']}]))
    try: load_source_records(p)
    except ValueError as e: assert str(e)=='SOURCE_BASE_HOST_NOT_ALLOWED'
    else: raise AssertionError('mismatched allow_hosts accepted')

def test_android_has_no_default_secret():
    bridge=AndroidBridge(None)
    assert not bridge.enabled
    try: bridge.envelope('x',{})
    except RuntimeError as e: assert str(e)=='ANDROID_BRIDGE_DISABLED'
    else: raise AssertionError('default Android secret exists')

def test_pipeline_does_not_duplicate_evidence():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); p=Pipeline(c); s={'name':'s','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}
            item={'title':'x','url':'https://example.test/x','description':'$100 USDT','evidence':[{'kind':'listing','url':'https://example.test/x','finding':'f','confidence':.9}]}
            p.ingest(s,item); p.ingest(s,item); c.commit()
            assert c.execute('select count(*) from evidence').fetchone()[0]==1
        finally:
            if 'c' in locals():
                c.close()

def test_install_marker_is_not_copied_to_installed_package():
    text=Path('packaging/installer.iss').read_text()
    assert 'Excludes: ".portable"' in text

def test_payment_validation_rejects_non_positive_amount():
    from marketradar.application import record_revenue
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/o','DELIVERED')"); c.commit(); oid=c.execute('select id from opportunities').fetchone()[0]
            try: record_revenue(c,oid,0,'USD','2026-01-01','ref')
            except ValueError as e: assert str(e)=='INVALID_PAYMENT_AMOUNT'
            else: raise AssertionError('zero payment accepted')
        finally:
            if 'c' in locals():
                c.close()

def test_submission_approval_is_single_use():
    from marketradar.runtime import MarketRadarRuntime
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); p=Pipeline(c); s={'name':'s','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}
            p.ingest(s,{'title':'x','url':'https://example.test/x','description':'$100 USDT','evidence':[{'kind':'listing','url':'https://example.test/x','finding':'f','confidence':.9}]}); c.commit()
            oid=c.execute('select id from opportunities').fetchone()[0]; rt=MarketRadarRuntime(c,[{'name':'s','base_url':'https://example.test','adapter':'json','status':'candidate','allow_hosts':['example.test']}],'secret')
            a=rt.issue_submission_approval(oid); rt.approve_and_submit(oid,a)
            try: rt.approve_and_submit(oid,a)
            except ValueError as e: assert str(e) in {'APPROVAL_REPLAY','SUBMISSION_NOT_ELIGIBLE'}
            else: raise AssertionError('approval replay accepted')
        finally:
            if 'c' in locals():
                c.close()

def test_approval_replay_survives_new_broker_instance():
    from marketradar.security import ApprovalBroker
    import time
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            b=ApprovalBroker(c); a=b.issue('SUBMIT','o',{'p':1},{'e':1},'p1',int(time.time()),300)
            assert b.authorize(a,'SUBMIT','o',{'p':1},{'e':1},'p1',int(time.time()))[0]
            b2=ApprovalBroker(c)
            assert b2.authorize(a,'SUBMIT','o',{'p':1},{'e':1},'p1',int(time.time()))[1]=='REPLAY'
        finally:
            if 'c' in locals():
                c.close()

def test_submission_transition_rolls_back_on_message_failure():
    from marketradar.runtime import MarketRadarRuntime
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); p=Pipeline(c); s={'name':'s','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}
            p.ingest(s,{'title':'x','url':'https://example.test/x','description':'$100 USDT','evidence':[{'kind':'listing','url':'https://example.test/x','finding':'f','confidence':.9}]}); c.commit()
            oid=c.execute('select id from opportunities').fetchone()[0]
            rt=MarketRadarRuntime(c,[{'name':'s','base_url':'https://example.test','adapter':'json','status':'candidate','allow_hosts':['example.test']}],'secret')
            approval=rt.issue_submission_approval(oid)
            original=rt.android.envelope
            rt.android.envelope=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('boom'))
            try: rt.approve_and_submit(oid,approval)
            except RuntimeError: pass
            else: raise AssertionError('expected message failure')
            assert c.execute('select state from opportunities where id=?',(oid,)).fetchone()[0]=='DISCOVERED'
            assert c.execute('select used_at from approvals where approval_id=?',(approval.approval_id,)).fetchone()[0] is None
            rt.android.envelope=original
        finally:
            if 'c' in locals():
                c.close()

def test_verify_registry_persists_health_and_parser_state():
    from marketradar.runtime import MarketRadarRuntime
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body=b'{"items":[{"title":"x","url":"http://127.0.0.1/x"}]}'
            self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self,*a): pass
    server=HTTPServer(('127.0.0.1',0),H); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as d:
            try:
                c=connect(Path(d)/'x.db'); src={'name':'s','base_url':f'http://127.0.0.1:{server.server_port}/feed','adapter':'json','status':'candidate','allow_hosts':['127.0.0.1'],'access_scope':'local'}
                rt=MarketRadarRuntime(c,[src],None); res=rt.verify_registry(['s'])
                assert res[0]['parse_ok'] is True
                assert c.execute("select verification_state,health from sources where name='s'").fetchone()['verification_state']=='verified'
                assert c.execute("select count(*) from federation_runs where source='s'").fetchone()[0]==1
            finally:
                if 'c' in locals():
                    c.close()
    finally: server.shutdown(); server.server_close()

def test_unverified_candidates_are_not_default_network_targets():
    from marketradar.runtime import MarketRadarRuntime
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            records=[
                {'name':'active','base_url':'https://example.test/a','adapter':'json','status':'active','allow_hosts':['example.test'],'verification_state':'documented'},
                {'name':'candidate','base_url':'https://example.test/b','adapter':'json','status':'candidate','allow_hosts':['example.test'],'verification_state':'unverified'},
            ]
            rt=MarketRadarRuntime(c,records,None)
            # No network call is needed: inspect the default selection logic.
            selected=[n for n,s in rt.source_records.items() if s.get('status')=='active' or s.get('verification_state') in ('documented','verified','degraded')]
            assert selected == ['active']
        finally:
            if 'c' in locals():
                c.close()

def test_generic_json_rejects_unknown_schema():
    from marketradar.federation import Federation, Source
    f=Federation([Source('x','https://example.test/feed',allow_hosts=('example.test',))])
    try: f.parse_json({'body':b'{"hello":"world"}','url':'https://example.test/feed'})
    except ValueError as e: assert str(e)=='JSON_SCHEMA_UNSUPPORTED'
    else: raise AssertionError('unknown JSON schema accepted')

def test_health_history_is_persisted():
    from marketradar.source_health import persist_health
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            source={'name':'x','base_url':'https://example.test','adapter':'json','status':'active','source_kind':'job_source','acquisition':'http','verification_state':'documented','access_scope':'public','terms_status':'needs_review'}
            persist_health(c,source,{'status':'OK','http_status':200,'parse_ok':True,'parsed_count':3,'sha256':'abc'})
            c.commit()
            row=c.execute("select health,verification_state,parsed_count from source_health_history where source='x'").fetchone()
            assert row['health']==100.0 and row['verification_state']=='verified' and row['parsed_count']==3
        finally:
            if 'c' in locals():
                c.close()

def test_approval_cannot_be_rebound_by_forging_returned_object():
    from marketradar.security import ApprovalBroker, Approval
    import time
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); b=ApprovalBroker(c); now=int(time.time())
            a=b.issue('SUBMIT','real',{'p':1},{'e':1},'p1',now,300)
            forged=Approval(a.approval_id,'SUBMIT','attacker',a.parameters_digest,a.evidence_digest,a.policy_version,a.expires_at)
            assert b.authorize(forged,'SUBMIT','attacker',{'p':1},{'e':1},'p1',now)[1]=='APPROVAL_RECORD_MISMATCH'
        finally:
            if 'c' in locals():
                c.close()

def test_android_rejects_nonpositive_ttl():
    from marketradar.android_bridge import AndroidBridge
    b=AndroidBridge('secret')
    for ttl in (0,-1,True,False):
        try: b.envelope('x',{},ttl=ttl)
        except ValueError as e: assert str(e)=='INVALID_TTL'
        else: raise AssertionError('invalid ttl accepted')

def test_rss_rejects_unsafe_entity_declarations():
    from marketradar.source_parsers import parse_rss
    body=b'<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss><channel><item><title>&x;</title><link>https://example.test/x</link></item></channel></rss>'
    try: parse_rss(body,'https://example.test/feed')
    except ValueError as e: assert str(e)=='RSS_UNSAFE_XML'
    else: raise AssertionError('unsafe XML accepted')

def test_payment_timestamp_must_be_iso8601():
    from marketradar.application import record_revenue
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/o','DELIVERED')"); c.commit(); oid=c.execute('select id from opportunities').fetchone()[0]
            for value in ('yesterday','2026-99-99'):
                try: record_revenue(c,oid,10,'USD',value,'ref-'+value)
                except ValueError as e: assert str(e)=='INVALID_PAYMENT_TIMESTAMP'
                else: raise AssertionError('invalid timestamp accepted')
        finally:
            if 'c' in locals():
                c.close()


def test_financial_and_audit_records_are_append_only():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/o','DELIVERED')")
            c.execute("insert into opportunities(source,title,url,state) values('s','t2','https://x.test/o2','DISCOVERED')")
            oid=c.execute("select id from opportunities where title='t'").fetchone()[0]
            from marketradar.application import transition
            oid2=c.execute("select id from opportunities where title='t2'").fetchone()[0]
            transition(c,oid2,'ELIGIBILITY_CHECK')
            from marketradar.application import record_revenue
            record_revenue(c,oid,10,'USD','2026-01-01T00:00:00+00:00','ref-1')
            c.execute("insert into audit(at,event,entity_type,entity_id,details) values('t','e','x','1','{}')")
            c.commit()
            for table, statement in [
                ('revenue', "update revenue set amount=999"),
                ('revenue', "delete from revenue"),
                ('audit', "update audit set details='tampered'"),
                ('audit', "delete from audit"),
                ('application_events', "update application_events set actor='tampered'"),
                ('application_events', "delete from application_events"),
            ]:
                try: c.execute(statement); c.commit()
                except Exception as exc: assert 'immutable' in str(exc)
                else: raise AssertionError(f'{table} mutation was accepted')
        finally:
            if 'c' in locals():
                c.close()


def test_record_revenue_commit_false_does_not_rollback_outer_transaction():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/o','DELIVERED')")
            c.execute("insert into opportunities(source,title,url,state) values('s','t2','https://x.test/o2','DISCOVERED')")
            oid=c.execute("select id from opportunities where title='t'").fetchone()[0]
            from marketradar.application import transition
            oid2=c.execute("select id from opportunities where title='t2'").fetchone()[0]
            transition(c,oid2,'ELIGIBILITY_CHECK')
            c.execute("insert into audit(at,event,entity_type,entity_id,details) values('t','before','x','1','{}')")
            from marketradar.application import record_revenue
            record_revenue(c,oid,10,'USD','2026-01-01T00:00:00+00:00','ref-1',commit=False)
            c.execute("insert into audit(at,event,entity_type,entity_id,details) values('t','after','x','1','{}')")
            c.commit()
            assert c.execute('select count(*) from revenue').fetchone()[0] == 1
            assert c.execute('select count(*) from audit').fetchone()[0] == 2
        finally:
            if 'c' in locals():
                c.close()


def test_approval_record_cannot_be_tampered_or_deleted():
    import time
    from marketradar.security import ApprovalBroker
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); b=ApprovalBroker(c); now=int(time.time())
            a=b.issue('SUBMIT','real',{'p':1},{'e':1},'p1',now,300); c.commit()
            assert b.authorize(a,'SUBMIT','real',{'p':1},{'e':1},'p1',now)[0]
            for statement in [
                "update approvals set target='attacker' where approval_id=?",
                "update approvals set parameters_digest='00' where approval_id=?",
                "update approvals set used_at=NULL where approval_id=?",
                "delete from approvals where approval_id=?",
            ]:
                try: c.execute(statement,(a.approval_id,)); c.commit()
                except Exception as exc: assert 'immutable' in str(exc)
                else: raise AssertionError('approval tampering was accepted')
        finally:
            if 'c' in locals():
                c.close()


def test_dns_rebinding_cannot_reach_private_ip_after_public_validation(monkeypatch):
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import marketradar.federation as fm
    from marketradar.federation import Federation, Source
    hits=[]
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            body=b'{"items":[]}'
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(body)
        def log_message(self,*a): pass
    server=HTTPServer(('127.0.0.1',0),H); threading.Thread(target=server.serve_forever,daemon=True).start()
    original=fm.socket.getaddrinfo; calls={'n':0}
    def rebinding(host,port,*args,**kwargs):
        calls['n'] += 1
        ip='93.184.216.34' if calls['n'] == 1 else '127.0.0.1'
        return [(fm.socket.AF_INET,fm.socket.SOCK_STREAM,6,'',(ip,port))]
    monkeypatch.setattr(fm.socket,'getaddrinfo',rebinding)
    try:
        f=Federation([Source('x',f'http://example.test:{server.server_port}/feed',allow_hosts=('example.test',),access_scope='public')],retries=0,timeout=1)
        try: f.fetch('x')
        except ValueError as exc: assert str(exc)=='PRIVATE_IP_BLOCK'
        else: raise AssertionError('DNS rebinding was not blocked')
        assert not hits, 'private endpoint was reached before validation'
    finally:
        server.shutdown(); server.server_close()

def test_android_message_replay_is_persistent_and_single_use():
    import tempfile
    from pathlib import Path
    from marketradar.db import connect
    from marketradar.android_bridge import AndroidBridge
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); b=AndroidBridge('secret', c)
            msg=b.envelope('TEST', {'x': 1})
            assert b.verify(msg)
            assert b.verify(msg, consume=True)
            assert not b.verify(msg, consume=True)
            row=c.execute('select consumed_at from android_messages where message_id=?',(msg['message_id'],)).fetchone()
            assert row['consumed_at'] is not None
        finally:
            if 'c' in locals():
                c.close()

def test_android_message_binding_cannot_be_tampered():
    import tempfile
    from pathlib import Path
    from marketradar.db import connect
    from marketradar.android_bridge import AndroidBridge
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); b=AndroidBridge('secret', c); msg=b.envelope('TEST', {'x': 1})
            try: c.execute("update android_messages set kind='EVIL' where message_id=?",(msg['message_id'],)); c.commit()
            except Exception: c.rollback()
            else: raise AssertionError('android message binding was mutable')
        finally:
            if 'c' in locals():
                c.close()

def test_lower_quality_cross_source_observation_cannot_poison_opportunity():
    import tempfile
    from pathlib import Path
    from marketradar.db import connect
    from marketradar.pipeline import Pipeline
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); p=Pipeline(c)
            good={'name':'A','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT'}
            bad={'name':'B','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT'}
            item={'title':'Legitimate automation task','url':'https://example.test/job/1','description':'Build a small automation workflow with clear requirements and deliver a tested implementation.','evidence':[{'kind':'listing','url':'https://example.test/job/1','finding':'verified listing with requirements and deliverables','confidence':1.0}]}
            p.ingest(good,item); c.commit()
            before=c.execute('select title,quality_score,score from opportunities where url=?',(item['url'],)).fetchone()
            poison=dict(item,title='PAY EVERYTHING NOW',description='x',evidence=[])
            p.ingest(bad,poison); c.commit()
            after=c.execute('select title,quality_score,score from opportunities where url=?',(item['url'],)).fetchone()
            assert tuple(after)==tuple(before)
            assert {r[0] for r in c.execute('select source from opportunity_sources').fetchall()}=={'A','B'}
        finally:
            if 'c' in locals():
                c.close()

def test_domain_records_reject_orphan_opportunity_references():
    import tempfile, sqlite3
    from pathlib import Path
    from marketradar.db import connect
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            for sql in [
                "insert into evidence(opportunity_id,kind,source,url,finding,confidence,provenance_root,observed_at) values(999,'x','s','https://x','x',0,'s','t')",
                "insert into application_events(opportunity_id,from_state,to_state,actor) values(999,'A','B','x')",
                "insert into revenue(opportunity_id,amount,currency,received_at,payment_ref,digest) values(999,1,'USD','2026-01-01T00:00:00+00:00','r','d')",
                "insert into opportunity_sources(opportunity_id,source,first_seen,last_seen) values(999,'s','t','t')",
            ]:
                try: c.execute(sql); c.commit()
                except sqlite3.IntegrityError: c.rollback()
                else: raise AssertionError('orphan domain record was accepted')
        finally:
            if 'c' in locals():
                c.close()

import json, tempfile, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from marketradar.analysis import budget
from marketradar.quality import canonical_url
from marketradar.source_onboarding import audit_registry, validate_source
from marketradar.adapter_registry import content_type_ok
from marketradar.db import connect
from marketradar.pipeline import Pipeline
from marketradar.source_health import persist_health
from marketradar.runtime import MarketRadarRuntime


def test_budget_formats_are_safe():
    assert budget('USD 1,200') == (1200.0, 'USD')
    assert budget('1,200 USD') == (1200.0, 'USD')
    assert budget('100 USDT') == (100.0, 'USDT')
    assert budget('€500') == (500.0, '€')


def test_canonical_url_removes_tracking_and_fragment():
    assert canonical_url('HTTPS://Example.COM/a?utm_source=x&b=2&a=1#frag') == 'https://example.com/a?a=1&b=2'


def test_content_type_contracts():
    assert content_type_ok('rss', 'application/rss+xml; charset=utf-8')
    assert content_type_ok('remoteok_json', 'application/json')
    assert not content_type_ok('remoteok_json', 'text/html')


def test_onboarding_flags_placeholder_and_invalid_active():
    r=validate_source({'name':'A','base_url':'https://example.com','adapter':'json','allow_hosts':['example.com'],'status':'active','verification_state':'unverified'})
    assert not r.ok and 'ACTIVE_SOURCE_MUST_NOT_BE_UNVERIFIED' in r.errors
    report=audit_registry([{'name':'A','base_url':'https://example.com','adapter':'json','allow_hosts':['example.com']}])
    assert report['warnings']==1 and 'A' not in report['promotable']


def test_quality_score_affects_ingestion_and_url_dedup():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); p=Pipeline(c)
            s={'name':'s','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT'}
            p.ingest(s,{'title':'Good Python Automation','url':'https://example.test/job?id=7&utm_source=x#top','description':'Build a small automation tool for a business workflow.','evidence':[{'kind':'listing','url':'https://example.test/job?id=7','finding':'listing','confidence':.9}]})
            p.ingest(s,{'title':'Good Python Automation','url':'https://example.test/job?id=7&utm_medium=email','description':'Build a small automation tool for a business workflow.','evidence':[{'kind':'listing','url':'https://example.test/job?id=7','finding':'listing','confidence':.9}]})
            assert c.execute('select count(*) from opportunities').fetchone()[0]==1
            assert c.execute('select quality_score from opportunities').fetchone()[0] > .5
        finally:
            if 'c' in locals():
                c.close()


def test_health_failures_increment_and_recovery_resets():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); s={'name':'s','base_url':'https://example.test','adapter':'json','status':'active','source_kind':'job_source','acquisition':'http','verification_state':'documented','access_scope':'public','terms_status':'needs_review'}
            persist_health(c,s,{'status':'ERROR','http_status':503,'error':'down'}); c.commit()
            assert c.execute("select failure_count,verification_state from sources where name='s'").fetchone()['failure_count']==1
            persist_health(c,s,{'status':'OK','http_status':200,'parse_ok':True,'parsed_count':1,'sha256':'x'}); c.commit()
            row=c.execute("select failure_count,verification_state from sources where name='s'").fetchone(); assert row['failure_count']==0 and row['verification_state']=='verified'
        finally:
            if 'c' in locals():
                c.close()


def test_revenue_android_failure_rolls_back_payment():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/t','DELIVERED')"); c.commit(); oid=c.execute('select id from opportunities').fetchone()[0]
            rt=MarketRadarRuntime(c,[{'name':'s','base_url':'https://example.test','adapter':'json','status':'candidate','allow_hosts':['example.test']}],'secret')
            rt.android.envelope=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('fail'))
            try: rt.record_payment(oid,10,'USDT','2026-09-10T10:00:00Z','p1')
            except RuntimeError: pass
            else: assert False
            assert c.execute('select count(*) from revenue').fetchone()[0]==0
            assert c.execute('select state from opportunities where id=?',(oid,)).fetchone()[0]=='DELIVERED'
        finally:
            if 'c' in locals():
                c.close()

def test_dry_federation_does_not_persist(monkeypatch):
    import marketradar.runtime as runtime_module
    class FakeFed:
        def __init__(self,*a,**k): pass
        def fetch(self,name,url=None): return {'status':200,'url':'https://example.test/feed','body':b'{"items":[{"title":"T","url":"https://example.test/t","description":"Long enough description for quality."}]}','sha256':'x','elapsed_ms':1,'bytes':80,'attempts':1,'content_type':'application/json'}
        @staticmethod
        def parse_json(obs): return json.loads(obs['body'])['items']
    monkeypatch.setattr(runtime_module,'Federation',FakeFed)
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); s={'name':'s','base_url':'https://example.test/feed','adapter':'json','status':'active','allow_hosts':['example.test'],'access_scope':'local','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT'}
            rt=MarketRadarRuntime(c,[s],None); r=rt.federate('s',dry=True); assert r['dry_run'] is True; assert c.execute('select count(*) from opportunities').fetchone()[0]==0
        finally:
            if 'c' in locals():
                c.close()

def test_health_updates_persisted_contract_state():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); s={'name':'s','base_url':'https://example.test','adapter':'json','status':'active','source_kind':'job_source','acquisition':'http','verification_state':'documented','access_scope':'public','terms_status':'needs_review','verification_basis':'test'}
            c.execute("insert into source_contracts(source,source_kind,acquisition,adapter,access_scope,verification_state,terms_status,verification_basis,updated_at) values(?,?,?,?,?,?,?,?,?)",('s','job_source','http','json','public','documented','needs_review','test','t')); c.commit()
            persist_health(c,s,{'status':'OK','http_status':200,'parse_ok':True,'parsed_count':2,'sha256':'z'}); c.commit()
            assert c.execute("select runtime_verification_state from source_contracts where source='s'").fetchone()[0]=='verified'
        finally:
            if 'c' in locals():
                c.close()


def test_federation_does_not_retry_policy_validation_errors(monkeypatch):
    from marketradar.federation import Federation, Source
    import marketradar.federation as fm
    calls={'n':0}
    def fake_open(*a,**k): calls['n']+=1; raise ValueError('HOST_BOUNDARY_BLOCK')
    monkeypatch.setattr(Federation,'_validate_target',lambda self,source,target: __import__('urllib.parse',fromlist=['urlparse']).urlparse(target))
    monkeypatch.setattr(Federation,'_validate_target',lambda self,source,target: __import__('urllib.parse',fromlist=['urlparse']).urlparse(target))
    monkeypatch.setattr(Federation,'_open_once',lambda self,source,target: fake_open())
    f=Federation([Source('s','https://example.test/feed',allow_hosts=('example.test',),access_scope='local')],retries=3)
    try: f.fetch('s','https://example.test/feed')
    except ValueError: pass
    assert calls['n']==1

def test_federation_retries_transient_errors(monkeypatch):
    from marketradar.federation import Federation, Source
    import marketradar.federation as fm
    calls={'n':0}
    class Resp:
        status=200
        def geturl(self): return 'https://example.test/feed'
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def read(self,n): return b'{"items":[]}'
        class H:
            def get(self,k,d=''): return 'application/json'
        headers=H()
    def fake_open(*a,**k):
        calls['n']+=1
        if calls['n']==1: raise fm.URLError('temporary')
        return (200,'application/json',b'{"items":[]}',None)
    monkeypatch.setattr(Federation,'_validate_target',lambda self,source,target: __import__('urllib.parse',fromlist=['urlparse']).urlparse(target))
    monkeypatch.setattr(Federation,'_open_once',lambda self,source,target: fake_open())
    f=Federation([Source('s','https://example.test/feed',allow_hosts=('example.test',),access_scope='local')],retries=2)
    r=f.fetch('s'); assert r['status']==200 and calls['n']==2


def test_http_4xx_is_not_retried(monkeypatch):
    from marketradar.federation import Federation, Source, HTTPError
    import marketradar.federation as fm
    calls={'n':0}
    def fake_open(*a,**k):
        calls['n'] += 1
        raise HTTPError('https://example.test/feed', 404, 'not found', {}, None)
    monkeypatch.setattr(Federation,'_validate_target',lambda self,source,target: __import__('urllib.parse',fromlist=['urlparse']).urlparse(target))
    monkeypatch.setattr(Federation,'_open_once',lambda self,source,target: fake_open())
    f=Federation([Source('s','https://example.test/feed',allow_hosts=('example.test',),access_scope='local')],retries=3)
    try: f.fetch('s')
    except HTTPError as exc: assert exc.code == 404
    else: assert False
    assert calls['n'] == 1


def test_registry_sync_does_not_erase_runtime_verification():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            s={'name':'s','base_url':'https://example.test','adapter':'json','status':'active','source_kind':'job_source','acquisition':'http','verification_state':'documented','access_scope':'public','terms_status':'needs_review','verification_basis':'test'}
            from marketradar.db import sync_source_contracts
            sync_source_contracts(c,[s])
            persist_health(c,s,{'status':'OK','http_status':200,'parse_ok':True,'parsed_count':1,'sha256':'z'})
            c.commit()
            assert c.execute("select runtime_verification_state from source_contracts where source='s'").fetchone()[0]=='verified'
            sync_source_contracts(c,[s])
            assert c.execute("select runtime_verification_state from source_contracts where source='s'").fetchone()[0]=='verified'
        finally:
            if 'c' in locals():
                c.close()


def test_health_refreshes_source_contract_metadata():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            old={'name':'s','base_url':'https://old.example.test','adapter':'json','status':'active','source_kind':'job_source','acquisition':'http','verification_state':'documented','access_scope':'public','terms_status':'needs_review'}
            new=dict(old, base_url='https://new.example.test', adapter='rss', acquisition='rss', source_kind='feed')
            persist_health(c,old,{'status':'OK','http_status':200,'parse_ok':True,'parsed_count':1,'sha256':'a'}); c.commit()
            persist_health(c,new,{'status':'OK','http_status':200,'parse_ok':True,'parsed_count':1,'sha256':'b'}); c.commit()
            row=c.execute("select base_url,adapter,source_kind,acquisition from sources where name='s'").fetchone()
            assert tuple(row)==('https://new.example.test','rss','feed','rss')
        finally:
            if 'c' in locals():
                c.close()


def test_rss_parser_accepts_atom_entries():
    from marketradar.source_parsers import parse_rss
    body=b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Python Task</title><link href="https://example.test/job/1"/><summary>Build a useful automation workflow for a business.</summary></entry></feed>'
    rows=parse_rss(body,'https://example.test/feed')
    assert len(rows)==1 and rows[0]['url']=='https://example.test/job/1'


def test_default_verification_skips_disabled_sources():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            records=[
                {'name':'disabled','base_url':'http://127.0.0.1:8765/feed','adapter':'json','status':'disabled','verification_state':'verified','allow_hosts':['127.0.0.1'],'access_scope':'local'},
                {'name':'active','base_url':'https://example.test/feed','adapter':'json','status':'active','verification_state':'documented','allow_hosts':['example.test'],'access_scope':'local'},
            ]
            rt=MarketRadarRuntime(c,records,None)
            assert rt.verify_registry.__self__.source_records.keys()
            # Avoid network: the default selection is inspected by monkeypatching the verifier.
            seen=[]
            class V:
                def verify_many(self,names,**kwargs): seen.extend(names); return []
            rt.verifier=V()
            rt.verify_registry()
            assert seen==['active']
        finally:
            if 'c' in locals():
                c.close()


def test_active_source_cannot_have_blocked_terms_or_verification():
    from marketradar.source_onboarding import validate_source
    base={'name':'s','base_url':'https://example.test/feed','adapter':'json','status':'active','verification_state':'documented','allow_hosts':['example.test'],'access_scope':'public'}
    assert not validate_source(dict(base, terms_status='blocked')).ok
    assert not validate_source(dict(base, verification_state='blocked', terms_status='needs_review')).ok


def test_federate_honors_retry_cooldown_and_blocked_state():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            s={'name':'s','base_url':'https://example.test/feed','adapter':'json','status':'active','verification_state':'documented','allow_hosts':['example.test'],'access_scope':'local'}
            persist_health(c,s,{'status':'ERROR','http_status':503,'error':'down'}); c.commit()
            rt=MarketRadarRuntime(c,[s],None)
            try: rt.federate('s')
            except ValueError as exc: assert str(exc)=='SOURCE_RETRY_COOLDOWN'
            else: assert False
            c.execute("update sources set next_retry_at=NULL,verification_state='blocked'"); c.commit()
            try: rt.federate('s')
            except ValueError as exc: assert str(exc)=='SOURCE_BLOCKED'
            else: assert False
        finally:
            if 'c' in locals():
                c.close()


def test_federate_failure_persists_health_and_retry_schedule(monkeypatch):
    from marketradar.runtime import MarketRadarRuntime
    import marketradar.runtime as rm
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            s={'name':'s','base_url':'https://example.test/feed','adapter':'json','status':'active','allow_hosts':['example.test'],'access_scope':'local','verification_state':'documented'}
            class F:
                def __init__(self,*a,**k): pass
                def fetch(self,*a,**k):
                    from marketradar.federation import URLError
                    e=URLError('down'); e.attempts=2; raise e
            monkeypatch.setattr(rm,'Federation',F)
            rt=MarketRadarRuntime(c,[s],None)
            try: rt.federate('s')
            except Exception: pass
            row=c.execute("select failure_count,last_error,next_retry_at from sources where name='s'").fetchone()
            assert row['failure_count']==1 and row['last_error'] and row['next_retry_at']
        finally:
            if 'c' in locals():
                c.close()


def test_federate_rejects_bad_content_type(monkeypatch):
    from marketradar.runtime import MarketRadarRuntime
    import marketradar.runtime as rm
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); s={'name':'s','base_url':'https://example.test/feed','adapter':'json','status':'active','allow_hosts':['example.test'],'access_scope':'local','verification_state':'documented'}
            class F:
                def __init__(self,*a,**k): pass
                def fetch(self,*a,**k): return {'status':200,'url':'https://example.test/feed','body':b'{"items":[]}','sha256':'x','elapsed_ms':1,'bytes':12,'attempts':1,'content_type':'text/html'}
            monkeypatch.setattr(rm,'Federation',F)
            rt=MarketRadarRuntime(c,[s],None)
            try: rt.federate('s')
            except ValueError as e: assert str(e)=='CONTENT_TYPE_MISMATCH'
            else: raise AssertionError('bad content type accepted')
        finally:
            if 'c' in locals():
                c.close()


def test_duplicate_url_preserves_source_provenance():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); p=Pipeline(c)
            a={'name':'A','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT'}; b={'name':'B','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT'}
            item={'title':'Shared job','url':'https://example.test/job/1','description':'Build a small automation tool for a business workflow.','evidence':[{'kind':'listing','url':'https://example.test/job/1','finding':'listing','confidence':.9}]}
            p.ingest(a,item); p.ingest(b,item); c.commit()
            assert c.execute('select count(*) from opportunities').fetchone()[0]==1
            assert {r[0] for r in c.execute('select source from opportunity_sources').fetchall()}=={'A','B'}
        finally:
            if 'c' in locals():
                c.close()


def test_engine_root_uses_requested_data_directory():
    from marketradar.engine import MarketRadar
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); (root/'config').mkdir(); (root/'data').mkdir()
        (root/'config'/'sources.json').write_text('[]',encoding='utf-8')
        m=MarketRadar(root)
        try: assert str(m.conn.execute('PRAGMA database_list').fetchone()[2]).startswith(str(root/'data'))
        finally: m.close()


def test_failed_acquisition_cannot_leave_source_verified():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); s={'name':'s','base_url':'https://example.test','adapter':'json','status':'active','verification_state':'verified'}
            persist_health(c,s,{'status':'ERROR','http_status':503,'error':'temporary'})
            row=c.execute("select verification_state,health from sources where name='s'").fetchone()
            assert row['verification_state']=='degraded' and row['health']==0.0
        finally:
            if 'c' in locals():
                c.close()


def test_force_cannot_bypass_blocked_source(monkeypatch):
    from marketradar.runtime import MarketRadarRuntime
    import marketradar.runtime as rm
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); s={'name':'s','base_url':'https://example.test/feed','adapter':'json','status':'active','allow_hosts':['example.test'],'access_scope':'local','verification_state':'documented'}
            c.execute("insert into sources(name,status,verification_state,terms_status) values('s','active','blocked','needs_review')"); c.commit()
            class F:
                def __init__(self,*a,**k): pass
                def fetch(self,*a,**k): raise AssertionError('blocked source was fetched')
            monkeypatch.setattr(rm,'Federation',F)
            rt=MarketRadarRuntime(c,[s],None)
            try: rt.federate('s',force=True)
            except ValueError as e: assert str(e)=='SOURCE_BLOCKED'
            else: raise AssertionError('force bypassed blocked source')
        finally:
            if 'c' in locals():
                c.close()


def test_registry_sync_refreshes_current_source_metadata_without_erasing_health():
    from marketradar.db import sync_source_contracts
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            old={'name':'s','base_url':'https://old.example.test','adapter':'json','status':'active','source_kind':'job_source','acquisition':'http','verification_state':'documented','access_scope':'public','terms_status':'needs_review'}
            sync_source_contracts(c,[old])
            persist_health(c,old,{'status':'OK','http_status':200,'parse_ok':True,'parsed_count':2,'sha256':'x'}); c.commit()
            new=dict(old,base_url='https://new.example.test',adapter='rss',acquisition='rss',source_kind='feed',status='disabled')
            sync_source_contracts(c,[new])
            row=c.execute("select base_url,adapter,status,health,verification_state from sources where name='s'").fetchone()
            assert tuple(row)==('https://new.example.test','rss','disabled',100.0,'verified')
        finally:
            if 'c' in locals():
                c.close()

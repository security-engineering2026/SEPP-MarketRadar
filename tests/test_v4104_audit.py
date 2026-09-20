import json, tempfile, threading, os
import pytest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from marketradar.db import connect, sync_source_contracts
from marketradar.policy import eligibility
from marketradar.runtime import MarketRadarRuntime


def _server():
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body=b'{"items": [{"title":"Audit task","url":"http://127.0.0.1/job/1","description":"Build a useful automation component for the team."}]}'
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(body)
        def log_message(self,*args): pass
    s=HTTPServer(('127.0.0.1',0),H); threading.Thread(target=s.serve_forever,daemon=True).start(); return s


def test_dry_run_is_truly_non_mutating():
    s=_server()
    try:
        with tempfile.TemporaryDirectory() as d:
            try:
                c=connect(Path(d)/'x.db')
                source={'name':'dry','base_url':f'http://127.0.0.1:{s.server_port}/feed','adapter':'json','status':'active','allow_hosts':['127.0.0.1'],'access_scope':'local','verification_state':'documented'}
                rt=MarketRadarRuntime(c,[source],None)
                before={t:c.execute(f'select count(*) from {t}').fetchone()[0] for t in ('raw_observations','opportunities','evidence','federation_runs','source_health_history')}
                result=rt.federate('dry',dry=True)
                after={t:c.execute(f'select count(*) from {t}').fetchone()[0] for t in before}
                assert result['dry_run'] is True and result['observations']==1 and after==before
            finally:
                if 'c' in locals():
                    c.close()
    finally: s.shutdown(); s.server_close()


def test_hard_policy_blocks_dominate_unknown_evidence():
    base={'iran_status':'UNKNOWN','kyc_status':'UNKNOWN','payment_status':'UNKNOWN','terms_status':'needs_review'}
    assert eligibility(dict(base, iran_status='BLOCK'), evidence_ok=False)[0]=='BLOCK'
    assert eligibility(dict(base, iran_status='ALLOW', kyc_status='BLOCK'), evidence_ok=False)[0]=='BLOCK'
    assert eligibility(dict(base, iran_status='ALLOW', terms_status='blocked'), evidence_ok=False)[0]=='BLOCK'


def test_persisted_runtime_block_survives_registry_sync_and_stops_federation():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            source={'name':'blocked','base_url':'https://example.test/feed','adapter':'json','status':'active','allow_hosts':['example.test'],'access_scope':'public','verification_state':'documented','terms_status':'needs_review'}
            sync_source_contracts(c,[source])
            c.execute("update source_contracts set runtime_verification_state='blocked' where source='blocked'"); c.commit()
            sync_source_contracts(c,[source])
            rt=MarketRadarRuntime(c,[source],None)
            try: rt.federate('blocked')
            except ValueError as exc: assert str(exc)=='SOURCE_BLOCKED'
            else: raise AssertionError('persisted runtime block was bypassed after registry sync')
        finally:
            if 'c' in locals():
                c.close()

def test_engine_honors_configured_http_timeout():
    from marketradar.engine import MarketRadar
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); (root/'config').mkdir(); (root/'data').mkdir()
        source={'name':'local','base_url':'http://127.0.0.1/feed','adapter':'json','status':'disabled','allow_hosts':['127.0.0.1'],'access_scope':'local','verification_state':'verified','terms_status':'n/a'}
        (root/'config'/'sources.json').write_text(json.dumps([source]),encoding='utf-8')
        (root/'config'/'settings.json').write_text(json.dumps({'http_timeout':23.5}),encoding='utf-8')
        radar=MarketRadar(root)
        try: assert radar.runtime.federation.timeout==23.5 and radar.runtime.verifier.timeout==23.5
        finally: radar.close()

def test_connect_replaces_legacy_security_triggers_on_upgrade():
    with tempfile.TemporaryDirectory() as d:
        try:
            db=Path(d)/'x.db'
            c=connect(db)
            c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/o','DISCOVERED')")
            oid=c.execute('select id from opportunities').fetchone()[0]
            c.execute('drop trigger opportunity_transition_valid')
            c.execute("create trigger opportunity_transition_valid BEFORE UPDATE OF state ON opportunities BEGIN SELECT 1; END")
            c.commit(); c.close()
            c=connect(db)
            try:
                try:
                    c.execute("update opportunities set state='PAID' where id=?",(oid,)); c.commit()
                except Exception:
                    c.rollback()
                else:
                    raise AssertionError('legacy permissive trigger survived database upgrade')
            finally: c.close()
        finally:
            if 'c' in locals():
                c.close()

def test_connect_migrates_legacy_schema_before_installing_new_triggers():
    import sqlite3
    with tempfile.TemporaryDirectory() as d:
        try:
            db=Path(d)/'legacy.db'
            c=sqlite3.connect(db)
            c.executescript('''
                CREATE TABLE sources(id INTEGER PRIMARY KEY,name TEXT UNIQUE,base_url TEXT,adapter TEXT,type TEXT,status TEXT,verification_state TEXT);
                CREATE TABLE source_contracts(source TEXT PRIMARY KEY,source_kind TEXT,acquisition TEXT,adapter TEXT,access_scope TEXT,verification_state TEXT,terms_status TEXT,verification_basis TEXT,updated_at TEXT);
                CREATE TABLE raw_observations(id INTEGER PRIMARY KEY,source TEXT,url TEXT,observed_at TEXT,payload BLOB,payload_sha256 TEXT,UNIQUE(source,url,payload_sha256));
                CREATE TABLE opportunities(id INTEGER PRIMARY KEY,source TEXT,title TEXT,url TEXT UNIQUE,description TEXT,category TEXT,budget REAL,currency TEXT,payment TEXT,evidence_confidence REAL,quality_score REAL,eligibility TEXT,score REAL,time_to_money REAL,state TEXT,rejection_reason TEXT,first_seen TEXT,last_seen TEXT);
                CREATE TABLE evidence(id INTEGER PRIMARY KEY,opportunity_id INTEGER,kind TEXT,source TEXT,url TEXT,finding TEXT,confidence REAL,provenance_root TEXT,observed_at TEXT,evidence_hash TEXT UNIQUE);
                CREATE TABLE audit(id INTEGER PRIMARY KEY,at TEXT,event TEXT,entity_type TEXT,entity_id TEXT,details TEXT);
                CREATE TABLE application_events(id INTEGER PRIMARY KEY,opportunity_id INTEGER,from_state TEXT,to_state TEXT,actor TEXT,at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE revenue(id INTEGER PRIMARY KEY,opportunity_id INTEGER,amount REAL,currency TEXT,received_at TEXT,payment_ref TEXT UNIQUE,digest TEXT UNIQUE);
                CREATE TABLE approvals(approval_id TEXT PRIMARY KEY,action TEXT,target TEXT,parameters_digest TEXT,evidence_digest TEXT,policy_version TEXT,issued_at INTEGER,expires_at INTEGER,used_at INTEGER);
                CREATE TABLE android_messages(message_id TEXT PRIMARY KEY,kind TEXT,issued_at INTEGER,expires_at INTEGER,consumed_at INTEGER);
                CREATE TABLE opportunity_sources(opportunity_id INTEGER,source TEXT,first_seen TEXT,last_seen TEXT,PRIMARY KEY(opportunity_id,source));
                CREATE TABLE federation_runs(id INTEGER PRIMARY KEY,source TEXT,started_at TEXT,status TEXT,http_status INTEGER,observation_count INTEGER,error TEXT,snapshot_sha256 TEXT);
                CREATE TABLE source_health_history(id INTEGER PRIMARY KEY,source TEXT,checked_at TEXT,status TEXT,http_status INTEGER,health REAL,verification_state TEXT,parse_ok INTEGER,parsed_count INTEGER,error TEXT,snapshot_sha256 TEXT,failure_count INTEGER DEFAULT 0);
                CREATE TABLE source_onboarding_events(id INTEGER PRIMARY KEY,source TEXT,at TEXT,event TEXT,ok INTEGER,errors TEXT,warnings TEXT);
            '''); c.commit(); c.close()
            c=connect(db)
            try:
                cols={r[1] for r in c.execute('pragma table_info(source_contracts)')}
                rawcols={r[1] for r in c.execute('pragma table_info(raw_observations)')}
                assert 'runtime_verification_state' in cols and 'observation_kind' in rawcols
                assert c.execute("select count(*) from sqlite_master where type='trigger'").fetchone()[0] == 68
            finally: c.close()
        finally:
            if 'c' in locals():
                c.close()


def test_raw_attestation_rejects_forged_persisted_hash():
    from marketradar.pipeline import Pipeline, AcquisitionAttestation
    import hashlib
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); p=Pipeline(c)
            payload=b'{"items": []}'
            fake=hashlib.sha256(b'forged').hexdigest()
            c.execute("insert into raw_observations(source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind) values(?,?,?,?,?,?,?,?)", ('s','https://example.test/feed','now',payload,fake,200,'application/json','source_response')); c.commit()
            try:
                p.ingest({'name':'s','iran_status':'UNKNOWN','kyc_status':'UNKNOWN','payment_status':'UNKNOWN'}, {'title':'Valid title','url':'https://example.test/job','description':'This description is long enough to be accepted by the pipeline.'}, AcquisitionAttestation('s','https://example.test/feed',fake,200))
            except ValueError as exc:
                assert str(exc)=='INVALID_ACQUISITION_ATTESTATION'
            else:
                raise AssertionError('forged persisted raw hash was accepted')
        finally:
            if 'c' in locals():
                c.close()

def test_direct_opportunity_state_change_requires_application_event():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/o','DISCOVERED')"); c.commit()
            try:
                c.execute("update opportunities set state='ELIGIBILITY_CHECK' where id=1"); c.commit()
            except Exception as exc:
                c.rollback(); assert 'application event' in str(exc)
            else:
                raise AssertionError('direct state mutation bypassed application event authority')
            from marketradar.application import transition
            transition(c,1,'ELIGIBILITY_CHECK')
            assert c.execute('select state from opportunities where id=1').fetchone()[0]=='ELIGIBILITY_CHECK'
        finally:
            if 'c' in locals():
                c.close()

def test_opportunity_delete_is_blocked_for_audit_integrity():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/o','DISCOVERED')"); c.commit()
            try:
                c.execute('delete from opportunities where id=1'); c.commit()
            except Exception as exc:
                c.rollback(); assert 'immutable' in str(exc)
            else:
                raise AssertionError('opportunity deletion bypassed audit integrity')
        finally:
            if 'c' in locals():
                c.close()

def test_registry_sync_disables_removed_sources_instead_of_erasing_history():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            old={'name':'old','base_url':'https://old.test/feed','adapter':'json','status':'active','allow_hosts':['old.test'],'access_scope':'public','verification_state':'documented'}
            sync_source_contracts(c,[old])
            c.execute("insert into federation_runs(source,started_at,status) values('old','now','OK')"); c.commit()
            sync_source_contracts(c,[])
            assert c.execute("select status from sources where name='old'").fetchone()[0]=='disabled'
            assert c.execute("select count(*) from federation_runs where source='old'").fetchone()[0]==1
        finally:
            if 'c' in locals():
                c.close()

def test_health_persistence_does_not_erase_existing_policy_metadata():
    from marketradar.source_health import persist_health
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            s={'name':'s','base_url':'https://s.test/feed','adapter':'json','status':'active','allow_hosts':['s.test'],'access_scope':'public','verification_state':'documented','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed','execution_mode':'MANUAL','proposal_limit':'10'}
            sync_source_contracts(c,[s])
            persist_health(c, s, {'status':'OK','http_status':200,'parse_ok':True,'parsed_count':1,'sha256':'a'*64}); c.commit()
            row=c.execute("select iran_status,kyc_status,payment_status,execution_mode,proposal_limit from sources where name='s'").fetchone()
            assert tuple(row)==('ALLOW','ALLOW','USDT','MANUAL','10')
        finally:
            if 'c' in locals():
                c.close()

def test_desktop_refresh_dashboard_handles_real_sqlite_rows():
    if os.name != 'nt' and not os.environ.get('DISPLAY'):
        pytest.skip('Tk display is required for this GUI-specific test')
    import tkinter as tk
    from marketradar.desktop import MarketRadarDesktop
    with tempfile.TemporaryDirectory() as d:
        os.environ['MARKETRADAR_DATA_ROOT']=d
        try:
            try: r=tk.Tk()
            except tk.TclError: pytest.skip('Tk display is unavailable')
            app=MarketRadarDesktop(r)
            app.conn.execute("insert into opportunities(source,title,url,description,eligibility,score,state,quality_score,evidence_confidence,time_to_money,first_seen,last_seen) values('s','A title','https://x.test/o','A sufficiently long description for the GUI data path.','EXECUTE',90,'DISCOVERED',.9,.9,10,datetime('now'),datetime('now'))"); app.conn.commit()
            app.refresh_dashboard(); r.update_idletasks(); r.update()
            assert app.action_list.get_children()
            app.close()
        finally:
            os.environ.pop('MARKETRADAR_DATA_ROOT',None)


def test_registry_sync_rolls_back_partial_changes_on_failure():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            good={'name':'good','base_url':'https://good.test/feed','adapter':'json','status':'active','allow_hosts':['good.test'],'access_scope':'public','verification_state':'documented'}
            bad={'name':'bad','base_url':'https://bad.test/feed','adapter':'json','status':'active','allow_hosts':['bad.test'],'access_scope':'public','verification_state':'not-a-state'}
            try: sync_source_contracts(c,[good,bad])
            except Exception: pass
            else: raise AssertionError('invalid registry sync unexpectedly succeeded')
            assert c.execute("select count(*) from sources where name='good'").fetchone()[0]==0
            assert c.execute("select count(*) from sources where name='bad'").fetchone()[0]==0
        finally:
            if 'c' in locals():
                c.close()


def test_dry_run_still_honors_source_blocks_and_retry_cooldown():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            source={'name':'blocked-dry','base_url':'https://example.test/feed','adapter':'json','status':'active','allow_hosts':['example.test'],'access_scope':'public','verification_state':'documented','terms_status':'needs_review'}
            sync_source_contracts(c,[source])
            c.execute("update sources set verification_state='blocked' where name='blocked-dry'"); c.commit()
            rt=MarketRadarRuntime(c,[source],None)
            try: rt.federate('blocked-dry',dry=True)
            except ValueError as exc: assert str(exc)=='SOURCE_BLOCKED'
            else: raise AssertionError('dry-run bypassed source block')
        finally:
            if 'c' in locals():
                c.close()


def test_verify_registry_never_networks_to_persistently_blocked_source():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            source={'name':'blocked-verify','base_url':'https://example.test/feed','adapter':'json','status':'active','allow_hosts':['example.test'],'access_scope':'public','verification_state':'documented','terms_status':'needs_review'}
            sync_source_contracts(c,[source])
            c.execute("update source_contracts set runtime_verification_state='blocked' where source='blocked-verify'"); c.commit()
            rt=MarketRadarRuntime(c,[source],None)
            results=rt.verify_registry(['blocked-verify'])
            assert len(results)==1 and results[0]['error']=='SOURCE_BLOCKED' and results[0]['attempts']==0
        finally:
            if 'c' in locals():
                c.close()


def test_source_and_contract_deletion_are_blocked():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            src={'name':'s','base_url':'https://s.test/feed','adapter':'json','status':'active','allow_hosts':['s.test'],'access_scope':'public','verification_state':'documented'}
            sync_source_contracts(c,[src])
            for table, key in [('sources','name'),('source_contracts','source')]:
                try:
                    c.execute(f'delete from {table} where {key}=?',('s',)); c.commit()
                except Exception as exc:
                    c.rollback(); assert 'immutable' in str(exc)
                else: raise AssertionError(f'{table} deletion bypassed source history protection')
        finally:
            if 'c' in locals():
                c.close()

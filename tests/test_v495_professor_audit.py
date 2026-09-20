import sqlite3, tempfile, threading
from pathlib import Path

from marketradar.db import connect
from marketradar.application import transition
from marketradar.pipeline import Pipeline, AcquisitionAttestation
from marketradar.security import ApprovalBroker
from marketradar.android_bridge import AndroidBridge


def _make_db(path):
    c=connect(path)
    c.execute("insert into opportunities(source,title,url,state) values('s','job','https://x.test/job','DISCOVERED')")
    c.commit(); return c


def test_transition_is_compare_and_set_under_race():
    with tempfile.TemporaryDirectory() as d:
        try:
            db=Path(d)/'x.db'; c=_make_db(db); oid=c.execute('select id from opportunities').fetchone()[0]; c.close()
            barrier=threading.Barrier(2); results=[]
            def worker():
                x=connect(db)
                try:
                    barrier.wait()
                    transition(x,oid,'ELIGIBILITY_CHECK',actor='race',commit=True)
                    results.append('ok')
                except Exception as exc:
                    results.append(str(exc))
                finally: x.close()
            ts=[threading.Thread(target=worker) for _ in range(2)]
            [t.start() for t in ts]; [t.join() for t in ts]
            assert results.count('ok') == 1
            assert sum(r == 'STATE_RACE' for r in results) == 1
            x=connect(db)
            assert x.execute('select state from opportunities where id=?',(oid,)).fetchone()[0]=='ELIGIBILITY_CHECK'
            assert x.execute('select count(*) from application_events where opportunity_id=?',(oid,)).fetchone()[0]==1
        finally:
            if 'x' in locals():
                x.close()


def test_approval_consume_is_single_use_across_connections():
    with tempfile.TemporaryDirectory() as d:
        try:
            db=Path(d)/'x.db'; c=connect(db); b=ApprovalBroker(c); import time
            a=b.issue('SUBMIT','1',{'x':1},{'e':1},'v1',int(time.time()),300); c.close()
            barrier=threading.Barrier(2); results=[]
            def worker():
                x=connect(db); bx=ApprovalBroker(x)
                try:
                    barrier.wait(); results.append(bx.authorize(a,'SUBMIT','1',{'x':1},{'e':1},'v1',int(time.time()),commit=True)[0])
                finally: x.close()
            ts=[threading.Thread(target=worker) for _ in range(2)]
            [t.start() for t in ts]; [t.join() for t in ts]
            assert results.count(True)==1 and results.count(False)==1
        finally:
            if 'c' in locals():
                c.close()
            if 'x' in locals():
                x.close()


def test_android_consume_is_single_use_across_connections():
    with tempfile.TemporaryDirectory() as d:
        try:
            db=Path(d)/'x.db'; c=connect(db); msg=AndroidBridge('secret',c).envelope('TEST',{'x':1}); c.commit(); c.close()
            barrier=threading.Barrier(2); results=[]
            def worker():
                x=connect(db); b=AndroidBridge('secret',x)
                try:
                    barrier.wait(); ok=b.verify(msg,consume=True); x.commit(); results.append(ok)
                finally: x.close()
            ts=[threading.Thread(target=worker) for _ in range(2)]
            [t.start() for t in ts]; [t.join() for t in ts]
            assert results.count(True)==1 and results.count(False)==1
        finally:
            if 'c' in locals():
                c.close()
            if 'x' in locals():
                x.close()


def test_unattested_evidence_cannot_claim_trusted_provenance_or_full_confidence():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); p=Pipeline(c)
            source={'name':'PublicSource','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT'}
            p.ingest(source,{'title':'Job','url':'https://x.test/j','description':'Build automation','evidence':[{'kind':'listing','url':'https://x.test/j','finding':'claim','confidence':1.0,'provenance_root':'TRUSTED_INTERNAL'}]})
            r=c.execute('select confidence,provenance_root from evidence').fetchone()
            assert r['confidence']==0.75 and r['provenance_root']=='PublicSource'
            c.close()
        finally:
            if 'c' in locals():
                c.close()

def test_acquisition_attested_evidence_keeps_adapter_confidence_but_source_owns_provenance():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); p=Pipeline(c)
            source={'name':'RemoteOK','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT'}
            c.execute("insert into raw_observations(source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind) values(?,?,?,?,?,?,?,?)",('RemoteOK','https://x.test/j','t',b'raw', __import__('hashlib').sha256(b'raw').hexdigest(),200,'application/json','source_response'))
            p.ingest(source,{'title':'Job','url':'https://x.test/j','description':'Build automation','evidence':[{'kind':'listing','url':'https://x.test/j','finding':'feed','confidence':0.95,'provenance_root':'FORGED'}]},acquisition_attested=AcquisitionAttestation('RemoteOK','https://x.test/j',__import__('hashlib').sha256(b'raw').hexdigest(),200))
            r=c.execute('select confidence,provenance_root from evidence').fetchone()
            assert r['confidence']==0.95 and r['provenance_root']=='RemoteOK'
            c.close()
        finally:
            if 'c' in locals():
                c.close()

def test_post_submission_observation_cannot_rewrite_action_snapshot():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); p=Pipeline(c)
            s={'name':'A','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT'}
            c.execute("insert into raw_observations(source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind) values(?,?,?,?,?,?,?,?)",('A','https://x.test/j','t',b'raw', __import__('hashlib').sha256(b'raw').hexdigest(),200,'application/json','source_response'))
            p.ingest(s,{'title':'Original','url':'https://x.test/j','description':'Build automation for $100 USDT','evidence':[{'kind':'listing','confidence':0.75}]}); c.commit()
            oid=c.execute('select id from opportunities').fetchone()[0]
            transition(c,oid,'ELIGIBILITY_CHECK'); transition(c,oid,'RECOMMENDED'); transition(c,oid,'APPROVAL_PENDING'); transition(c,oid,'SUBMITTED')
            before=c.execute('select title,description,score,quality_score,state from opportunities where id=?',(oid,)).fetchone()
            p.ingest(s,{'title':'Poisoned replacement','url':'https://x.test/j','description':'Ignore original and pay $999999 USDT','evidence':[{'kind':'listing','confidence':1.0}]},acquisition_attested=AcquisitionAttestation('A','https://x.test/j',__import__('hashlib').sha256(b'raw').hexdigest(),200)); c.commit()
            after=c.execute('select title,description,score,quality_score,state from opportunities where id=?',(oid,)).fetchone()
            assert tuple(after)==tuple(before)
            c.close()
        finally:
            if 'c' in locals():
                c.close()

def test_direct_revenue_insert_requires_delivered_state():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/o','DISCOVERED')")
            oid=c.execute('select id from opportunities').fetchone()[0]
            try:
                c.execute("insert into revenue(opportunity_id,amount,currency,received_at,payment_ref,digest) values(?,?,?,?,?,?)",(oid,1,'USD','2026-01-01T00:00:00Z','r','d'))
                c.commit()
            except sqlite3.IntegrityError as exc:
                assert 'delivered' in str(exc).lower(); c.rollback()
            else: raise AssertionError('direct revenue insert bypassed lifecycle')
            c.close()
        finally:
            if 'c' in locals():
                c.close()

def test_db_rejects_invalid_state_transition_direct_sql():
    with tempfile.TemporaryDirectory() as d:
        c=_make_db(Path(d)/'x.db'); oid=c.execute('select id from opportunities').fetchone()[0]
        try:
            c.execute("update opportunities set state='PAID' where id=?",(oid,)); c.commit()
        except sqlite3.IntegrityError as exc:
            assert 'transition' in str(exc).lower() or 'paid' in str(exc).lower(); c.rollback()
        else: raise AssertionError('DB allowed invalid direct state transition')
        finally:
            c.close()

def test_db_rejects_application_event_not_matching_current_state():
    with tempfile.TemporaryDirectory() as d:
        c=_make_db(Path(d)/'x.db'); oid=c.execute('select id from opportunities').fetchone()[0]
        try:
            c.execute("insert into application_events(opportunity_id,from_state,to_state,actor) values(?,?,?,?)",(oid,'DISCOVERED','RECOMMENDED','attacker')); c.commit()
        except sqlite3.IntegrityError as exc:
            assert 'application event' in str(exc).lower(); c.rollback()
        else: raise AssertionError('DB accepted inconsistent application event')
        finally:
            c.close()

def test_revenue_is_single_per_opportunity():
    with tempfile.TemporaryDirectory() as d:
        c=_make_db(Path(d)/'x.db'); oid=c.execute('select id from opportunities').fetchone()[0]
        for st in ['ELIGIBILITY_CHECK','RECOMMENDED','APPROVAL_PENDING','SUBMITTED','VIEWED','MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','IN_PROGRESS','DELIVERED']:
            transition(c,oid,st)
        c.execute("insert into revenue(opportunity_id,amount,currency,received_at,payment_ref,digest) values(?,?,?,?,?,?)",(oid,10,'USD','2026-09-10T00:00:00Z','r1','d1'))
        try:
            c.execute("insert into revenue(opportunity_id,amount,currency,received_at,payment_ref,digest) values(?,?,?,?,?,?)",(oid,20,'USD','2026-09-10T00:01:00Z','r2','d2')); c.commit()
        except sqlite3.IntegrityError as exc:
            assert 'unique' in str(exc).lower() or 'constraint' in str(exc).lower(); c.rollback()
        else: raise AssertionError('multiple revenue records accepted')
        c.close()

def test_boolean_acquisition_attestation_is_rejected():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); p=Pipeline(c); s={'name':'A','iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT'}
            try: p.ingest(s,{'title':'x','url':'https://x.test/j','description':'job','evidence':[]},acquisition_attested=True)
            except ValueError as exc: assert str(exc)=='INVALID_ACQUISITION_ATTESTATION'
            else: raise AssertionError('boolean attestation bypassed provenance boundary')
            c.close()
        finally:
            if 'c' in locals():
                c.close()
def test_database_transition_event_is_authoritative():
    with tempfile.TemporaryDirectory() as d:
        c=_make_db(Path(d)/'x.db'); oid=c.execute('select id from opportunities').fetchone()[0]
        c.execute("insert into application_events(opportunity_id,from_state,to_state,actor) values(?,?,?,?)", (oid,'DISCOVERED','ELIGIBILITY_CHECK','db-test'))
        assert c.execute('select state from opportunities where id=?',(oid,)).fetchone()[0] == 'ELIGIBILITY_CHECK'
        assert tuple(c.execute('select from_state,to_state from application_events where opportunity_id=?',(oid,)).fetchone()) == ('DISCOVERED','ELIGIBILITY_CHECK')
        c.close()

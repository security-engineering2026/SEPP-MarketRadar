import tempfile
from pathlib import Path
from marketradar.db import connect
from marketradar.pipeline import Pipeline, AcquisitionAttestation

def test_raw_observation_is_actual_acquisition_and_attestation_is_bound():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/"x.db")
            body=b'{"items":[]}'
            import hashlib
            sha=hashlib.sha256(body).hexdigest()
            c.execute("insert into raw_observations(source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind) values(?,?,?,?,?,?,?,?)",('s','https://example.test/feed','t',body,sha,200,'application/json','source_response'))
            c.commit()
            p=Pipeline(c)
            item={'title':'Bound acquisition','url':'https://example.test/job/1','description':'A real task with requirements and deliverables.','evidence':[]}
            p.ingest({'name':'s','iran_status':'UNKNOWN','kyc_status':'UNKNOWN','payment_status':'UNKNOWN'},item,AcquisitionAttestation('s','https://example.test/feed',sha,200))
            assert c.execute('select payload from raw_observations').fetchone()[0] == body
            try:
                p.ingest({'name':'s'},item,AcquisitionAttestation('s','https://example.test/feed','a'*64,200))
            except ValueError as exc:
                assert str(exc)=='INVALID_ACQUISITION_ATTESTATION'
            else:
                raise AssertionError('unbound acquisition attestation accepted')
        finally:
            if 'c' in locals():
                c.close()

def test_evidence_and_provenance_bindings_are_append_only():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/o','DISCOVERED')")
            oid=c.execute('select id from opportunities').fetchone()[0]
            c.execute("insert into evidence(opportunity_id,kind,source,url,finding,confidence,provenance_root,observed_at,evidence_hash) values(?,?,?,?,?,?,?,?,?)",(oid,'listing','s','https://x.test/o','f',.9,'s','t','h'))
            c.execute("insert into opportunity_sources(opportunity_id,source,first_seen,last_seen) values(?,?,?,?)",(oid,'s','t','t'))
            c.commit()
            for sql in (
                "update evidence set confidence=.1",
                "delete from evidence",
                "update opportunity_sources set source='evil'",
                "delete from opportunity_sources",
            ):
                try:
                    c.execute(sql); c.commit()
                except Exception as exc:
                    assert 'immutable' in str(exc)
                else:
                    raise AssertionError('provenance mutation accepted')
        finally:
            if 'c' in locals():
                c.close()

def test_action_snapshot_is_frozen_after_execution_starts():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/o','DISCOVERED')")
            oid=c.execute('select id from opportunities').fetchone()[0]
            c.execute("insert into application_events(opportunity_id,from_state,to_state,actor) values(?,?,?,?)",(oid,'DISCOVERED','ELIGIBILITY_CHECK','system'))
            c.commit()
            try:
                c.execute("update opportunities set title='tampered' where id=?",(oid,)); c.commit()
            except Exception as exc:
                assert 'snapshot' in str(exc)
            else:
                raise AssertionError('action snapshot mutation accepted')
        finally:
            if 'c' in locals():
                c.close()

def test_source_contract_keeps_declared_and_runtime_verification_separate():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            from marketradar.db import sync_source_contracts
            s={'name':'s','base_url':'https://example.test','adapter':'json','status':'active','allow_hosts':['example.test'],'verification_state':'documented','source_kind':'job_source','acquisition':'http','access_scope':'public','terms_status':'needs_review'}
            sync_source_contracts(c,[s])
            row=c.execute("select verification_state,runtime_verification_state from source_contracts where source='s'").fetchone()
            assert row['verification_state']=='documented' and row['runtime_verification_state'] is None
        finally:
            if 'c' in locals():
                c.close()

def test_canonical_url_preserves_ipv6_brackets():
    from marketradar.quality import canonical_url
    assert canonical_url('https://[2001:db8::1]:443/feed') == 'https://[2001:db8::1]/feed'


def test_invalid_access_scope_cannot_disable_public_ip_ssrf_protection():
    from marketradar.source_onboarding import validate_source
    result=validate_source({'name':'bad','base_url':'https://example.test','adapter':'json','status':'active','verification_state':'documented','allow_hosts':['example.test'],'access_scope':'unsafe'})
    assert not result.ok and 'SOURCE_ACCESS_SCOPE_INVALID' in result.errors


def test_active_unsupported_acquisition_family_is_not_operational():
    from marketradar.source_onboarding import validate_source
    result=validate_source({'name':'bad','base_url':'https://example.test','adapter':'json','status':'active','verification_state':'documented','allow_hosts':['example.test'],'access_scope':'public','acquisition':'telegram_api'})
    assert not result.ok and 'ACTIVE_SOURCE_ACQUISITION_UNSUPPORTED' in result.errors


def test_payment_timestamp_requires_timezone():
    from marketradar.application import record_revenue
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); c.execute("insert into opportunities(source,title,url,state) values('s','t','https://x.test/o','DELIVERED')"); c.commit(); oid=c.execute('select id from opportunities').fetchone()[0]
            try: record_revenue(c,oid,10,'USD','2026-01-01T00:00:00','tz')
            except ValueError as exc: assert str(exc)=='INVALID_PAYMENT_TIMESTAMP'
            else: raise AssertionError('naive timestamp accepted')
        finally:
            if 'c' in locals():
                c.close()


def test_policy_hard_blocks_dominate_missing_evidence():
    from marketradar.policy import eligibility
    assert eligibility({'iran_status': 'BLOCK'}, evidence_ok=False)[0] == 'BLOCK'
    assert eligibility({'iran_status': 'ALLOW', 'kyc_status': 'ALLOW', 'payment_status': 'USDT', 'terms_status': 'blocked'}, evidence_ok=False)[0] == 'BLOCK'


def test_dry_federation_does_not_persist_raw_observation(monkeypatch):
    import marketradar.runtime as runtime_module
    class FakeFed:
        def __init__(self,*a,**k): pass
        def fetch(self,name,url=None):
            body=b'{"items":[]}'
            import hashlib
            return {'status':200,'url':'https://example.test/feed','body':body,'sha256':hashlib.sha256(body).hexdigest(),'elapsed_ms':1,'bytes':len(body),'attempts':1,'content_type':'application/json'}
        @staticmethod
        def parse_json(obs):
            return []
    monkeypatch.setattr(runtime_module,'Federation',FakeFed)
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db')
            s={'name':'s','base_url':'https://example.test/feed','adapter':'json','status':'active','allow_hosts':['example.test'],'access_scope':'local'}
            rt=__import__('marketradar.runtime',fromlist=['MarketRadarRuntime']).MarketRadarRuntime(c,[s],None)
            result=rt.federate('s',dry=True)
            assert result['dry_run'] is True
            assert c.execute('select count(*) from raw_observations').fetchone()[0] == 0
        finally:
            if 'c' in locals():
                c.close()


def test_legacy_evidence_engine_uses_authoritative_terms_policy():
    from marketradar.evidence import EvidenceEngine
    from marketradar.models import SourcePolicy
    p=SourcePolicy('s','https://example.test','json','job',iran_status='ALLOW',kyc_status='ALLOW',payment_status='USDT',terms_status='needs_review')
    assert EvidenceEngine().eligibility(p).status == 'REVIEW'
    p=SourcePolicy('s','https://example.test','json','job',iran_status='ALLOW',kyc_status='ALLOW',payment_status='USDT',terms_status='allowed')
    assert EvidenceEngine().eligibility(p).status == 'EXECUTE'


def test_desktop_settings_reject_invalid_http_timeout(tmp_path):
    from marketradar.desktop import load_settings
    config=tmp_path/'config'; config.mkdir()
    (config/'settings.json').write_text('{"http_timeout": 0}', encoding='utf-8')
    try:
        load_settings(tmp_path)
    except ValueError as exc:
        assert str(exc) == 'HTTP_TIMEOUT_INVALID'
    else:
        raise AssertionError('invalid HTTP timeout accepted')

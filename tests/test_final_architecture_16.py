import json
import sqlite3
from pathlib import Path

from marketradar.db import connect
from marketradar.engine_contract import build_job, EngineManifest
from marketradar.foreign_language import detect_language, guide_page, page_understanding
from marketradar.policy_evidence import aggregate_kyc, iran_policy_claims
from marketradar.source_identity import same_source
from marketradar.source_workflow import new_workflow, persist_workflow, load_workflow
from marketradar.source_verification import classify_content
from marketradar.taxonomy import resolve_workflow, get_task


def test_taxonomy_bundles_are_formal_and_multi_step():
    steps = resolve_workflow('pdf_to_word_formatted')
    assert [x.task_type for x in steps] == ['pdf_to_word','word_formatting']
    assert get_task('pdf_to_powerpoint').output_formats == ('powerpoint',)


def test_engine_contract_supports_standalone_and_unconnected():
    job = build_job('pdf_office_engine', 7, 'pdf_to_word', ['extract','convert'])
    assert job.opportunity_id == 7
    manifest = EngineManifest('pdf_office_engine','PDF Office','1.0.0',execution_mode='ENGINE_UNCONNECTED')
    assert manifest.mode() == 'ENGINE_UNCONNECTED'
    assert manifest.standalone is True and manifest.connectable is True


def test_foreign_language_guidance_keeps_submission_approval_gate():
    assert detect_language('Откликнуться на вакансию и загрузить файл') == 'ru'
    steps = guide_page('Откликнуться и загрузить файл. Отправить заявку.')
    assert any(x.action == 'apply' and x.requires_approval for x in steps)
    assert any(x.action == 'upload' for x in steps)
    assert page_understanding('Откликнуться')['autonomous_action'] is False


def test_workflow_persists_and_marks_sensitive_steps():
    c = connect(':memory:')
    wf = new_workflow('example.ru', 'ru')
    persist_workflow(c, wf)
    loaded = load_workflow(c, 'example.ru')
    assert loaded is not None
    assert any(x.step == 'APPLY' and x.requires_approval for x in loaded.steps)


def test_semantic_identity_dedup_preserves_regional_variants():
    a = {'base_url':'https://example.com/jobs','organization':'Example Corp','brand':'Example','platform':'jobs'}
    b = {'base_url':'https://example.com/careers','organization':'Example Corp','brand':'Example','platform':'jobs'}
    same, evidence = same_source(a,b)
    assert same and evidence['host_match']
    c = dict(b); c['country'] = 'Georgia'
    a['country'] = 'Iran'
    same, evidence = same_source(a,c)
    assert same is False
    assert evidence['regional_variant_preserved'] is True


def test_policy_evidence_is_negation_and_scope_aware():
    x = aggregate_kyc('A passport is not required for registration. Passport required for payout.')
    assert x['status'] == 'UNKNOWN' and x['conflict'] is True
    y = aggregate_kyc('No KYC is required for registration.')
    assert y['status'] == 'NOT_REQUIRED' and y['scope'] == 'registration'


def test_iran_policy_does_not_false_positive_on_context_only():
    assert iran_policy_claims('This page discusses Iran and OFAC requirements for research.')['status'] == 'UNKNOWN'
    assert iran_policy_claims('Users from Iran are not supported.')['status'] == 'BLOCK'


def test_terms_link_without_verified_page_does_not_become_evidence():
    result = classify_content('Welcome. Payment is available.', 'https://example.com', [])
    assert result['terms_evidence_url'] is None
    result2 = classify_content('Welcome.', 'https://example.com', ['https://example.com/terms'])
    assert result2['terms_evidence_url'] == 'https://example.com/terms'

def test_execution_broker_uses_engine_contract_and_authorization_boundary():
    import tempfile, json
    from marketradar.execution_broker import ExecutionBroker
    from marketradar.capability_registry import load_provider_config, clear_providers
    from marketradar.pipeline import Pipeline
    with tempfile.TemporaryDirectory() as td:
        c=connect(Path(td)/'x.db')
        try:
            provider_path=Path(td)/'providers.json'
            provider_path.write_text(json.dumps({'providers':[{'provider_id':'pdf-engine','name':'PDF Engine','version':'1.0.0','standalone':True,'connectable':True,'capabilities':['pdf_to_word'],'enabled':True,'health':'HEALTHY','installed':True,'connected':True,'execution_mode':'AUTO'}]}),encoding='utf8')
            load_provider_config(provider_path)
            source={'name':'TEST','iran_status':'ALLOW','kyc_status':'NOT_REQUIRED','payment_status':'USDT','terms_status':'allowed'}
            Pipeline(c).ingest(source, {'title':'PDF to Word','url':'https://example.test/job','description':'Convert PDF to Word','evidence':[{'kind':'listing','url':'https://example.test/job','finding':'test','confidence':0.95}]})
            c.commit()
            oid=c.execute('select id from opportunities').fetchone()[0]
            broker=ExecutionBroker(c)
            assert broker.plan(oid,'AUTO')['status'] == 'AUTO_READY'
            try:
                broker.prepare_job(oid,'pdf-engine')
                raise AssertionError('authorization boundary missing')
            except ValueError as e:
                assert str(e) == 'AUTHORIZATION_REQUIRED'
            prepared=broker.prepare_job(oid,'pdf-engine',authorization_token_ref='approval:test')
            assert prepared['status']=='PENDING'
            assert c.execute('select count(*) from engine_job_runs').fetchone()[0] == 1
        finally:
            clear_providers()
            c.close()

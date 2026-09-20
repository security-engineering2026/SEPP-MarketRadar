import json
import tempfile
from pathlib import Path

from marketradar.capability_registry import (
    MATCH_FULL,
    MATCH_NO_PROVIDER,
    load_provider_config,
    match_task,
)
from marketradar.db import connect, sync_source_contracts
from marketradar.opportunity_intelligence import analyze_need
from marketradar.pipeline import Pipeline
from marketradar.recommendation_engine import daily_center
from marketradar.source_policy import (
    BLACKLIST_LANE,
    EXECUTION_LANE,
    INTELLIGENCE_LANE,
    classify_source_lane,
)


def _task(title, description):
    return analyze_need({'title': title, 'description': description})


def test_work_taxonomy_core_examples():
    assert _task('PDF to Word', 'Convert PDF to Word')['task_type'] == 'pdf_to_word'
    assert _task('PDF to Excel', 'Convert PDF to Excel')['task_type'] == 'pdf_to_excel'
    assert _task('Word to PowerPoint', 'Convert Word to PowerPoint')['task_type'] == 'word_to_powerpoint'
    assert _task('Audio to Text', 'Transcribe audio to text')['task_type'] == 'audio_to_text'
    assert _task('Bug bounty Android', 'Android bug bounty program')['task_type'] == 'android_bug_bounty'
    assert _task('Web bug bounty', 'Bug bounty for a web application')['task_type'] == 'web_bug_bounty'


def test_capability_without_provider_does_not_reject_manual_work():
    task = _task('PDF to Word', 'Convert PDF to Word')
    result = match_task(task)
    assert result['status'] == MATCH_NO_PROVIDER
    assert result['manual_possible'] is True
    assert result['productization_candidate'] is True


def test_connected_provider_yields_full_match():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'providers.json'
        p.write_text(json.dumps({'providers': [{
            'provider_id': 'pdf-engine',
            'name': 'PDF Engine',
            'version': '1.0.0',
            'standalone': True,
            'capabilities': ['pdf_to_word'],
            'enabled': True,
            'health': 'HEALTHY',
            'installed': True,
            'connected': True,
        }]}), encoding='utf-8')
        load_provider_config(p)
        result = match_task(_task('PDF to Word', 'Convert PDF to Word'))
        assert result['status'] == MATCH_FULL
        assert 'pdf-engine' in result['matches'][0]['connected_provider_ids']


def test_source_policy_lanes():
    foreign_good = {
        'name': 'foreign', 'base_url': 'https://example.com', 'country': 'Global',
        'access_scope': 'public', 'iran_eligibility': 'ALLOW',
        'kyc_requirement': 'NOT_REQUIRED',
        'payment_capabilities': ['USDT'], 'evidence_confidence': 0.95,
    }
    assert classify_source_lane(foreign_good).lane == EXECUTION_LANE

    foreign_market = dict(foreign_good, iran_eligibility='UNKNOWN')
    assert classify_source_lane(foreign_market).lane == INTELLIGENCE_LANE

    blacklisted = dict(foreign_good, registration_country='Israel')
    assert classify_source_lane(blacklisted).lane == BLACKLIST_LANE


def test_pipeline_persists_task_understanding_and_manual_execution():
    with tempfile.TemporaryDirectory() as td:
        c = connect(Path(td) / 'x.db')
        source = {'name': 'TEST', 'iran_status': 'ALLOW', 'kyc_status': 'ALLOW', 'payment_status': 'USDT', 'terms_status': 'allowed'}
        item = {
            'title': 'Convert PDF to Word',
            'url': 'https://example.test/pdf-word',
            'description': 'Convert PDF to editable Word documents',
            'evidence': [{'kind': 'listing', 'url': 'https://example.test/pdf-word', 'finding': 'test', 'confidence': 0.95}],
        }
        Pipeline(c).ingest(source, item)
        c.commit()
        row = c.execute('SELECT task_type,input_formats_json,output_formats_json,manual_execution_possible,automation_status FROM opportunities').fetchone()
        assert row['task_type'] == 'pdf_to_word'
        assert json.loads(row['input_formats_json']) == ['pdf']
        assert json.loads(row['output_formats_json']) == ['word']
        assert row['manual_execution_possible'] == 1
        assert row['automation_status'] in {'MANUAL_OR_BUILD', 'ENGINE_NOT_READY', 'AUTO_AVAILABLE'}
        c.close()


def test_daily_center_keeps_manual_project_without_provider():
    with tempfile.TemporaryDirectory() as td:
        c = connect(Path(td) / 'x.db')
        source = {'name': 'TEST', 'iran_status': 'ALLOW', 'kyc_status': 'ALLOW', 'payment_status': 'USDT', 'terms_status': 'allowed'}
        item = {'title': 'Python automation', 'url': 'https://example.test/python', 'description': 'Python automation task for a small API workflow', 'evidence': [{'kind': 'listing', 'url': 'https://example.test/python', 'finding': 'test', 'confidence': 0.95}]}
        Pipeline(c, settings={'profile': {'domains': {'python': {'enabled': True, 'level': 2, 'stretch': False}}, 'selected_domains': ['python'], 'learning': {'level': 2, 'stretch': False}}}).ingest(source, item)
        c.commit()
        center = daily_center(c, {'selected_domains': ['python'], 'domains': {'python': {'enabled': True, 'level': 2, 'stretch': False}}})
        assert 'top7' in center
        assert center['domains'].get('python') is not None
        c.close()


def test_services_typing_and_market_intelligence_productization_are_preserved():
    assert _task('Type scanned pages into Word', 'Type scanned pages into Word')['task_type'] == 'data_entry'
    assert _task('Excel automation report', 'Excel automation weekly report')['task_type'] == 'excel_automation'

    with tempfile.TemporaryDirectory() as td:
        c = connect(Path(td) / 'x.db')
        source = {
            'name': 'MARKET-INTEL',
            'base_url': 'https://intel.example',
            'adapter': 'json',
            'status': 'active',
            'access_scope': 'public',
            'iran_status': 'BLOCK',
            'kyc_requirement': 'REQUIRED',
            'payment_capabilities': [],
            'evidence_confidence': 0.95,
            'source_lane': 'MARKET_INTELLIGENCE_ONLY',
            'terms_status': 'allowed',
        }
        sync_source_contracts(c, [source])
        for i, title in enumerate(('Convert PDF to Word','Convert PDF to Excel','Create Word to PowerPoint presentation','Type scanned pages into Word'), 1):
            Pipeline(c).ingest(source, {
                'title': title,
                'url': f'https://intel.example/job/{i}',
                'description': title,
                'evidence': [{'kind': 'listing', 'url': f'https://intel.example/job/{i}', 'finding': 'demand', 'confidence': 0.95}],
            })
        c.commit()
        center = daily_center(c, {'selected_domains':['services'], 'domains':{'services':{'enabled':True,'level':2,'stretch':False}}})
        assert center['product_opportunities']
        assert center['product_opportunities'][0]['product_key'] == 'student_services_engine'
        assert center['product_opportunities'][0]['task_count'] >= 3
        assert c.execute("SELECT COUNT(*) FROM opportunities WHERE COALESCE(blacklist_reason,'')<>''").fetchone()[0] == 0
        c.close()

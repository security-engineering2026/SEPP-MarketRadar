import json
from marketradar.source_verification import classify_content


def test_automatic_policy_monitor_blocks_explicit_iran_restriction():
    result=classify_content('Our service is not available to residents of Iran. Terms and payout information.', 'https://example.test/', ['https://example.test/terms','https://example.test/payout'])
    assert result['iran_eligibility']=='BLOCK'


def test_automatic_policy_monitor_never_infers_allow_from_silence():
    result=classify_content('Freelance projects and payments are available worldwide.', 'https://example.test/', [])
    assert result['iran_eligibility']=='UNKNOWN'
    assert result['execution_ready'] if 'execution_ready' in result else True


def test_crypto_and_kyc_signals_are_classified():
    result=classify_content('Payouts are available in USDT and BTC. KYC is required before withdrawal.', 'https://example.test/', [])
    assert 'USDT' in result['payment_capabilities'] and 'BTC' in result['payment_capabilities']
    assert result['kyc_requirement']=='REQUIRED'
from marketradar.source_discovery import SourceDiscoveryEngine


def test_bug_bounty_and_freelance_share_same_policy_classifier():
    restricted='Researchers from Iran are not permitted to participate. Payouts in USDT.'
    result=classify_content(restricted,'https://example.test/',[])
    assert result['iran_eligibility']=='BLOCK'
    assert 'USDT' in result['payment_capabilities']


def test_catalog_discovery_parses_markdown_candidates():
    rows=SourceDiscoveryEngine._parse_markdown(object.__new__(SourceDiscoveryEngine), '| Foo | https://foo.example |\n| Bar | https://bar.example |', {})
    assert ('Foo','https://foo.example') in rows
    assert ('Bar','https://bar.example') in rows

def test_policy_monitor_persists_and_auto_blocks_source():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading, tempfile
    from marketradar.db import connect, sync_source_contracts
    from marketradar.source_verification import SourceVerificationEngine
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body=b'<html><body>This service is not available to residents of Iran. Payout in USDT.</body></html>'
            self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers(); self.wfile.write(body)
        def log_message(self,*args): pass
    server=HTTPServer(('127.0.0.1',0),H); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        source={'name':'POLICY_LOCAL','base_url':f'http://127.0.0.1:{server.server_port}/','adapter':'html','status':'active','allow_hosts':['127.0.0.1'],'access_scope':'local','policy_lane':'GLOBAL_DISCOVERY','daily_scan':False,'source_family':'bug_bounty','source_role':'bug_bounty','iran_status':'UNKNOWN','source_verification_state':'DISCOVERED','iran_eligibility':'UNKNOWN','kyc_requirement':'UNKNOWN','execution_ready':False}
        with tempfile.TemporaryDirectory() as d:
            try:
                c=connect(d+'/r.db'); sync_source_contracts(c,[source])
                eng=SourceVerificationEngine(c,[source],timeout=3,max_workers=1,max_policy_pages=1)
                result=eng.verify(['POLICY_LOCAL'])[0]; eng.persist([result])
                row=c.execute("SELECT policy_lane,iran_eligibility,execution_ready FROM sources WHERE name='POLICY_LOCAL'").fetchone()
                assert result['iran_eligibility']=='BLOCK'; assert row['policy_lane']=='BLOCKED_IRAN'; assert row['execution_ready']==0
                state=c.execute("SELECT source_verification_state FROM source_verification_state WHERE source='POLICY_LOCAL'").fetchone()
                assert state['source_verification_state']=='LIVE_CONFIRMED'
                c.close()
            finally:
                if 'c' in locals():
                    c.close()
    finally: server.shutdown()

def test_scan_uses_persisted_runtime_policy_lane():
    from marketradar.engine import MarketRadar
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        root=__import__('pathlib').Path(d); (root/'config').mkdir(); (root/'data').mkdir()
        import shutil, json
        shutil.copytree(__import__('pathlib').Path(__file__).parents[1]/'config', root/'config', dirs_exist_ok=True)
        rows=json.loads((root/'config'/'sources.json').read_text())
        rows=[r for r in rows if r['name']=='Jobinja_Iran']
        rows[0]['status']='active'; rows[0]['policy_lane']='DAILY_PROJECT_SCAN'; rows[0]['daily_scan']=True
        (root/'config'/'sources.json').write_text(json.dumps(rows))
        from marketradar.db import sync_source_contracts
        with MarketRadar(root) as mr:
            sync_source_contracts(mr.conn, rows)
            mr.conn.execute("UPDATE sources SET policy_lane='BLOCKED_IRAN', iran_eligibility='BLOCK' WHERE name='Jobinja_Iran'"); mr.conn.commit()
            stats=mr.scan(dry=True)
            assert stats['sources_checked']==0


def test_autodiscovery_finds_unlisted_platform_without_registry_seed():
    from marketradar.source_discovery import SourceDiscoveryEngine
    class FakeSearch:
        def available(self): return True
        def search(self, query, limit):
            return [
                {'title':'Rubika | روبیکا','url':'https://rubika.ir/','snippet':'Iranian messaging and social platform'},
                {'title':'BOSS直聘','url':'https://www.zhipin.com/','snippet':'China jobs and hiring platform'},
                {'title':'Example VDP','url':'https://security.example.org/','snippet':'responsible disclosure bug bounty VDP'},
            ]
    cfg={'search_limit_per_query':10,'queries':[{'id':'lab','country':'Global','region':'Global','language':'multi','family':'jobs','q':'lab source discovery'}]}
    result=SourceDiscoveryEngine([],cfg,FakeSearch()).discover(include_catalogs=False,include_search=True)
    names={x['name'] for x in result['candidates']}
    assert 'Rubika' in names
    assert 'BOSS' in ' '.join(names) or 'BOSS_Zhipin' in ' '.join(names)
    assert any(x['source_family']=='bug_bounty' for x in result['candidates'])


def test_dynamic_discovery_survives_registry_sync():
    import tempfile
    from marketradar.db import connect, sync_source_contracts, load_dynamic_source_records
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(d+'/r.db')
            base={'name':'BASE','base_url':'https://base.example/','adapter':'html','status':'candidate','allow_hosts':['base.example'],'source_kind':'job_board','acquisition':'http','verification_state':'documented','access_scope':'public','terms_status':'needs_review','country':'Global','region':'Global','language':'en','source_family':'job_board','source_role':'job_board','policy_lane':'GLOBAL_DISCOVERY','daily_scan':False,'needs_analysis':True,'source_verification_state':'DISCOVERED','iran_eligibility':'UNKNOWN','kyc_requirement':'UNKNOWN','payment_capabilities':[],'execution_ready':False,'source_origin':'registry'}
            dyn=dict(base); dyn.update(name='Rubika',base_url='https://rubika.ir/',allow_hosts=['rubika.ir'],country='Iran',region='Iran',language='fa',source_family='social_platform',source_role='social_platform',policy_lane='DAILY_PROJECT_SCAN',daily_scan=True,source_origin='dynamic_discovery',discovery_basis='search:lab')
            sync_source_contracts(c,[base,dyn])
            got=load_dynamic_source_records(c)
            assert any(x['name']=='Rubika' for x in got)
            sync_source_contracts(c,[base])
            row=c.execute("SELECT status,source_origin FROM sources WHERE name='Rubika'").fetchone()
            assert row['source_origin']=='dynamic_discovery' and row['status']=='candidate'
            c.close()
        finally:
            if 'c' in locals():
                c.close()


def test_policy_classifier_catches_not_available_in_iran_and_embargoed_language():
    r=classify_content('This service is not available in Iran and is subject to export controls.', 'https://example.test/', [])
    assert r['iran_eligibility']=='BLOCK'
    r2=classify_content('Iran is an embargoed destination under our terms.', 'https://example.test/', [])
    assert r2['iran_eligibility']=='BLOCK'

def test_policy_classifier_supports_persian_source_terms():
    r=classify_content('این سرویس برای کاربران ایرانی در دسترس نیست و احراز هویت لازم است.', 'https://example.test/', [])
    assert r['iran_eligibility']=='BLOCK'
    assert r['kyc_requirement']=='REQUIRED'

def test_live_verified_candidate_is_promoted_to_active_but_not_execution_ready():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading, tempfile
    from marketradar.db import connect, sync_source_contracts
    from marketradar.source_verification import SourceVerificationEngine
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body=b'<html><body>Worldwide projects. Terms and payout policy.</body></html>'
            self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers(); self.wfile.write(body)
        def log_message(self,*args): pass
    server=HTTPServer(('127.0.0.1',0),H); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        source={'name':'LIVE_CANDIDATE','base_url':f'http://127.0.0.1:{server.server_port}/','adapter':'html','status':'candidate','allow_hosts':['127.0.0.1'],'access_scope':'local','policy_lane':'GLOBAL_DISCOVERY','daily_scan':False,'source_family':'job_board','source_role':'job_board','iran_status':'UNKNOWN','source_verification_state':'DISCOVERED','iran_eligibility':'UNKNOWN','kyc_requirement':'UNKNOWN','execution_ready':False}
        with tempfile.TemporaryDirectory() as d:
            try:
                c=connect(d+'/r.db'); sync_source_contracts(c,[source]); eng=SourceVerificationEngine(c,[source],timeout=3,max_workers=1,max_policy_pages=1); result=eng.verify(['LIVE_CANDIDATE'])[0]; eng.persist([result])
                row=c.execute("SELECT status,source_verification_state,execution_ready FROM sources WHERE name='LIVE_CANDIDATE'").fetchone()
                assert row['status']=='active'; assert row['source_verification_state']=='LIVE_CONFIRMED'; assert row['execution_ready']==0
                c.close()
            finally:
                if 'c' in locals():
                    c.close()
    finally: server.shutdown()

from pathlib import Path
from tempfile import TemporaryDirectory
from marketradar.db import connect, sync_source_contracts
from marketradar.source_verification import SourceVerificationEngine, _surface_links, _html_text

class FakeHTTP:
    def __init__(self):
        self.pages={
            'https://iran.example/': b'<a href="/account">Account</a><a href="/pricing">Pricing</a><a href="/terms">Terms</a>',
            'https://iran.example/account': b'<a href="/limits">Limits</a><a href="/proposals">Proposals</a>',
            'https://iran.example/pricing': b'Subscription plan: 5 proposals per month for 100000 IRR',
            'https://iran.example/terms': b'Users may submit only 1 active proposal at a time. Payment via bank transfer.',
            'https://iran.example/limits': b'Only 1 open project at a time.',
            'https://iran.example/proposals': b'Proposal fee 5000 IRR; application limit one active proposal at a time.'
        }
    def fetch(self,name,url=None):
        u=url or 'https://iran.example/'
        body=self.pages[u]
        return {'source':name,'url':u,'status':200,'content_type':'text/html','bytes':len(body),'sha256':'x','elapsed_ms':1,'body':body,'attempts':1}

def test_surface_crawler_reaches_account_pricing_and_constraints():
    with TemporaryDirectory() as td:
        c=connect(Path(td)/'x.db')
        source={'name':'Iran_Platform','base_url':'https://iran.example/','adapter':'html','status':'active','allow_hosts':['iran.example'],'source_lane':'EXECUTION_ELIGIBLE','policy_lane':'DAILY_PROJECT_SCAN','country':'Iran','region':'Iran','language':'fa','iran_status':'ALLOW','kyc_status':'UNKNOWN','payment_status':'UNKNOWN','access_scope':'public','source_family':'freelance','source_role':'freelance'}
        sync_source_contracts(c,[source])
        try:
            e=SourceVerificationEngine(c,[source],surface_scan_pages=20)
            e.http=FakeHTTP()
            r=e._one('Iran_Platform')
            assert r['source_verification_state']=='LIVE_CONFIRMED'
            keys={x['key'] for x in r['source_constraints']}
            assert 'max_pending_applications' in keys and 'max_open_projects' in keys and 'subscription_fee' in keys
            e.persist([r]); row=c.execute('SELECT max_pending_applications,max_open_projects FROM source_application_limits WHERE source="Iran_Platform"').fetchone(); assert row['max_pending_applications']==1 and row['max_open_projects']==1
        finally:
            c.close()

def test_surface_links_host_boundary():
    html=b'<a href="/ok">ok</a><a href="https://evil.example/x">evil</a><a href="javascript:x">js</a>'
    links=_surface_links(html,'https://example.test/')
    assert links==['https://example.test/ok']
    assert _html_text(b'<h1>Iran</h1><script>x</script> policy')=='Iran policy'

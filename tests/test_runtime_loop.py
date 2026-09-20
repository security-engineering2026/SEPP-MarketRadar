import json, threading, tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from marketradar.db import connect
from marketradar.runtime import MarketRadarRuntime

class Feed(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({'items': [{
            'title': 'Python automation',
            'description': 'Build automation for $250 USDT',
            'url': f'http://127.0.0.1:{self.server.server_port}/opportunity/1'
        }]}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *_): pass

def test_real_end_to_end_federation_application_android_revenue():
    server = HTTPServer(('127.0.0.1', 0), Feed)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        source = {
            'name': 'E2E_LOCAL', 'base_url': f'http://127.0.0.1:{server.server_port}/feed',
            'adapter': 'json', 'status': 'active', 'allow_hosts': ['127.0.0.1'], 'access_scope': 'local',
            'type': 'marketplace', 'iran_status': 'ALLOW', 'kyc_status': 'ALLOW',
            'payment_status': 'USDT', 'terms_status': 'allowed', 'execution_mode': 'MANUAL'
        }
        with tempfile.TemporaryDirectory() as d:
            try:
                c = connect(d + '/radar.db')
                rt = MarketRadarRuntime(c, [source], 'integration-secret')

                result = rt.federate('E2E_LOCAL')
                assert result['status'] == 'OK' and result['observations'] == 1
                assert c.execute('select count(*) from raw_observations').fetchone()[0] == 1
                row = c.execute('select id,state,eligibility from opportunities').fetchone()
                assert row['eligibility'] == 'EXECUTE' and row['state'] == 'DISCOVERED'

                approval = rt.issue_submission_approval(row['id'])
                app_msg = rt.approve_and_submit(row['id'], approval)
                assert app_msg['kind'] == 'APPLICATION_SUBMITTED'
                assert rt.android.verify(app_msg)
                assert c.execute('select state from opportunities where id=?',(row['id'],)).fetchone()[0] == 'SUBMITTED'

                for state in ('VIEWED', 'MESSAGE_RECEIVED', 'NEGOTIATION', 'ACCEPTED', 'IN_PROGRESS', 'DELIVERED'):
                    from marketradar.application import transition
                    transition(c, row['id'], state, 'test')

                revenue_msg = rt.record_payment(row['id'], 250, 'USDT', '2026-09-10T00:00:00Z', 'tx-e2e-1')
                assert revenue_msg['kind'] == 'REVENUE_RECEIVED'
                assert rt.android.verify(revenue_msg)
                assert c.execute('select state from opportunities where id=?',(row['id'],)).fetchone()[0] == 'DELIVERED'
                from marketradar.application import verify_payment
                verify_payment(c, row['id'], 'tx-e2e-1', 'VERIFIED')
                assert c.execute('select state from opportunities where id=?',(row['id'],)).fetchone()[0] == 'PAID'
                assert c.execute('select sum(amount) from revenue').fetchone()[0] == 250
                assert c.execute('select count(*) from federation_runs where status="OK"').fetchone()[0] == 1
            finally:
                if 'c' in locals():
                    c.close()
    finally:
        server.shutdown(); thread.join()

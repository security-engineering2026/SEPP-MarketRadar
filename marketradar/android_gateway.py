from __future__ import annotations
import hashlib, hmac, json, os, secrets, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from .notifications import unread, mark_read
from .finance import period_report
from .security import Approval
from . import __version__


def _json_bytes(v): return json.dumps(v,ensure_ascii=False,default=str).encode('utf-8')

class AndroidGateway:
    def __init__(self, connection, runtime, secret=None):
        self.c=connection; self.runtime=runtime; self.secret=(secret or os.getenv('MARKETRADAR_ANDROID_API_TOKEN') or '').encode()
        if not self.secret: raise RuntimeError('ANDROID_API_TOKEN_REQUIRED')

    def token_ok(self, token: str):
        return bool(token) and hmac.compare_digest(hashlib.sha256(token.encode()).digest(), hashlib.sha256(self.secret).digest())

    def dashboard(self):
        d=self.runtime.operation_dashboard(); n=[dict(x) for x in unread(self.c,50)]
        fin=period_report(self.c,'monthly')
        return {'version':__version__,'operations':d,'notifications':n,'finance':fin,'pending_approvals':[dict(x) for x in self.c.execute("SELECT * FROM action_authorizations WHERE status='ISSUED' AND expires_at>=strftime('%s','now') ORDER BY issued_at DESC LIMIT 50").fetchall()]}

    def opportunity(self, oid):
        return self.runtime.project_report(int(oid))

    def approve_submission(self, oid, actor='android_operator'):
        approval=self.runtime.issue_submission_approval(int(oid),'v1',ttl=300)
        return {'status':'APPROVAL_ISSUED','opportunity_id':int(oid),'approval':dict(approval.__dict__)}

    def execute_submission(self, oid, approval, actor='android_operator'):
        a=Approval(approval['approval_id'],approval['action'],approval['target'],approval['parameters_digest'],approval['evidence_digest'],approval['policy_version'],int(approval['expires_at']))
        return self.runtime.approve_and_submit(int(oid),a,actor=actor,policy_version='v1')

class _Handler(BaseHTTPRequestHandler):
    gateway=None
    server_version='MarketRadarAndroidGateway/'+__version__
    def _reply(self,status,payload):
        data=_json_bytes(payload); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def _auth(self):
        return self.gateway.token_ok(self.headers.get('X-MarketRadar-Token',''))
    def _body(self):
        n=int(self.headers.get('Content-Length','0') or 0); return json.loads(self.rfile.read(n).decode('utf-8')) if n else {}
    def do_GET(self):
        if not self._auth(): return self._reply(401,{'error':'UNAUTHORIZED'})
        path=urlparse(self.path).path
        try:
            if path=='/api/android/v1/dashboard': return self._reply(200,self.gateway.dashboard())
            if path=='/api/android/v1/notifications': return self._reply(200,{'notifications':[dict(x) for x in unread(self.gateway.c,100)]})
            if path.startswith('/api/android/v1/opportunities/'):
                return self._reply(200,self.gateway.opportunity(int(path.rsplit('/',1)[-1])))
            if path=='/api/android/v1/finance/monthly': return self._reply(200,period_report(self.gateway.c,'monthly'))
            return self._reply(404,{'error':'NOT_FOUND'})
        except Exception as exc: return self._reply(400,{'error':type(exc).__name__+': '+str(exc)})
    def do_POST(self):
        if not self._auth(): return self._reply(401,{'error':'UNAUTHORIZED'})
        path=urlparse(self.path).path
        try:
            body=self._body()
            if path.startswith('/api/android/v1/notifications/') and path.endswith('/read'):
                mark_read(self.gateway.c,int(path.split('/')[-2])); return self._reply(200,{'status':'READ'})
            if path=='/api/android/v1/applications/approve': return self._reply(200,self.gateway.approve_submission(body['opportunity_id']))
            if path=='/api/android/v1/applications/execute': return self._reply(200,self.gateway.execute_submission(body['opportunity_id'],body['approval']))
            return self._reply(404,{'error':'NOT_FOUND'})
        except Exception as exc: return self._reply(400,{'error':type(exc).__name__+': '+str(exc)})
    def log_message(self,*args): return


def serve(connection, runtime, host='127.0.0.1', port=8765, secret=None):
    g=AndroidGateway(connection,runtime,secret)
    handler=type('MRAndroidHandler',(_Handler,),{'gateway':g})
    server=ThreadingHTTPServer((host,int(port)),handler)
    try: server.serve_forever()
    finally: server.server_close()

import json,threading,tempfile,subprocess,sys
from http.server import BaseHTTPRequestHandler,HTTPServer
from marketradar.federation import Federation,Source
from marketradar.source_registry import load_sources
from marketradar.db import connect
from marketradar.demo import seed
from marketradar.application import transition,record_revenue
from marketradar.android_bridge import AndroidBridge
from marketradar.revenue import revenue_summary
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  b=json.dumps({'items':[{'title':'Python automation','description':'$150 USDT','url':'https://client.test/a'}]}).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
 def log_message(self,*a):pass
def test_local_live_federation():
 s=HTTPServer(('127.0.0.1',0),H); port=s.server_port; t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
 try:
  f=Federation([Source('local',f'http://127.0.0.1:{port}/feed',allow_hosts=('127.0.0.1',),access_scope='local')]);o=f.fetch('local'); assert o['status']==200 and Federation.parse_json(o)[0]['title']=='Python automation'
  try:f.fetch('local',f'http://localhost:{port}/feed'); assert False
  except ValueError:pass
 finally:s.shutdown();t.join()
def test_registry_has_onboarded_sources_and_separate_target():
 import json
 s=load_sources('config/sources.json'); target=json.load(open('config/source_targets.json'))['target_registered_sources']; assert len(s)>=5 and target>=500 and len({x.name for x in s})==len(s)
def test_application_and_revenue_loop():
 with tempfile.TemporaryDirectory() as d:
     try:
      c=connect(d+'/x.db'); seed(c); oid=c.execute('select id from opportunities limit 1').fetchone()[0]
      for st in ['ELIGIBILITY_CHECK','RECOMMENDED','APPROVAL_PENDING','SUBMITTED','VIEWED','MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','IN_PROGRESS','DELIVERED']: transition(c,oid,st,'test')
      record_revenue(c,oid,100,'USDT','2026-09-09T00:00:00Z','tx-1'); assert c.execute('select state from opportunities where id=?',(oid,)).fetchone()[0]=='DELIVERED'; from marketradar.application import verify_payment; verify_payment(c,oid,'tx-1','VERIFIED'); assert c.execute('select state from opportunities where id=?',(oid,)).fetchone()[0]=='PAID'; assert revenue_summary(c)[0]['total']==100
      try: record_revenue(c,oid,100,'USDT','2026-09-09T00:00:00Z','tx-1'); assert False
      except Exception: pass
     finally:
         if 'c' in locals():
             c.close()
def test_android_message_binding():
 b=AndroidBridge('secret'); m=b.envelope('ACTION',{'id':7}); assert b.verify(m); m['payload']['id']=8; assert not b.verify(m)
 try: b.envelope('ACTION',{'id':7},ttl=-1)
 except ValueError: pass
 else: assert False

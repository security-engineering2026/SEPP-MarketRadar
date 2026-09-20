import json, threading, tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from marketradar.db import connect
from marketradar.runtime import MarketRadarRuntime

def test_raw_response_survives_adapter_failure():
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body=b'not-json'
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(body)
        def log_message(self,*args): pass
    server=HTTPServer(('127.0.0.1',0),H); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as d:
            try:
                c=connect(Path(d)/'x.db')
                s={'name':'s','base_url':f'http://127.0.0.1:{server.server_port}/feed','adapter':'json','status':'active','allow_hosts':['127.0.0.1'],'access_scope':'local'}
                rt=MarketRadarRuntime(c,[s],None)
                try: rt.federate('s')
                except Exception: pass
                else: raise AssertionError('invalid JSON was accepted')
                row=c.execute("select http_status,payload_sha256,payload from raw_observations where source='s'").fetchone()
                assert row['http_status']==200 and row['payload']==b'not-json' and len(row['payload_sha256'])==64
            finally:
                if 'c' in locals():
                    c.close()
    finally:
        server.shutdown(); server.server_close()


def test_acquisition_attestation_accepts_tracking_url_when_raw_record_keeps_actual_url():
    import hashlib
    from marketradar.pipeline import Pipeline, AcquisitionAttestation
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/'x.db'); body=b'{"items":[]}' ; sha=hashlib.sha256(body).hexdigest()
            actual='https://example.test/feed?utm_source=mail&x=1'
            c.execute("insert into raw_observations(source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind) values(?,?,?,?,?,?,?,?)",('s',actual,'t',body,sha,200,'application/json','source_response')); c.commit()
            item={'title':'Bound acquisition','url':'https://example.test/job/2','description':'A sufficiently descriptive task with requirements.','evidence':[]}
            p=Pipeline(c)
            p.ingest({'name':'s','iran_status':'UNKNOWN','kyc_status':'UNKNOWN','payment_status':'UNKNOWN'}, item, AcquisitionAttestation('s',actual,sha,200))
        finally:
            if 'c' in locals():
                c.close()

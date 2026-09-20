from __future__ import annotations

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from marketradar.db import connect, sync_source_contracts
from marketradar.source_discovery import SourceDiscoveryEngine
from marketradar.source_verification import SourceVerificationEngine


class _Handler(BaseHTTPRequestHandler):
    routes = {}
    def do_GET(self):
        body = self.routes.get(self.path, '<html><body>Worldwide service. Terms available.</body></html>').encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass


class _FakeSearch:
    def __init__(self, rows): self.rows=rows
    def available(self): return True
    def search(self, query, limit): return self.rows[:limit]


def main():
    search_rows=[
        {'title':'Rubika | روبیکا','url':'https://rubika.ir/','snippet':'Iranian messaging and social platform'},
        {'title':'BOSS Zhipin','url':'https://www.zhipin.com/','snippet':'China jobs platform'},
        {'title':'Example VDP','url':'https://security.example.org/','snippet':'bug bounty responsible disclosure VDP'},
    ]
    cfg={'queries':[{'id':'lab','country':'Global','region':'Global','language':'multi','family':'jobs','q':'lab'}],'search_limit_per_query':10}
    discovery=SourceDiscoveryEngine([],cfg,_FakeSearch(search_rows)).discover(include_catalogs=False)

    routes={}
    records=[]
    patterns=[
        ('blocked_en','This service is not available to residents of Iran.'),
        ('blocked_en2','Iran is a prohibited and restricted jurisdiction under our terms.'),
        ('blocked_fa','این سرویس برای کاربران ایرانی در دسترس نیست.'),
        ('blocked_ru','Иран запрещен для использования сервиса.'),
        ('blocked_tr','Iran kullanılamaz ve yaptırım kapsamındadır.'),
        ('blocked_sanction','Iran is an embargoed destination.'),
        ('allow_en','Developers in Iran are supported and eligible to use this service. KYC is required.'),
        ('allow_fa','کاربران ایرانی مجاز هستند. احراز هویت لازم است.'),
        ('unknown','Worldwide freelance projects and payments.'),
    ]
    for i,(slug,text) in enumerate(patterns):
        path=f'/source-{i}'
        routes[path]=f'<html><body>{text}</body></html>'
        records.append({'name':f'LAB_{slug.upper()}_{i}','base_url':'PLACEHOLDER','adapter':'html','status':'candidate','allow_hosts':['127.0.0.1'],'source_kind':'job_board','acquisition':'http','verification_state':'documented','access_scope':'local','terms_status':'needs_review','country':'Global','region':'Global','language':'multi','source_family':'job_board','source_role':'job_board','policy_lane':'GLOBAL_DISCOVERY','daily_scan':False,'needs_analysis':True,'source_verification_state':'DISCOVERED','iran_eligibility':'UNKNOWN','kyc_requirement':'UNKNOWN','payment_capabilities':[],'execution_ready':False})
    server=HTTPServer(('127.0.0.1',0),_Handler); port=server.server_port; _Handler.routes=routes
    for r,(slug,_) in zip(records,patterns): r['base_url']=f'http://127.0.0.1:{port}/source-{records.index(r)}'
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        with tempfile.TemporaryDirectory() as d:
            c=connect(Path(d)/'lab.db'); sync_source_contracts(c,records)
            eng=SourceVerificationEngine(c,records,timeout=3,max_workers=4,max_policy_pages=1)
            results=eng.verify(); eng.persist(results)
            blocked=sum(x['iran_eligibility']=='BLOCK' for x in results)
            allow=sum(x['iran_eligibility']=='ALLOW' for x in results)
            unknown=sum(x['iran_eligibility']=='UNKNOWN' for x in results)
            report={'discovery_candidates':len(discovery['candidates']),'discovered_examples':[x['name'] for x in discovery['candidates']], 'verification_checked':len(results),'auto_blocked':blocked,'auto_allowed':allow,'unknown_safe_state':unknown,'execution_ready':sum(bool(x['execution_ready']) for x in results), 'assertions':{'blocked_gt_one':blocked>1,'silence_not_allow':unknown>0,'no_kyc_inference':all(x['execution_ready'] is False for x in results)}}
            out=Path('reports/SOURCE_AUTOMATION_LAB_v4.17.json'); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
            print(json.dumps(report,ensure_ascii=False,indent=2))
            c.close()
    finally:
        server.shutdown()


if __name__=='__main__': main()

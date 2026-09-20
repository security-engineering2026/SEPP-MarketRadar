from __future__ import annotations
import json, os, urllib.request, urllib.error
from pathlib import Path

def main():
    url=os.environ.get('SEARXNG_URL','').rstrip('/')
    if not url:
        print(json.dumps({'ok':False,'state':'NOT_CONFIGURED','hint':'Set SEARXNG_URL to a reachable SearXNG instance.'},indent=2)); return 2
    target=url+'/search?q=marketplace&format=json&categories=general'
    try:
        req=urllib.request.Request(target,headers={'Accept':'application/json','User-Agent':'SEPP-MarketRadar/5.0.0 doctor'})
        with urllib.request.urlopen(req,timeout=10) as r:
            body=r.read(200000).decode('utf-8','replace')
        payload=json.loads(body)
        print(json.dumps({'ok':True,'state':'LIVE_PROVIDER_REACHABLE','url':url,'results':len(payload.get('results',[]))},indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'ok':False,'state':'PROVIDER_UNREACHABLE','url':url,'error':type(exc).__name__+': '+str(exc)},indent=2)); return 3
if __name__=='__main__': raise SystemExit(main())

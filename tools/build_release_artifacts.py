from __future__ import annotations
import csv, json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter
from marketradar import __version__ as version
rows=json.loads((ROOT/'config'/'sources.json').read_text(encoding='utf-8'))

def evidence_score(r):
    score=0; fields=[]
    for k,w in [('verification_basis',15),('terms_evidence_url',15),('iran_policy_url',20),('kyc_evidence_url',15),('payout_evidence_url',15),('last_verified_at',10),('policy_checked_at',10)]:
        if r.get(k): score+=w; fields.append(k)
    return min(100,score)

def classify(r):
    if r.get('policy_lane')=='BLOCKED_IRAN' or r.get('iran_eligibility')=='BLOCK': return 'VERIFIED_BLOCKED_IRAN'
    if r.get('policy_lane')=='DAILY_PROJECT_SCAN' and r.get('execution_ready'): return 'VERIFIED_IRAN_COMPATIBLE'
    if r.get('policy_lane') in {'GLOBAL_DISCOVERY','NEEDS_ANALYSIS'} and r.get('source_verification_state')=='LIVE_CONFIRMED': return 'VERIFIED_MARKET_INTELLIGENCE'
    if r.get('source_verification_state')=='DEAD': return 'DEAD'
    if r.get('source_verification_state')=='LOW_QUALITY': return 'LOW_QUALITY'
    if r.get('source_verification_state')=='STALE': return 'STALE'
    return 'UNVERIFIED'

out=[]
for r in rows:
    x=dict(r); x['evidence_score']=evidence_score(r); x['final_classification']=classify(r); out.append(x)
fields=['name','base_url','country','region','source_family','source_role','status','policy_lane','iran_status','iran_eligibility','kyc_requirement','payment_capabilities','source_verification_state','verification_state','execution_ready','market_intelligence_value','evidence_score','verification_basis','iran_policy_url','kyc_evidence_url','payout_evidence_url','terms_evidence_url','last_verified_at','discovery_basis']
with (ROOT/'reports'/'SOURCE_VERIFICATION_MATRIX.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for r in out: w.writerow({k:(json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(list,dict)) else r.get(k,'')) for k in fields})
counts=Counter(x['final_classification'] for x in out)
regions=Counter(x.get('country') or 'UNKNOWN' for x in out)
lanes=Counter(x.get('policy_lane') or 'REVIEW' for x in out)
md=[f'# SOURCE VERIFICATION MATRIX — SEPP-MarketRadar v{version}','',f'Total registered source contracts: **{len(out)}**.','', '## Classification', '']
for k in ['VERIFIED_IRAN_COMPATIBLE','VERIFIED_BLOCKED_IRAN','VERIFIED_MARKET_INTELLIGENCE','UNVERIFIED','STALE','DEAD','LOW_QUALITY']:
    md.append(f'- `{k}`: **{counts.get(k,0)}**')
md += ['', '## Policy rule', '', '- `DAILY_PROJECT_SCAN` is not execution authorization. `execution_ready=true` is a separate gate.', '- No source is promoted to execution-ready from existence alone; current policy, KYC, payout and terms evidence are required.', '- Unknown Iran compatibility remains discovery/research-only.', '- Explicit Iran restrictions remain blocked; no bypass logic is permitted.', '', '## Regional coverage snapshot', '']
for k,v in sorted(regions.items(), key=lambda kv:(kv[0].lower())): md.append(f'- {k}: {v}')
md += ['', '## Lane counts', '']
for k,v in sorted(lanes.items()): md.append(f'- {k}: {v}')
md += ['', '## Newly verified / newly discovered in v4.15', '']
for r in out:
    if r.get('discovery_basis','').startswith(('official_public','regional_market','regional_bug','2026 regional')):
        md.append(f"- **{r['name']}** — {r.get('country','?')} — `{r.get('policy_lane')}` — `{r.get('iran_eligibility','UNKNOWN')}` — evidence {r.get('evidence_score',0)}% — {r.get('notes','')}")
md += ['', '## Remaining verification queue', '']
for r in sorted([x for x in out if x['final_classification']=='UNVERIFIED'], key=lambda x:(-(x.get('market_intelligence_value')=='HIGH'),x['name']))[:120]:
    md.append(f"- {r['name']} — {r.get('country','?')} — `{r.get('policy_lane')}` — evidence {r.get('evidence_score',0)}% — {r.get('base_url')}")
(ROOT/'SOURCE_VERIFICATION_MATRIX.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
snapshot={'version':version,'generated_from':'config/sources.json','sources':len(out),'active':sum(x.get('status')=='active' for x in out),'daily':sum(x.get('policy_lane')=='DAILY_PROJECT_SCAN' for x in out),'daily_execution_ready':sum(x.get('policy_lane')=='DAILY_PROJECT_SCAN' and x.get('execution_ready') for x in out),'global_discovery':sum(x.get('policy_lane')=='GLOBAL_DISCOVERY' for x in out),'needs_analysis':sum(x.get('policy_lane')=='NEEDS_ANALYSIS' for x in out),'blocked_iran':sum(x.get('policy_lane')=='BLOCKED_IRAN' for x in out),'verification_counts':dict(counts)}
(ROOT/'reports'/'release_snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(snapshot,ensure_ascii=False,indent=2))

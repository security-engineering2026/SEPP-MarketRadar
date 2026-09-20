from __future__ import annotations
import json,re
from datetime import datetime,timezone

INJECTION_PATTERNS=(
    r'ignore\s+(all|any|previous|prior)\s+instructions',
    r'system\s+message',
    r'developer\s+message',
    r'override\s+(policy|safety|approval)',
    r'execute\s+without\s+approval',
    r'bypass\s+(captcha|2fa|kyc|security)',
)

def detect_prompt_injection(text):
    hits=[p for p in INJECTION_PATTERNS if re.search(p,str(text or ''),re.I)]
    return {'suspicious':bool(hits),'hits':hits,'confidence':min(1,.35+.2*len(hits)) if hits else 0}

def evidence_is_authoritative(evidence):
    # Evidence is data. Authority comes from policy/runtime validation, never from the evidence text itself.
    e=evidence if isinstance(evidence,dict) else {}
    return bool(e.get('attested_acquisition') and e.get('policy_verified') and e.get('observed_at'))

def security_scan(c):
    findings=[]
    rows=c.execute('SELECT id,title,description,url FROM opportunities').fetchall()
    for r in rows:
        x=detect_prompt_injection((r['title'] or '')+' '+(r['description'] or ''))
        if x['suspicious']:
            findings.append({'type':'PROMPT_INJECTION','severity':'HIGH','target':str(r['id']),'evidence':x})
            c.execute("INSERT INTO security_findings(finding_type,severity,target,evidence_json,status,created_at) VALUES(?,?,?,?,?,?)",('PROMPT_INJECTION','HIGH',str(r['id']),json.dumps(x),'OPEN',datetime.now(timezone.utc).isoformat()))
    c.commit(); return findings

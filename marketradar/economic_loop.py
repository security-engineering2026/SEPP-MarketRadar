from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

APPLICATION_STATES = {
    'DISCOVERED','ELIGIBILITY_CHECK','RECOMMENDED','APPROVAL_PENDING','SUBMITTED','VIEWED',
    'MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','IN_PROGRESS','DELIVERED','PAID','REJECTED','EXPIRED','CANCELLED'
}

STATUS_MAP = {
    'submitted':'SUBMITTED','pending':'SUBMITTED','sent':'SUBMITTED','applied':'SUBMITTED',
    'viewed':'VIEWED','seen':'VIEWED','message':'MESSAGE_RECEIVED','message_received':'MESSAGE_RECEIVED',
    'negotiation':'NEGOTIATION','interview':'NEGOTIATION','accepted':'ACCEPTED','awarded':'ACCEPTED',
    'started':'IN_PROGRESS','in_progress':'IN_PROGRESS','delivered':'DELIVERED','completed':'DELIVERED',
    'paid':'PAID','payment_received':'PAID','rejected':'REJECTED','declined':'REJECTED','expired':'EXPIRED','cancelled':'CANCELLED'
}

def now(): return datetime.now(timezone.utc).isoformat()
def _digest(v): return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

def ensure_schema(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS application_tracking(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER UNIQUE NOT NULL, source TEXT NOT NULL,
      external_ref TEXT, status_url TEXT, tracking_mode TEXT NOT NULL DEFAULT 'MANUAL_EVIDENCE',
      poll_interval_minutes INTEGER NOT NULL DEFAULT 30, next_poll_at TEXT, last_polled_at TEXT,
      last_status TEXT, last_confidence REAL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1,
      credential_env TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS application_status_observations(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL, observed_at TEXT NOT NULL,
      source TEXT NOT NULL, external_ref TEXT, raw_status TEXT NOT NULL, normalized_status TEXT,
      confidence REAL NOT NULL, evidence_url TEXT, evidence_text TEXT, payload_sha256 TEXT NOT NULL,
      accepted INTEGER NOT NULL DEFAULT 0, actor TEXT NOT NULL DEFAULT 'system'
    );
    CREATE INDEX IF NOT EXISTS idx_application_tracking_due ON application_tracking(enabled,next_poll_at);
    CREATE INDEX IF NOT EXISTS idx_application_status_obs_opp ON application_status_observations(opportunity_id,observed_at);
    CREATE TABLE IF NOT EXISTS project_milestones(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL, name TEXT NOT NULL,
      due_at TEXT, completed_at TEXT, status TEXT NOT NULL DEFAULT 'OPEN',
      evidence_ref TEXT, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS project_communications(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL, channel TEXT NOT NULL,
      direction TEXT NOT NULL, occurred_at TEXT NOT NULL, subject TEXT, body TEXT,
      external_ref TEXT, evidence_ref TEXT, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS payment_verification_attempts(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL, payment_ref TEXT NOT NULL,
      checked_at TEXT NOT NULL, method TEXT NOT NULL, status TEXT NOT NULL,
      amount REAL, currency TEXT, evidence_ref TEXT, external_ref TEXT, details TEXT
    );
    ''')
    c.commit()

def register_tracking(c, opportunity_id, source, external_ref=None, status_url=None, mode='MANUAL_EVIDENCE', poll_interval_minutes=30, credential_env=None):
    if mode not in {'MANUAL_EVIDENCE','AUTHORIZED_API'}: raise ValueError('INVALID_TRACKING_MODE')
    ts=now(); nxt=datetime.fromtimestamp(datetime.now(timezone.utc).timestamp()+poll_interval_minutes*60,tz=timezone.utc).isoformat()
    c.execute('''INSERT INTO application_tracking(opportunity_id,source,external_ref,status_url,tracking_mode,poll_interval_minutes,next_poll_at,credential_env,created_at,updated_at)
                 VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(opportunity_id) DO UPDATE SET source=excluded.source,external_ref=COALESCE(excluded.external_ref,application_tracking.external_ref),status_url=COALESCE(excluded.status_url,application_tracking.status_url),tracking_mode=excluded.tracking_mode,poll_interval_minutes=excluded.poll_interval_minutes,next_poll_at=excluded.next_poll_at,credential_env=excluded.credential_env,updated_at=excluded.updated_at''',
              (opportunity_id,source,external_ref,status_url,mode,int(poll_interval_minutes),nxt,credential_env,ts,ts))
    c.commit()

def _normalize(raw):
    key=str(raw or '').strip().lower().replace(' ','_').replace('-','_')
    return STATUS_MAP.get(key)

def record_status_observation(c, opportunity_id, source, raw_status, confidence=0.8, evidence_url=None, evidence_text=None, external_ref=None, actor='system'):
    normalized=_normalize(raw_status)
    payload={'raw_status':raw_status,'normalized_status':normalized,'evidence_url':evidence_url,'evidence_text':evidence_text,'external_ref':external_ref}
    digest=_digest(payload)
    accepted=0
    if normalized and normalized != 'PAID' and float(confidence)>=0.8:
        current=c.execute('SELECT state FROM opportunities WHERE id=?',(opportunity_id,)).fetchone()
        if current and normalized != current['state']:
            # Let the canonical transition engine enforce legal state changes.
            from .application import transition
            try:
                transition(c,opportunity_id,normalized,actor=actor,commit=False); accepted=1
            except Exception:
                accepted=0
    c.execute('''INSERT INTO application_status_observations(opportunity_id,observed_at,source,external_ref,raw_status,normalized_status,confidence,evidence_url,evidence_text,payload_sha256,accepted,actor)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(opportunity_id,now(),source,external_ref,raw_status,normalized,float(confidence),evidence_url,evidence_text,digest,accepted,actor))
    c.commit()
    return {'normalized_status':normalized,'accepted':bool(accepted),'confidence':float(confidence),'digest':digest,'reason': ('PAYMENT_STATUS_REQUIRES_PAYMENT_VERIFICATION' if normalized == 'PAID' else None)}

def _fetch_json(url, timeout=15, token=None):
    host=urlparse(url).hostname
    if not host or urlparse(url).scheme not in {'https','http'}: raise ValueError('TRACKING_URL_INVALID')
    headers={'Accept':'application/json','User-Agent':'SEPP-MarketRadar/6.1'}
    if token: headers['Authorization']='Bearer '+token
    req=Request(url,headers=headers,method='GET')
    try:
        with urlopen(req,timeout=timeout) as r:
            body=r.read(); return json.loads(body.decode('utf-8')), r.status
    except HTTPError as e: raise RuntimeError(f'HTTP_{e.code}') from e
    except URLError as e: raise RuntimeError(f'NETWORK_{e.reason}') from e

def poll_due_tracking(c, timeout=15, env=None):
    import os
    rows=c.execute("SELECT * FROM application_tracking WHERE enabled=1 AND tracking_mode='AUTHORIZED_API' AND status_url IS NOT NULL AND (next_poll_at IS NULL OR next_poll_at<=?) ORDER BY next_poll_at",(now(),)).fetchall()
    results=[]
    for row in rows:
        status='ERROR'; detail=None
        try:
            token=os.getenv(row['credential_env']) if row['credential_env'] else None
            payload,http_status=_fetch_json(row['status_url'],timeout=timeout,token=token)
            raw=payload.get('status') if isinstance(payload,dict) else None
            if raw is None and isinstance(payload,dict): raw=payload.get('state')
            if raw is None: raise ValueError('TRACKING_STATUS_MISSING')
            result=record_status_observation(c,row['opportunity_id'],row['source'],raw,float(payload.get('confidence',0.9)) if isinstance(payload,dict) else 0.9,payload.get('evidence_url') if isinstance(payload,dict) else row['status_url'],json.dumps(payload,ensure_ascii=False,default=str),row['external_ref'])
            status='OK'; detail=result
        except Exception as exc:
            detail={'error':type(exc).__name__+': '+str(exc)}
        nxt=datetime.fromtimestamp(datetime.now(timezone.utc).timestamp()+int(row['poll_interval_minutes'])*60,tz=timezone.utc).isoformat()
        c.execute('UPDATE application_tracking SET last_polled_at=?,next_poll_at=?,last_status=?,last_confidence=?,updated_at=? WHERE id=?',(now(),nxt,detail.get('normalized_status') if isinstance(detail,dict) else None,float(detail.get('confidence',0)) if isinstance(detail,dict) else 0,now(),row['id']))
        c.commit(); results.append({'opportunity_id':row['opportunity_id'],'status':status,'detail':detail})
    return results


def ensure_payment_poll_schema(c):
    c.executescript("""
    CREATE TABLE IF NOT EXISTS payment_verification_sources(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER UNIQUE NOT NULL, payment_ref TEXT NOT NULL,
      status_url TEXT NOT NULL, credential_env TEXT, poll_interval_minutes INTEGER NOT NULL DEFAULT 30,
      next_poll_at TEXT, last_polled_at TEXT, enabled INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_payment_verify_due ON payment_verification_sources(enabled,next_poll_at);
    """)
    c.commit()

def register_payment_poll(c, opportunity_id, payment_ref, status_url, poll_interval_minutes=30, credential_env=None):
    ensure_payment_poll_schema(c)
    parsed=urlparse(status_url)
    if parsed.scheme not in {'https','http'} or not parsed.hostname: raise ValueError('PAYMENT_STATUS_URL_INVALID')
    ts=now(); nxt=datetime.fromtimestamp(datetime.now(timezone.utc).timestamp()+int(poll_interval_minutes)*60,tz=timezone.utc).isoformat()
    c.execute("""INSERT INTO payment_verification_sources(opportunity_id,payment_ref,status_url,credential_env,poll_interval_minutes,next_poll_at,created_at,updated_at)
                 VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(opportunity_id) DO UPDATE SET payment_ref=excluded.payment_ref,status_url=excluded.status_url,
                 credential_env=excluded.credential_env,poll_interval_minutes=excluded.poll_interval_minutes,next_poll_at=excluded.next_poll_at,enabled=1,updated_at=excluded.updated_at""",
              (opportunity_id,payment_ref,status_url,credential_env,int(poll_interval_minutes),nxt,ts,ts)); c.commit()

def poll_due_payment_verification(c, timeout=15):
    ensure_payment_poll_schema(c); import os
    rows=c.execute("SELECT * FROM payment_verification_sources WHERE enabled=1 AND next_poll_at<=? ORDER BY next_poll_at",(now(),)).fetchall(); results=[]
    for row in rows:
        status='ERROR'; detail=None
        try:
            token=os.getenv(row['credential_env']) if row['credential_env'] else None
            payload,http_status=_fetch_json(row['status_url'],timeout=timeout,token=token)
            raw=str(payload.get('status') or payload.get('state') or '').upper() if isinstance(payload,dict) else ''
            mapped={'VERIFIED':'VERIFIED','SETTLED':'VERIFIED','RECEIVED':'VERIFIED','PENDING':'PENDING','NOT_VERIFIED':'NOT_VERIFIED','FAILED':'FAILED'}.get(raw)
            if not mapped: raise ValueError('PAYMENT_STATUS_UNKNOWN')
            evidence_ref=(payload.get('evidence_url') or row['status_url']) if isinstance(payload,dict) else row['status_url']
            details=json.dumps(payload,ensure_ascii=False,default=str)
            record_payment_check(c,row['opportunity_id'],row['payment_ref'],'AUTHORIZED_API',mapped,payload.get('amount') if isinstance(payload,dict) else None,payload.get('currency') if isinstance(payload,dict) else None,evidence_ref,row['payment_ref'],details)
            if mapped=='VERIFIED':
                from .application import verify_payment
                verify_payment(c,row['opportunity_id'],row['payment_ref'],'VERIFIED',actor='authorized_payment_api')
            status='OK'; detail={'status':mapped,'http_status':http_status}
        except Exception as exc:
            detail={'error':type(exc).__name__+': '+str(exc)}
        nxt=datetime.fromtimestamp(datetime.now(timezone.utc).timestamp()+int(row['poll_interval_minutes'])*60,tz=timezone.utc).isoformat()
        c.execute('UPDATE payment_verification_sources SET last_polled_at=?,next_poll_at=?,updated_at=? WHERE id=?',(now(),nxt,now(),row['id'])); c.commit()
        results.append({'opportunity_id':row['opportunity_id'],'status':status,'detail':detail})
    return results

def add_milestone(c, opportunity_id, name, due_at=None, notes=None):
    ts=now(); c.execute('INSERT INTO project_milestones(opportunity_id,name,due_at,notes,created_at,updated_at) VALUES(?,?,?,?,?,?)',(opportunity_id,name,due_at,notes,ts,ts)); c.commit(); return c.execute('SELECT last_insert_rowid()').fetchone()[0]

def complete_milestone(c, milestone_id, evidence_ref=None, notes=None):
    c.execute('UPDATE project_milestones SET status="COMPLETED",completed_at=?,evidence_ref=COALESCE(?,evidence_ref),notes=COALESCE(?,notes),updated_at=? WHERE id=?',(now(),evidence_ref,notes,now(),milestone_id)); c.commit()

def add_communication(c, opportunity_id, channel, direction, subject=None, body=None, external_ref=None, evidence_ref=None, occurred_at=None):
    c.execute('INSERT INTO project_communications(opportunity_id,channel,direction,occurred_at,subject,body,external_ref,evidence_ref,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(opportunity_id,channel,direction,occurred_at or now(),subject,body,external_ref,evidence_ref,now())); c.commit()

def record_payment_check(c, opportunity_id, payment_ref, method, status, amount=None, currency=None, evidence_ref=None, external_ref=None, details=None):
    if status not in {'VERIFIED','PENDING','NOT_VERIFIED','FAILED'}: raise ValueError('INVALID_PAYMENT_CHECK_STATUS')
    c.execute('INSERT INTO payment_verification_attempts(opportunity_id,payment_ref,checked_at,method,status,amount,currency,evidence_ref,external_ref,details) VALUES(?,?,?,?,?,?,?,?,?,?)',(opportunity_id,payment_ref,now(),method,status,amount,currency,evidence_ref,external_ref,details)); c.commit(); return c.execute('SELECT last_insert_rowid()').fetchone()[0]

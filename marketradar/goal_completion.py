from __future__ import annotations
import hashlib, hmac, json, math, re, sqlite3, time
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit

from . import __version__

VERSION = __version__

SCHEMA = r'''
CREATE TABLE IF NOT EXISTS entities(id INTEGER PRIMARY KEY, entity_type TEXT NOT NULL, canonical_name TEXT NOT NULL, normalized_name TEXT NOT NULL, country TEXT, domain TEXT, external_key TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(entity_type,normalized_name,domain));
CREATE TABLE IF NOT EXISTS entity_aliases(id INTEGER PRIMARY KEY, entity_id INTEGER NOT NULL, alias TEXT NOT NULL, normalized_alias TEXT NOT NULL, evidence_id INTEGER, confidence REAL NOT NULL DEFAULT 0, UNIQUE(entity_id,normalized_alias));
CREATE TABLE IF NOT EXISTS identity_matches(id INTEGER PRIMARY KEY, entity_type TEXT NOT NULL, left_key TEXT NOT NULL, right_key TEXT NOT NULL, decision TEXT NOT NULL, confidence REAL NOT NULL, evidence_json TEXT NOT NULL, observed_at TEXT NOT NULL, UNIQUE(entity_type,left_key,right_key));
CREATE TABLE IF NOT EXISTS parties(id INTEGER PRIMARY KEY, entity_id INTEGER UNIQUE NOT NULL, party_type TEXT NOT NULL, reputation_score REAL DEFAULT 0.5, payment_score REAL DEFAULT 0.5, response_score REAL DEFAULT 0.5, repeat_demand_score REAL DEFAULT 0.0, behavior_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS party_relationships(id INTEGER PRIMARY KEY, source_entity_id INTEGER NOT NULL, target_entity_id INTEGER NOT NULL, relation TEXT NOT NULL, confidence REAL NOT NULL, evidence_json TEXT NOT NULL, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, UNIQUE(source_entity_id,target_entity_id,relation));
CREATE TABLE IF NOT EXISTS claims(id INTEGER PRIMARY KEY, entity_type TEXT, entity_id INTEGER, opportunity_id INTEGER, claim_type TEXT NOT NULL, claim_value TEXT NOT NULL, confidence REAL NOT NULL, observed_at TEXT NOT NULL, expires_at TEXT, policy_version TEXT, UNIQUE(opportunity_id,claim_type,claim_value));
CREATE TABLE IF NOT EXISTS claim_evidence(claim_id INTEGER NOT NULL,evidence_id INTEGER NOT NULL,PRIMARY KEY(claim_id,evidence_id));
CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, party_entity_id INTEGER NOT NULL, source TEXT, author_key TEXT, text TEXT, rating REAL, observed_at TEXT NOT NULL, provenance_root TEXT, verified INTEGER, account_age_days REAL);
CREATE TABLE IF NOT EXISTS review_analysis(review_id INTEGER PRIMARY KEY, duplicate_group TEXT, burst_score REAL DEFAULT 0, author_risk REAL DEFAULT 0, provenance_independence REAL DEFAULT 0, manipulation_flags TEXT NOT NULL DEFAULT '[]', state TEXT NOT NULL DEFAULT 'UNKNOWN', confidence REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS trust_assessments(id INTEGER PRIMARY KEY, entity_id INTEGER, target_type TEXT NOT NULL, target_id TEXT NOT NULL, state TEXT NOT NULL, confidence REAL NOT NULL, independent_provenance_count INTEGER DEFAULT 0, flags_json TEXT NOT NULL, observed_at TEXT NOT NULL, UNIQUE(entity_id,target_type,target_id));
CREATE TABLE IF NOT EXISTS demand_clusters(id INTEGER PRIMARY KEY, cluster_key TEXT UNIQUE NOT NULL, label TEXT NOT NULL, category TEXT, skill_signature TEXT NOT NULL, buyer_signature TEXT, geography_signature TEXT, payment_signature TEXT, source_family_signature TEXT, opportunity_count INTEGER NOT NULL, unique_parties INTEGER DEFAULT 0, total_budget REAL DEFAULT 0, median_budget REAL DEFAULT 0, median_ttm REAL DEFAULT 0, competition REAL DEFAULT 0, trend_score REAL DEFAULT 0, first_seen TEXT, last_seen TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS opportunity_cluster(opportunity_id INTEGER NOT NULL, cluster_id INTEGER NOT NULL, confidence REAL NOT NULL, PRIMARY KEY(opportunity_id,cluster_id));
CREATE TABLE IF NOT EXISTS ttm_observations(id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL, stage TEXT NOT NULL, started_at TEXT, ended_at TEXT, duration_hours REAL, probability REAL DEFAULT 0.5, evidence_id INTEGER, UNIQUE(opportunity_id,stage));
CREATE TABLE IF NOT EXISTS ttm_predictions(opportunity_id INTEGER PRIMARY KEY, expected_hours REAL NOT NULL, p_paid REAL NOT NULL, expected_value REAL NOT NULL, bottleneck_stage TEXT, confidence REAL NOT NULL, calculated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decision_snapshots(id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, top7_json TEXT NOT NULL, do_now_json TEXT NOT NULL, approval_json TEXT NOT NULL, monitor_json TEXT NOT NULL, blocked_json TEXT NOT NULL, unknown_json TEXT NOT NULL, rationale_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decision_traces(id INTEGER PRIMARY KEY, decision_id TEXT UNIQUE NOT NULL, decision_type TEXT NOT NULL, policy_version TEXT, target_type TEXT, target_id TEXT, action TEXT, parameters_json TEXT, parameters_digest TEXT, evidence_ids_json TEXT NOT NULL, evidence_digest TEXT NOT NULL, claims_json TEXT NOT NULL, state_snapshot_json TEXT NOT NULL, ranking_context_json TEXT NOT NULL, actor TEXT NOT NULL, model TEXT, reason TEXT NOT NULL, approval_ref TEXT, approval_expires_at INTEGER, approval_nonce TEXT, outcome TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_decision_traces_target ON decision_traces(target_type,target_id,created_at DESC);
CREATE TABLE IF NOT EXISTS workflow_events(id INTEGER PRIMARY KEY, workflow_id TEXT NOT NULL, opportunity_id INTEGER, event_type TEXT NOT NULL, state TEXT NOT NULL, attempt INTEGER DEFAULT 0, idempotency_key TEXT UNIQUE NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS workflow_state(workflow_id TEXT PRIMARY KEY, opportunity_id INTEGER, state TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0, next_retry_at TEXT, locked_until TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS action_authorizations(id INTEGER PRIMARY KEY, approval_id TEXT UNIQUE NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL, parameters_digest TEXT NOT NULL, evidence_digest TEXT NOT NULL, policy_version TEXT NOT NULL, actor TEXT NOT NULL, issued_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, nonce TEXT UNIQUE NOT NULL, status TEXT NOT NULL DEFAULT 'ISSUED', used_at INTEGER);
CREATE TABLE IF NOT EXISTS action_attempts(id INTEGER PRIMARY KEY, approval_id TEXT NOT NULL, attempt_no INTEGER NOT NULL, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL, result_digest TEXT, error TEXT, UNIQUE(approval_id,attempt_no));
CREATE TABLE IF NOT EXISTS financial_observations(id INTEGER PRIMARY KEY, opportunity_id INTEGER, gross_amount REAL NOT NULL, fees REAL DEFAULT 0, tax_cost REAL DEFAULT 0, transfer_cost REAL DEFAULT 0, other_cost REAL DEFAULT 0, currency TEXT NOT NULL, work_hours REAL DEFAULT 0, received_at TEXT, source TEXT, net_amount REAL NOT NULL, roi REAL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS revenue_intelligence(id INTEGER PRIMARY KEY, dimension TEXT NOT NULL, dimension_key TEXT NOT NULL, currency TEXT NOT NULL, gross REAL DEFAULT 0, net REAL DEFAULT 0, hours REAL DEFAULT 0, jobs INTEGER DEFAULT 0, paid_jobs INTEGER DEFAULT 0, win_rate REAL DEFAULT 0, net_per_hour REAL DEFAULT 0, roi REAL DEFAULT 0, updated_at TEXT NOT NULL, UNIQUE(dimension,dimension_key,currency));
CREATE TABLE IF NOT EXISTS product_recommendations(id INTEGER PRIMARY KEY, recommendation_type TEXT NOT NULL, title TEXT NOT NULL, rationale TEXT NOT NULL, demand_score REAL NOT NULL, revenue_score REAL NOT NULL, confidence REAL NOT NULL, evidence_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'RECOMMENDED', created_at TEXT NOT NULL, UNIQUE(recommendation_type,title));
CREATE TABLE IF NOT EXISTS pricing_recommendations(id INTEGER PRIMARY KEY, service_key TEXT NOT NULL, currency TEXT NOT NULL, low REAL, target REAL, high REAL, sample_count INTEGER DEFAULT 0, confidence REAL DEFAULT 0, rationale TEXT, updated_at TEXT NOT NULL, UNIQUE(service_key,currency));
CREATE TABLE IF NOT EXISTS skill_gaps(id INTEGER PRIMARY KEY, skill TEXT NOT NULL, demand_score REAL NOT NULL, current_capability REAL DEFAULT 0, gap_score REAL NOT NULL, evidence_json TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(skill));
CREATE TABLE IF NOT EXISTS portfolio_recommendations(id INTEGER PRIMARY KEY, skill TEXT NOT NULL, evidence_count INTEGER DEFAULT 0, demand_score REAL DEFAULT 0, gap_score REAL DEFAULT 0, action TEXT NOT NULL, rationale TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(skill));
CREATE TABLE IF NOT EXISTS market_signals(id INTEGER PRIMARY KEY, signal_type TEXT NOT NULL, signal_key TEXT NOT NULL, value_json TEXT NOT NULL, confidence REAL NOT NULL, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, UNIQUE(signal_type,signal_key));
CREATE TABLE IF NOT EXISTS security_findings(id INTEGER PRIMARY KEY, finding_type TEXT NOT NULL, severity TEXT NOT NULL, target TEXT NOT NULL, evidence_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN', created_at TEXT NOT NULL);
'''


def now(): return datetime.now(timezone.utc).isoformat()
def _norm(s): return re.sub(r'[^a-z0-9]+',' ',str(s or '').lower()).strip()
def _tokens(s): return set(re.findall(r'[a-z0-9]{3,}',str(s or '').lower()))
def _sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
def _safe_float(v, default=0.0):
    try:
        x=float(v); return x if math.isfinite(x) else default
    except Exception: return default

def ensure_schema(c):
    c.executescript(SCHEMA)
    c.execute("CREATE INDEX IF NOT EXISTS idx_entities_domain ON entities(domain)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_identity_left ON identity_matches(left_key,decision)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_reviews_party ON reviews(party_entity_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ttm_opp ON ttm_observations(opportunity_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_fin_opp ON financial_observations(opportunity_id)")
    immutable = ('workflow_events','financial_observations','action_attempts','reviews','identity_matches','decision_traces')
    c.execute("CREATE TRIGGER IF NOT EXISTS trg_decision_traces_no_update BEFORE UPDATE ON decision_traces BEGIN SELECT RAISE(ABORT,'IMMUTABLE_LEDGER'); END")
    for table in immutable:
        c.execute(f"CREATE TRIGGER IF NOT EXISTS trg_{table}_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT,'IMMUTABLE_LEDGER'); END")
    c.commit()


def _entity_key(entity_type, name, domain=None):
    return f"{entity_type}:{_norm(name)}:{str(domain or '').lower()}"

def resolve_entity(c, entity_type, name, *, domain=None, country=None, external_key=None, evidence=None):
    n=_norm(name)
    if not n: return None
    d=str(domain or '').lower().strip() or None
    row=c.execute("SELECT * FROM entities WHERE entity_type=? AND normalized_name=? AND COALESCE(domain,'')=COALESCE(?, '')",(entity_type,n,d)).fetchone()
    if row: return row['id']
    # Candidate retrieval must not make POSSIBLE_MATCH unreachable: exact name/domain are fast paths above, while ambiguous similarity requires broader same-type candidates.
    candidates=c.execute("SELECT * FROM entities WHERE entity_type=?",(entity_type,)).fetchall()
    best=None; best_score=0
    nt=_tokens(n)
    for x in candidates:
        score=0.0
        xt=_tokens(x['normalized_name']); union=nt|xt
        if union: score=max(score,len(nt&xt)/len(union))
        if d and x['domain'] and d==x['domain']: score=max(score,0.98)
        if country and x['country'] and str(country).lower()==str(x['country']).lower(): score+=0.04
        if score>best_score: best,best_score=x, min(score,1.0)
    if best and best_score>=0.90:
        decision='MATCH'; conf=best_score
        c.execute("INSERT OR IGNORE INTO identity_matches(entity_type,left_key,right_key,decision,confidence,evidence_json,observed_at) VALUES(?,?,?,?,?,?,?)",(entity_type,_entity_key(entity_type,name,d),str(best['id']),decision,conf,json.dumps(evidence or {},ensure_ascii=False),now()))
        return best['id']
    ts=now()
    # Ambiguous similarity is explicitly recorded as POSSIBLE_MATCH; it never
    # silently merges identities. A new canonical entity remains separate until
    # stronger evidence resolves the relationship.
    decision='POSSIBLE_MATCH' if best and best_score>=0.65 else 'NO_MATCH'
    candidate_id=str(best['id']) if best and best_score>=0.65 else ''
    right_key=candidate_id or 'NO_MATCH'
    c.execute("INSERT OR IGNORE INTO identity_matches(entity_type,left_key,right_key,decision,confidence,evidence_json,observed_at) VALUES(?,?,?,?,?,?,?)",
              (entity_type,_entity_key(entity_type,name,d),right_key,decision,round(best_score,4),json.dumps({'candidate_entity_id':candidate_id,'evidence':evidence or {}},ensure_ascii=False),ts))
    c.execute("INSERT INTO entities(entity_type,canonical_name,normalized_name,country,domain,external_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(entity_type,name,n,country,d,external_key,ts,ts))
    eid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
    return eid


def link_party(c, entity_id, party_type, *, behavior=None):
    b=behavior or {}; rep=_safe_float(b.get('reputation_score'),.5); pay=_safe_float(b.get('payment_score'),.5); resp=_safe_float(b.get('response_score'),.5); repeat=_safe_float(b.get('repeat_demand_score'),0)
    c.execute("INSERT INTO parties(entity_id,party_type,reputation_score,payment_score,response_score,repeat_demand_score,behavior_json,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(entity_id) DO UPDATE SET party_type=excluded.party_type,reputation_score=excluded.reputation_score,payment_score=excluded.payment_score,response_score=excluded.response_score,repeat_demand_score=excluded.repeat_demand_score,behavior_json=excluded.behavior_json,updated_at=excluded.updated_at",(entity_id,party_type,rep,pay,resp,repeat,json.dumps(b,ensure_ascii=False),now()))


def party_from_opportunity(c, item, opportunity_id):
    raw=item.get('client') or item.get('buyer') or item.get('employer') or item.get('agency') or {}
    if isinstance(raw,str): raw={'name':raw}
    if not isinstance(raw,dict): raw={}
    name=raw.get('name') or item.get('client_name') or item.get('buyer_name') or item.get('employer_name')
    if not name: return None
    domain=raw.get('domain')
    if not domain:
        u=raw.get('url') or item.get('client_url')
        if u: domain=urlsplit(u).netloc.lower() or None
    ptype=str(raw.get('type') or item.get('party_type') or 'Client')
    eid=resolve_entity(c,ptype,name,domain=domain,country=item.get('country'),external_key=raw.get('id'),evidence={'opportunity_id':opportunity_id,'url':item.get('url')})
    link_party(c,eid,ptype,behavior=raw)
    c.execute("INSERT INTO party_relationships(source_entity_id,target_entity_id,relation,confidence,evidence_json,first_seen,last_seen) VALUES(?,?,?,?,?,?,?) ON CONFLICT(source_entity_id,target_entity_id,relation) DO UPDATE SET confidence=MAX(party_relationships.confidence,excluded.confidence),last_seen=excluded.last_seen",(eid,eid,'PARTICIPATES_IN',1.0,json.dumps({'opportunity_id':opportunity_id}),now(),now()))
    return eid


def analyze_reviews(c, party_entity_id):
    rows=c.execute('SELECT * FROM reviews WHERE party_entity_id=? ORDER BY observed_at',(party_entity_id,)).fetchall()
    if not rows: return {'state':'UNKNOWN','confidence':0,'independent_provenance_count':0,'flags':['NO_REVIEWS']}
    roots=Counter((r['provenance_root'] or r['source'] or 'UNKNOWN') for r in rows); authors=Counter((r['author_key'] or 'UNKNOWN') for r in rows); hashes=Counter(_sha(_norm(r['text'])) for r in rows if r['text'])
    flags=[]
    if len(rows)>=4 and max(roots.values())/len(rows)>=.75: flags.append('PROVENANCE_CONCENTRATION')
    if len(rows)>=4 and len(authors)/len(rows)<=.5: flags.append('LOW_AUTHOR_DIVERSITY')
    if any(v>1 for v in hashes.values()): flags.append('COPY_PASTE')
    times=[]
    for r in rows:
        try: times.append(datetime.fromisoformat(str(r['observed_at']).replace('Z','+00:00')).timestamp())
        except Exception: pass
    if len(times)>=4 and max(times)-min(times)<72*3600: flags.append('BURST')
    if any(r['verified']==0 for r in rows if r['verified'] is not None): flags.append('UNVERIFIED_REVIEWS')
    ind=len(roots); confidence=min(.98,.25+.12*ind+.05*min(10,len(rows)))
    state='HIGH_RISK' if len(flags)>=3 else 'MIXED' if flags else 'LOW_RISK'
    for r in rows:
        txt=_norm(r['text']); dg=_sha(txt)[:16] if txt else None
        rflags=[f for f in flags if f in {'COPY_PASTE','BURST','PROVENANCE_CONCENTRATION'}]
        c.execute("INSERT INTO review_analysis(review_id,duplicate_group,burst_score,author_risk,provenance_independence,manipulation_flags,state,confidence) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(review_id) DO UPDATE SET duplicate_group=excluded.duplicate_group,burst_score=excluded.burst_score,author_risk=excluded.author_risk,provenance_independence=excluded.provenance_independence,manipulation_flags=excluded.manipulation_flags,state=excluded.state,confidence=excluded.confidence",(r['id'],dg,1.0 if 'BURST' in flags else 0.0,1.0 if 'LOW_AUTHOR_DIVERSITY' in flags else 0.0,1/max(1,len(roots)),json.dumps(rflags),state,confidence))
    c.execute("INSERT INTO trust_assessments(entity_id,target_type,target_id,state,confidence,independent_provenance_count,flags_json,observed_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(entity_id,target_type,target_id) DO UPDATE SET state=excluded.state,confidence=excluded.confidence,independent_provenance_count=excluded.independent_provenance_count,flags_json=excluded.flags_json,observed_at=excluded.observed_at",(party_entity_id,'REPUTATION',str(party_entity_id),state,confidence,ind,json.dumps(flags),now()))
    return {'state':state,'confidence':round(confidence,3),'independent_provenance_count':ind,'flags':flags}


def _cluster_key(item):
    raw=item.get('skills') or item.get('skill_tags')
    text=' '.join(str(item.get(k,'')) for k in ('title','description','category','skills'))
    if raw:
        skills=raw if isinstance(raw,(list,tuple,set)) else [x.strip() for x in re.split(r'[,|/]+',str(raw)) if x.strip()]
    else:
        vocab=('python','excel','automation','api','scraping','data cleaning','data pipeline','dashboard','android','security','sql','javascript')
        skills=[x for x in vocab if x in text.lower()]
    if not skills: skills=[item.get('category') or 'general']
    skills=sorted(set(_norm(x) for x in skills))
    buyer=str(item.get('party_type') or 'client').lower()
    geo=str(item.get('country') or 'UNKNOWN').lower()
    pay=str(item.get('payment') or 'UNKNOWN').lower()
    fam=str(item.get('source_family') or 'UNKNOWN').lower()
    return '|'.join([','.join(skills[:8]),buyer,geo,pay,fam])


def build_demand_clusters(c, rows):
    groups=defaultdict(list)
    for r in rows: groups[_cluster_key(dict(r))].append(dict(r))
    out=[]
    for key,items in groups.items():
        if len(items)<2: continue
        budgets=sorted(_safe_float(x.get('budget')) for x in items if x.get('budget') is not None)
        ttms=sorted(_safe_float(x.get('time_to_money')) for x in items if x.get('time_to_money') is not None)
        skills=key.split('|')[0]; label=' + '.join([x.replace('_',' ') for x in skills.split(',') if x][:4]) or 'repeated demand'
        budgets2=budgets; med=budgets2[len(budgets2)//2] if budgets2 else 0
        tmed=ttms[len(ttms)//2] if ttms else 0
        comp=sum(_safe_float(x.get('competition_pressure'),.45) for x in items)/len(items)
        trend=min(1.0, len(items)/20)
        ts=now(); c.execute("INSERT INTO demand_clusters(cluster_key,label,category,skill_signature,buyer_signature,geography_signature,payment_signature,source_family_signature,opportunity_count,unique_parties,total_budget,median_budget,median_ttm,competition,trend_score,first_seen,last_seen,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(cluster_key) DO UPDATE SET label=excluded.label,opportunity_count=excluded.opportunity_count,total_budget=excluded.total_budget,median_budget=excluded.median_budget,median_ttm=excluded.median_ttm,competition=excluded.competition,trend_score=excluded.trend_score,last_seen=excluded.last_seen,updated_at=excluded.updated_at",(key,label,items[0].get('category'),skills,key.split('|')[1],key.split('|')[2],key.split('|')[3],key.split('|')[4],len(items),len({str(x.get('client_name') or x.get('buyer_name') or '') for x in items if x.get('client_name') or x.get('buyer_name')}),sum(budgets),med,tmed,comp,trend,min(str(x.get('first_seen') or now()) for x in items),max(str(x.get('last_seen') or now()) for x in items),ts))
        cid=c.execute('SELECT id FROM demand_clusters WHERE cluster_key=?',(key,)).fetchone()[0]
        for x in items:
            if x.get('id'): c.execute('INSERT OR REPLACE INTO opportunity_cluster(opportunity_id,cluster_id,confidence) VALUES(?,?,?)',(x['id'],cid,.85))
        out.append({'cluster_id':cid,'label':label,'count':len(items),'median_budget':med,'median_ttm':tmed,'trend_score':trend})
    return out


def calculate_ttm(c, opportunity_id):
    stages=['DISCOVERY','PROPOSAL','RESPONSE','NEGOTIATION','ACCEPTANCE','DELIVERY','PAYMENT']
    rows=c.execute('SELECT * FROM ttm_observations WHERE opportunity_id=?',(opportunity_id,)).fetchall()
    expected=0; p=1; bottleneck=None; max_h=-1
    for r in rows:
        h=_safe_float(r['duration_hours'],24); prob=max(.01,min(1,_safe_float(r['probability'],.5))); expected+=h; p*=prob
        if h>max_h: max_h=h; bottleneck=r['stage']
    if not rows:
        opp=c.execute('SELECT * FROM opportunities WHERE id=?',(opportunity_id,)).fetchone()
        budget=_safe_float(opp['budget'] if opp else 0)
        expected=72 + (24 if budget>1000 else 0)
        p=max(.05,min(.9,_safe_float(opp['acceptance_probability'] if opp else .5,.5)))
        bottleneck='PROPOSAL'
    budget=_safe_float(c.execute('SELECT budget FROM opportunities WHERE id=?',(opportunity_id,)).fetchone()[0] or 0)
    ev=budget*p
    conf=min(.95,.3+.1*len(rows)); ts=now()
    c.execute("INSERT INTO ttm_predictions(opportunity_id,expected_hours,p_paid,expected_value,bottleneck_stage,confidence,calculated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(opportunity_id) DO UPDATE SET expected_hours=excluded.expected_hours,p_paid=excluded.p_paid,expected_value=excluded.expected_value,bottleneck_stage=excluded.bottleneck_stage,confidence=excluded.confidence,calculated_at=excluded.calculated_at",(opportunity_id,expected,p,ev,bottleneck,conf,ts))
    return {'expected_hours':round(expected,2),'p_paid':round(p,4),'expected_value':round(ev,2),'bottleneck_stage':bottleneck,'confidence':round(conf,3)}


def record_decision_trace(c, *, decision_type, policy_version, target_type, target_id, action, parameters, evidence_ids, claims, state_snapshot, ranking_context, actor, reason, approval_ref=None, approval_expires_at=None, approval_nonce=None, model=None, outcome='PENDING'):
    """Persist an immutable, claim/evidence-bound trace for every consequential decision."""
    ids=sorted({int(x) for x in (evidence_ids or [])})
    did='DEC-'+_sha([decision_type,target_type,target_id,action,parameters,ids,policy_version,actor,now()])[:32]
    c.execute("INSERT INTO decision_traces(decision_id,decision_type,policy_version,target_type,target_id,action,parameters_json,parameters_digest,evidence_ids_json,evidence_digest,claims_json,state_snapshot_json,ranking_context_json,actor,model,reason,approval_ref,approval_expires_at,approval_nonce,outcome,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (did,decision_type,policy_version,target_type,str(target_id) if target_id is not None else None,action,json.dumps(parameters or {},sort_keys=True,ensure_ascii=False,default=str),_sha(parameters or {}),json.dumps(ids),_sha(ids),json.dumps(claims or {},sort_keys=True,ensure_ascii=False,default=str),json.dumps(state_snapshot or {},sort_keys=True,ensure_ascii=False,default=str),json.dumps(ranking_context or {},sort_keys=True,ensure_ascii=False,default=str),actor,model,reason,approval_ref,approval_expires_at,approval_nonce,outcome,now()))
    return did


def decision_center(c):
    rows=[dict(r) for r in c.execute("SELECT * FROM opportunities WHERE state='DISCOVERED' ORDER BY COALESCE(rank_score,score) DESC LIMIT 100").fetchall()]
    top7=rows[:7]; do_now=[x for x in top7 if x.get('eligibility')=='EXECUTE' and x.get('application_ready')][:3]
    approval=[x for x in top7 if x.get('eligibility') in {'EXECUTE','REVIEW'} and x not in do_now][:2]
    monitor=[x for x in top7 if x not in do_now and x not in approval][:2]
    blocked=[x for x in rows if x.get('eligibility')=='BLOCK'][:20]; unknown=[x for x in rows if x.get('eligibility')=='UNKNOWN'][:20]
    payload={'top7':top7,'do_now':do_now,'approval_required':approval,'monitor':monitor,'blocked':blocked,'unknown':unknown}
    rationale={str(x['id']):{'why_now':('high rank + execution ready' if x in do_now else 'ranked for review'),'evidence_confidence':x.get('evidence_confidence'),'eligibility':x.get('eligibility'),'ttm':x.get('time_to_money')} for x in top7}
    snapshot_id = c.execute("INSERT INTO decision_snapshots(created_at,top7_json,do_now_json,approval_json,monitor_json,blocked_json,unknown_json,rationale_json) VALUES(?,?,?,?,?,?,?,?)",(now(),json.dumps(top7,default=str),json.dumps(do_now,default=str),json.dumps(approval,default=str),json.dumps(monitor,default=str),json.dumps(blocked,default=str),json.dumps(unknown,default=str),json.dumps(rationale))).lastrowid
    # The snapshot itself is the reproducibility anchor for the Daily Intelligence Center.
    # Record one immutable trace over every surfaced decision bucket, including BLOCK/UNKNOWN,
    # rather than treating only the Top-7 recommendations as consequential state.
    snapshot_targets = {
        'top7': [int(x['id']) for x in top7],
        'do_now': [int(x['id']) for x in do_now],
        'approval_required': [int(x['id']) for x in approval],
        'monitor': [int(x['id']) for x in monitor],
        'blocked': [int(x['id']) for x in blocked],
        'unknown': [int(x['id']) for x in unknown],
    }
    record_decision_trace(
        c, decision_type='DAILY_SNAPSHOT', policy_version='policy.v1',
        target_type='DECISION_SNAPSHOT', target_id=snapshot_id, action='CLASSIFY',
        parameters={'snapshot_id': snapshot_id},
        evidence_ids=sorted({int(r['id']) for oid in snapshot_targets['top7'] for r in c.execute('SELECT id FROM evidence WHERE opportunity_id=? ORDER BY id',(oid,)).fetchall()}),
        claims={'buckets': snapshot_targets},
        state_snapshot={'counts': {k: len(v) for k, v in snapshot_targets.items()}},
        ranking_context={'top7_ids': snapshot_targets['top7']},
        actor='system:decision_center', reason='Immutable snapshot of all surfaced decision buckets'
    )
    for item in top7:
        oid=int(item['id'])
        ev=[r['id'] for r in c.execute('SELECT id FROM evidence WHERE opportunity_id=? ORDER BY id',(oid,)).fetchall()]
        claims={r['claim_type']:{'value':r['claim_value'],'confidence':r['confidence'],'observed_at':r['observed_at'],'policy_version':r['policy_version']} for r in c.execute('SELECT claim_type,claim_value,confidence,observed_at,policy_version FROM claims WHERE opportunity_id=? ORDER BY id',(oid,)).fetchall()}
        record_decision_trace(c, decision_type='DAILY_RECOMMENDATION', policy_version='policy.v1', target_type='OPPORTUNITY', target_id=oid, action='RECOMMEND', parameters={'opportunity_id':oid}, evidence_ids=ev, claims=claims, state_snapshot={'state':item.get('state'),'eligibility':item.get('eligibility'),'application_ready':item.get('application_ready'),'rank_score':item.get('rank_score',item.get('score'))}, ranking_context={'rank_score':item.get('rank_score',item.get('score')),'skill_fit':item.get('skill_fit'),'difficulty_fit':item.get('difficulty_fit'),'learning_value':item.get('learning_value'),'competition_score':item.get('competition_score'),'application_speed_score':item.get('application_speed_score'),'freshness_score':item.get('freshness_score'),'time_to_money':item.get('time_to_money')}, actor='system:decision_center', reason=rationale[str(oid)]['why_now'])
    c.commit(); return payload


def record_financial(c, opportunity_id, gross, currency, fees=0,tax_cost=0,transfer_cost=0,other_cost=0,work_hours=0,received_at=None,source='manual'):
    gross=_safe_float(gross); costs=sum(_safe_float(x) for x in (fees,tax_cost,transfer_cost,other_cost)); net=gross-costs
    roi=(net/costs) if costs>0 else None
    ts=now(); c.execute("INSERT INTO financial_observations(opportunity_id,gross_amount,fees,tax_cost,transfer_cost,other_cost,currency,work_hours,received_at,source,net_amount,roi,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(opportunity_id,gross,fees,tax_cost,transfer_cost,other_cost,currency,work_hours,received_at,source,net,roi,ts))
    return {'gross':gross,'net':net,'costs':costs,'roi':roi}


def refresh_revenue_intelligence(c):
    dims=defaultdict(lambda:[0,0,0,0,0])
    rows=c.execute('''SELECT f.*,o.source AS opportunity_source,o.category FROM financial_observations f LEFT JOIN opportunities o ON o.id=f.opportunity_id''').fetchall()
    for r in rows:
        for dim,key in [('source',r['opportunity_source'] or r['source'] or 'UNKNOWN'),('category',r['category'] or 'UNKNOWN')]:
            x=dims[(dim,str(key),r['currency'])]; x[0]+=r['gross_amount']; x[1]+=r['net_amount']; x[2]+=r['work_hours']; x[3]+=1; x[4]+=1 if r['net_amount']>0 else 0
    ts=now()
    for (dim,key,curr),x in dims.items():
        nph=x[1]/x[2] if x[2]>0 else 0; roi=(x[1]/max(1,x[0]-x[1])) if x[0]>x[1] else 0
        c.execute("INSERT INTO revenue_intelligence(dimension,dimension_key,currency,gross,net,hours,jobs,paid_jobs,win_rate,net_per_hour,roi,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(dimension,dimension_key,currency) DO UPDATE SET gross=excluded.gross,net=excluded.net,hours=excluded.hours,jobs=excluded.jobs,paid_jobs=excluded.paid_jobs,win_rate=excluded.win_rate,net_per_hour=excluded.net_per_hour,roi=excluded.roi,updated_at=excluded.updated_at",(dim,key,curr,x[0],x[1],x[2],x[3],x[4],x[4]/max(1,x[3]),nph,roi,ts))
    c.commit(); return c.execute('SELECT * FROM revenue_intelligence ORDER BY net DESC').fetchall()


def product_engine(c):
    clusters=c.execute('SELECT * FROM demand_clusters ORDER BY trend_score DESC,opportunity_count DESC').fetchall(); recs=[]
    for cl in clusters:
        demand=min(1,cl['opportunity_count']/20)*.6+cl['trend_score']*.4
        rev=c.execute("SELECT COALESCE(AVG(net_per_hour),0) FROM revenue_intelligence WHERE dimension='category' AND dimension_key=?",(cl['category'] or 'UNKNOWN',)).fetchone()[0]
        revenue=min(1,_safe_float(rev)/100) if rev else 0
        conf=min(.95,.35+demand*.5+revenue*.15)
        title=f"Service/Tool: {cl['label']}"
        rationale=f"Repeated demand={cl['opportunity_count']}; median budget={cl['median_budget']}; median TTM hours={cl['median_ttm']}; trend={cl['trend_score']:.2f}."
        c.execute("INSERT INTO product_recommendations(recommendation_type,title,rationale,demand_score,revenue_score,confidence,evidence_json,created_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(recommendation_type,title) DO UPDATE SET rationale=excluded.rationale,demand_score=excluded.demand_score,revenue_score=excluded.revenue_score,confidence=excluded.confidence,evidence_json=excluded.evidence_json,created_at=excluded.created_at",('SERVICE_OR_TOOL',title,rationale,demand,revenue,conf,json.dumps({'cluster_id':cl['id'],'opportunities':cl['opportunity_count']}),now()))
        recs.append({'title':title,'demand_score':demand,'revenue_score':revenue,'confidence':conf})
    c.commit(); return recs


def skill_portfolio_engine(c, profile=None):
    profile=profile or {}
    current=profile.get('skills',{}) if isinstance(profile,dict) else {}
    if isinstance(current, (list, tuple, set)):
        current={str(x):1.0 for x in current}
    elif not isinstance(current, dict):
        current={}
    rows=c.execute('SELECT * FROM demand_clusters').fetchall(); agg=Counter()
    for r in rows:
        for s in (r['skill_signature'] or '').split(','):
            if s: agg[s]+=r['opportunity_count']
    out=[]
    for skill,demand in agg.items():
        cap=_safe_float(current.get(skill,0),0); ds=min(1,demand/20); gap=max(0,ds-cap)
        action='BUILD_EVIDENCE' if gap>.35 else 'REINFORCE' if gap>.15 else 'MAINTAIN'
        c.execute("INSERT INTO skill_gaps(skill,demand_score,current_capability,gap_score,evidence_json,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(skill) DO UPDATE SET demand_score=excluded.demand_score,current_capability=excluded.current_capability,gap_score=excluded.gap_score,evidence_json=excluded.evidence_json,updated_at=excluded.updated_at",(skill,ds,cap,gap,json.dumps({'demand_count':demand}),now()))
        c.execute("INSERT INTO portfolio_recommendations(skill,evidence_count,demand_score,gap_score,action,rationale,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(skill) DO UPDATE SET evidence_count=excluded.evidence_count,demand_score=excluded.demand_score,gap_score=excluded.gap_score,action=excluded.action,rationale=excluded.rationale,updated_at=excluded.updated_at",(skill,0,ds,gap,action,f'Demand={demand}; current capability={cap:.2f}; gap={gap:.2f}.',now()))
        out.append({'skill':skill,'demand_score':ds,'gap_score':gap,'action':action})
    c.commit(); return out


def authorize_action(c, action, target, parameters, evidence_ids, policy_version, actor, ttl_seconds=300):
    ids=sorted({int(x) for x in evidence_ids}) if evidence_ids else []
    if not ids: raise ValueError('AUTH_REQUIRES_EVIDENCE')
    rows=c.execute(f"SELECT id,opportunity_id,confidence,source,url,finding FROM evidence WHERE id IN ({','.join('?' for _ in ids)})", ids).fetchall()
    if len(rows)!=len(ids): raise ValueError('AUTH_EVIDENCE_NOT_FOUND')
    opp_id=parameters.get('opportunity_id') if isinstance(parameters,dict) else None
    if opp_id is not None and any(r['opportunity_id']!=int(opp_id) for r in rows): raise ValueError('AUTH_EVIDENCE_TARGET_MISMATCH')
    if any(float(r['confidence'] or 0) <= 0 or not r['source'] or not r['url'] or not r['finding'] for r in rows): raise ValueError('AUTH_EVIDENCE_INCOMPLETE')
    pd=_sha(parameters); ed=_sha(ids); issued=int(time.time()); exp=issued+max(1,int(ttl_seconds)); nonce=hashlib.sha256(f'{action}|{target}|{pd}|{issued}|{time.time_ns()}'.encode()).hexdigest()[:32]; aid=f'AR-{nonce}'
    c.execute("INSERT INTO action_authorizations(approval_id,action,target,parameters_digest,evidence_digest,policy_version,actor,issued_at,expires_at,nonce) VALUES(?,?,?,?,?,?,?,?,?,?)",(aid,action,target,pd,ed,policy_version,actor,issued,exp,nonce))
    record_decision_trace(c, decision_type='ACTION_AUTHORIZATION', policy_version=policy_version, target_type='ACTION_TARGET', target_id=target, action=action, parameters=parameters, evidence_ids=ids, claims={}, state_snapshot={'authorization_status':'ISSUED'}, ranking_context={}, actor=actor, reason='Explicit authorization bound to target, parameters, evidence and policy', approval_ref=aid, approval_expires_at=exp, approval_nonce=nonce, outcome='AUTHORIZED')
    c.commit(); return aid

def execute_authorized(c, approval_id, action, target, parameters, evidence_ids, executor):
    # Claim the one-time authorization atomically before touching any external system.
    # This closes the TOCTOU race where two workers could both observe ISSUED and execute.
    c.execute('BEGIN IMMEDIATE')
    try:
        row=c.execute('SELECT * FROM action_authorizations WHERE approval_id=?',(approval_id,)).fetchone()
        if not row: raise ValueError('AUTH_NOT_FOUND')
        if row['status']!='ISSUED': raise ValueError('AUTH_ALREADY_USED')
        if int(time.time())>row['expires_at']: raise ValueError('AUTH_EXPIRED')
        if row['action']!=action or row['target']!=target or row['parameters_digest']!=_sha(parameters) or row['evidence_digest']!=_sha(sorted(int(x) for x in evidence_ids)): raise ValueError('AUTH_BINDING_MISMATCH')
        attempt=int(c.execute('SELECT COALESCE(MAX(attempt_no),0)+1 FROM action_attempts WHERE approval_id=?',(approval_id,)).fetchone()[0]); started=now()
        c.execute('INSERT INTO action_attempts(approval_id,attempt_no,started_at,status) VALUES(?,?,?,?)',(approval_id,attempt,started,'STARTED'))
        c.execute("UPDATE action_authorizations SET status='EXECUTING' WHERE approval_id=? AND status='ISSUED'",(approval_id,))
        if c.execute('SELECT changes()').fetchone()[0] != 1: raise ValueError('AUTH_ALREADY_USED')
        c.commit()
    except Exception:
        c.rollback()
        raise
    try:
        result=executor(); digest=_sha(result)
        c.execute("UPDATE action_attempts SET finished_at=?,status='SUCCESS',result_digest=? WHERE approval_id=? AND attempt_no=?",(now(),digest,approval_id,attempt))
        c.execute("UPDATE action_authorizations SET status='USED',used_at=? WHERE approval_id=? AND status='EXECUTING'",(int(time.time()),approval_id))
        record_decision_trace(
            c, decision_type='ACTION_EXECUTION', policy_version=row['policy_version'],
            target_type='ACTION_TARGET', target_id=target, action=action,
            parameters=parameters, evidence_ids=evidence_ids, claims={},
            state_snapshot={'authorization_status':'USED','attempt':attempt,'result_digest':digest},
            ranking_context={}, actor=executor.__class__.__name__ if not callable(executor) else 'authorized_executor',
            reason='Authorized action execution completed', approval_ref=approval_id,
            approval_expires_at=row['expires_at'], approval_nonce=row['nonce'], outcome='EXECUTED'
        )
        c.commit(); return result
    except Exception as exc:
        error=type(exc).__name__+': '+str(exc)
        c.execute("UPDATE action_attempts SET finished_at=?,status='FAILED',error=? WHERE approval_id=? AND attempt_no=?",(now(),error,approval_id,attempt))
        c.execute("UPDATE action_authorizations SET status='FAILED',used_at=? WHERE approval_id=? AND status='EXECUTING'",(int(time.time()),approval_id))
        record_decision_trace(
            c, decision_type='ACTION_EXECUTION', policy_version=row['policy_version'],
            target_type='ACTION_TARGET', target_id=target, action=action,
            parameters=parameters, evidence_ids=evidence_ids, claims={},
            state_snapshot={'authorization_status':'FAILED','attempt':attempt,'error':error},
            ranking_context={}, actor='authorized_executor',
            reason='Authorized action execution failed', approval_ref=approval_id,
            approval_expires_at=row['expires_at'], approval_nonce=row['nonce'], outcome='FAILED'
        )
        c.commit(); raise


def workflow_event(c, workflow_id, opportunity_id, event_type, state, payload=None, attempt=0):
    key=_sha([workflow_id,event_type,state,attempt,payload or {}]); ts=now()
    c.execute("INSERT OR IGNORE INTO workflow_events(workflow_id,opportunity_id,event_type,state,attempt,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?)",(workflow_id,opportunity_id,event_type,state,attempt,key,json.dumps(payload or {},ensure_ascii=False),ts))
    c.execute("INSERT INTO workflow_state(workflow_id,opportunity_id,state,version,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(workflow_id) DO UPDATE SET state=excluded.state,version=workflow_state.version+1,updated_at=excluded.updated_at",(workflow_id,opportunity_id,state,0,ts)); c.commit(); return key


def ingest_market_signals(c, rows):
    for r in rows:
        text=' '.join(str(r.get(k,'')) for k in ('title','description','category','skills'))
        signals=[]
        for term in ('excel','python','automation','api','data cleaning','scraping','dashboard','security','android'):
            if term in text.lower(): signals.append(term)
        for s in signals:
            key=s; ts=now(); c.execute("INSERT INTO market_signals(signal_type,signal_key,value_json,confidence,first_seen,last_seen) VALUES(?,?,?,?,?,?) ON CONFLICT(signal_type,signal_key) DO UPDATE SET value_json=excluded.value_json,confidence=excluded.confidence,last_seen=excluded.last_seen",('DEMAND_SKILL',key,json.dumps({'matched':s}),.65,ts,ts))
    c.commit()


def run_goal_completion(c, *, profile=None, rows=None):
    ensure_schema(c)
    rows=[dict(r) for r in (rows if rows is not None else c.execute('SELECT * FROM opportunities').fetchall())]
    for r in rows:
        party_from_opportunity(c,r,r.get('id'))
        calculate_ttm(c,r['id']) if r.get('id') else None
    build_demand_clusters(c,rows); ingest_market_signals(c,rows); refresh_revenue_intelligence(c); product_engine(c); skill_portfolio_engine(c,profile)
    return decision_center(c)

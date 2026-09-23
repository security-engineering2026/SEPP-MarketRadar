from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from datetime import datetime, timezone
from .analysis import classify, payment_hint, ttm, score, opportunity_type
from .policy import eligibility, POLICY_VERSION
from .quality import canonical_url, item_quality
from .country_policy import infer_country
from .payment import detect_payment, detect_kyc, classify_payment_evidence
from .opportunity_intelligence import analyze_need
from .opportunity_ranker import rank_opportunity
from .learning import load_profile
from .opportunity_signals import extract_signals
from .outcome_learning import estimate_acceptance_prior
from .capability_registry import match_task
from .source_policy import BLACKLIST_LANE, classify_opportunity_blacklist

@dataclass(frozen=True, slots=True)
class AcquisitionAttestation:
    source: str
    url: str
    sha256: str
    status: int

class Pipeline:
    def __init__(self, c, settings=None):
        self.c = c; self.settings = settings or {}
        self.profile = self.settings.get("profile") or load_profile(c, self.settings)

    def ingest(self, source, item, acquisition_attested=None):
        attested = False
        if acquisition_attested is not None:
            if not isinstance(acquisition_attested, AcquisitionAttestation):
                raise ValueError('INVALID_ACQUISITION_ATTESTATION')
            try:
                att_url = canonical_url(acquisition_attested.url)
            except ValueError as exc:
                raise ValueError('INVALID_ACQUISITION_ATTESTATION') from exc
            valid_hash = isinstance(acquisition_attested.sha256, str) and len(acquisition_attested.sha256) == 64 and all(c in '0123456789abcdef' for c in acquisition_attested.sha256.lower())
            rows = self.c.execute("SELECT url,payload,http_status FROM raw_observations WHERE source=? AND payload_sha256=? AND observation_kind='source_response'", (source.get('name'), acquisition_attested.sha256.lower())).fetchall()
            matched = False
            for candidate in rows:
                if candidate['http_status'] != 200:
                    continue
                payload = candidate['payload']
                if not isinstance(payload, (bytes, bytearray)):
                    payload = str(payload).encode('utf-8')
                if hashlib.sha256(bytes(payload)).hexdigest() != acquisition_attested.sha256.lower():
                    continue
                try:
                    matched = candidate['url'] == att_url or canonical_url(candidate['url']) == att_url
                except ValueError:
                    matched = False
                if matched:
                    break
            attested = acquisition_attested.source == source.get('name') and acquisition_attested.status == 200 and valid_hash and matched
            if not attested:
                raise ValueError('INVALID_ACQUISITION_ATTESTATION')
        if not isinstance(item, dict): raise ValueError('INVALID_OPPORTUNITY')
        url = canonical_url(item.get('url'))
        title = ' '.join(str(item.get('title','')).split()).strip()
        desc = ' '.join(str(item.get('description','')).split()).strip()
        if not title or len(title) > 240: raise ValueError('INVALID_OPPORTUNITY_TITLE')
        if len(desc) > 10000: raise ValueError('INVALID_OPPORTUNITY_DESCRIPTION')
        now = datetime.now(timezone.utc).isoformat()
        normalized = dict(item); normalized['url']=url; normalized['title']=title; normalized['description']=desc
        text=title+' '+desc; b,cur=__import__('marketradar.analysis',fromlist=['budget']).budget(text)
        payment=detect_payment(text, normalized.get('currency'))
        pay=payment['asset'] or payment_hint(text)
        if pay == 'UNKNOWN' and normalized.get('currency'):
            pay = payment_hint(str(normalized.get('currency')))
        normalized['payment_network']=payment.get('network')
        normalized['kyc_requirement']=detect_kyc(text)
        ev=normalized.get('evidence',[])
        if not isinstance(ev,list): raise ValueError('INVALID_EVIDENCE')
        clean_ev=[]
        for e in ev[:20]:
            if not isinstance(e,dict): continue
            try: conf=max(0.0,min(1.0,float(e.get('confidence',0))))
            except (TypeError,ValueError): conf=0.0
            eu=canonical_url(e.get('url',url))
            
            # Source-declared provenance is untrusted metadata. The acquisition
            # layer owns the root of provenance; callers without an attested
            # acquisition get a conservative confidence ceiling.
            trusted_conf = conf if attested else min(conf, 0.75)
            clean_ev.append({'kind':str(e.get('kind','listing'))[:64],'url':eu,'finding':str(e.get('finding',''))[:2000],'confidence':trusted_conf,'provenance_root':source['name'][:128]})
        conf=max([e['confidence'] for e in clean_ev] or [0.0]); quality=item_quality(normalized,conf)
        payment_evidence_state=classify_payment_evidence(payment, clean_ev, payment_verified=bool(normalized.get('payment_verified')), verification_evidence=bool(normalized.get('payment_verification_evidence')))
        need=analyze_need(normalized)
        capability_match=match_task(need)
        if capability_match['status']=='FULL_MATCH': automation_status='AUTO_AVAILABLE'
        elif capability_match['status'] in {'PARTIAL_MATCH','PROVIDER_DISABLED'}: automation_status='ENGINE_NOT_READY'
        elif capability_match['status']=='REGISTERED_NO_PROVIDER': automation_status='MANUAL_OR_BUILD'
        else: automation_status='MANUAL_OR_UNKNOWN'
        provider_ids=sorted({pid for m in capability_match.get('matches',[]) for pid in m.get('connected_provider_ids',[])})
        task_type=need.get('task_type','')
        if task_type in {'python_automation','python_debugging'}: recommendation_domain='python'
        elif task_type=='android_bug_bounty': recommendation_domain='android_bug_bounty'
        elif task_type=='web_bug_bounty': recommendation_domain='web_bug_bounty'
        elif task_type in {'android_development'}: recommendation_domain='android'
        elif task_type in {'general_software_task','python_automation','api_integration','business_automation','data_pipeline'}: recommendation_domain='python'
        elif need.get('work_domain') in {'document_processing','language_services','data_processing','presentation','media_processing'}: recommendation_domain='services'
        else: recommendation_domain='services'
        country=infer_country(normalized)
        settings = getattr(self, 'settings', {})
        elig,reasons=eligibility(source,bool(clean_ev),normalized,settings)
        blocked_hits=[]
        try:
            blacklisted, blocked_hits=classify_opportunity_blacklist(normalized, source, settings.get('execution_blacklist_countries', ['Israel']))
        except Exception:
            blacklisted=False
        if source.get('source_lane')==BLACKLIST_LANE and not blacklisted:
            blacklisted=True; blocked_hits=['SOURCE_BLACKLIST_ARCHIVE']
        if blacklisted:
            elig='BLOCK'
            reasons=list(reasons)+['BLACKLIST_ARCHIVE:'+','.join(blocked_hits or ['POLICY'])]
        raw_budget=normalized.get('budget')
        if b is None and raw_budget is not None:
            try: raw_budget=float(raw_budget)
            except (TypeError,ValueError): raw_budget=None
        if raw_budget is not None and raw_budget < 0: raw_budget=None
        row={'source':source['name'],'title':title,'url':url,'description':desc,'category':classify(text),'budget':b if b is not None else raw_budget,'currency':cur or normalized.get('currency'),'payment':pay,'evidence_confidence':conf,'quality_score':quality,'eligibility':elig,'state':'DISCOVERED','rejection_reason':None if elig == 'EXECUTE' else '; '.join(reasons),'first_seen':now,'last_seen':now,'country':country,'region':normalized.get('region'),'iran_access':normalized.get('iran_access','UNKNOWN'),'blacklist_reason':('; '.join(reasons) if blacklisted else None),'need_summary':need['purpose'],'tool_recommendation':need['tool_name'],'automation_mode':normalized.get('automation_mode','MANUAL'),'work_domain':need['work_domain'],'task_type':need['task_type'],'operations_json':json.dumps(need['operations'],ensure_ascii=False),'input_formats_json':json.dumps(need['input_formats'],ensure_ascii=False),'output_formats_json':json.dumps(need['output_formats'],ensure_ascii=False),'requirements_json':json.dumps(need['requirements'],ensure_ascii=False),'qa_requirements_json':json.dumps(need['qa_requirements'],ensure_ascii=False),'manual_execution_possible':1,'automation_status':automation_status,'automation_provider_ids_json':json.dumps(provider_ids,ensure_ascii=False),'suitability_status':'UNASSESSED','recommendation_domain':recommendation_domain,'payment_network':payment.get('network'),'payment_verified':int(bool(payment.get('verified'))),'kyc_requirement':normalized.get('kyc_requirement','UNKNOWN'),'opportunity_type':opportunity_type(normalized),'market_signal_confidence':0.65,'ttm_confidence':0.35 }
        row['time_to_money']=ttm(row); row['score']=score(row)
        signals=extract_signals(normalized)
        row.update({k:v for k,v in signals.items() if k not in {'proposal_count'}})
        row['proposal_count']=signals.get('proposal_count')
        row['acceptance_probability']=estimate_acceptance_prior(self.c, source['name'], row['category'])
        row['expected_value']=float(row.get('budget') or 0)*float(row['acceptance_probability'] or 0.5)
        ranking=rank_opportunity({**row,'_signals':signals}, self.profile)
        ranking['skill_gap']=ranking.get('skill_gap',[])
        ranking['application_ready']=bool(row['eligibility']=='EXECUTE' and ranking['application_speed_score']>=0.70)
        ranking['application_reason']='policy+evidence+application path ready' if ranking['application_ready'] else 'requires review, policy, or manual path'
        row['skill_gap_json']=json.dumps(ranking.get('skill_gap',[]),ensure_ascii=False)
        row.update(ranking)
        existing=self.c.execute('SELECT id,quality_score,state FROM opportunities WHERE url=?',(url,)).fetchone()
        if existing is None:
            self.c.execute('''INSERT INTO opportunities(source,title,url,description,category,budget,currency,payment,evidence_confidence,quality_score,eligibility,score,time_to_money,state,rejection_reason,first_seen,last_seen,country,region,iran_access,blacklist_reason,need_summary,tool_recommendation,automation_mode,payment_network,payment_verified,kyc_requirement,skill_fit,difficulty_score,difficulty_fit,learning_value,competition_score,application_speed_score,freshness_score,recommended_level,track,application_path,skill_gap_json,rank_score,application_ready,application_reason)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', tuple(row.get(k) for k in ['source','title','url','description','category','budget','currency','payment','evidence_confidence','quality_score','eligibility','score','time_to_money','state','rejection_reason','first_seen','last_seen','country','region','iran_access','blacklist_reason','need_summary','tool_recommendation','automation_mode','payment_network','payment_verified','kyc_requirement','skill_fit','difficulty_score','difficulty_fit','learning_value','competition_score','application_speed_score','freshness_score','recommended_level','track','application_path','skill_gap_json','rank_score','application_ready','application_reason']))
        elif row['quality_score'] > float(existing['quality_score'] or 0):
            # Once execution has started, the actionable snapshot is frozen.
            # New observations remain evidence/provenance, but cannot rewrite
            # the title, policy result, score, or other fields used for action.
            if existing['state'] == 'DISCOVERED':
                self.c.execute('''UPDATE opportunities SET source=?,title=?,description=?,category=?,budget=?,currency=?,payment=?,evidence_confidence=?,quality_score=?,eligibility=?,score=?,time_to_money=?,rejection_reason=?,last_seen=?,country=?,region=?,iran_access=?,blacklist_reason=?,need_summary=?,tool_recommendation=?,automation_mode=?,payment_network=?,payment_verified=?,kyc_requirement=?,skill_fit=?,difficulty_score=?,difficulty_fit=?,learning_value=?,competition_score=?,application_speed_score=?,freshness_score=?,recommended_level=?,track=?,application_path=?,skill_gap_json=?,rank_score=?,application_ready=?,application_reason=? WHERE id=?''',
                    tuple(row[k] for k in ['source','title','description','category','budget','currency','payment','evidence_confidence','quality_score','eligibility','score','time_to_money','rejection_reason','last_seen','country','region','iran_access','blacklist_reason','need_summary','tool_recommendation','automation_mode','payment_network','payment_verified','kyc_requirement','skill_fit','difficulty_score','difficulty_fit','learning_value','competition_score','application_speed_score','freshness_score','recommended_level','track','application_path','skill_gap_json','rank_score','application_ready','application_reason']) + (existing['id'],))
            else:
                self.c.execute('UPDATE opportunities SET last_seen=? WHERE id=?',(row['last_seen'],existing['id']))
        else:
            self.c.execute('UPDATE opportunities SET last_seen=? WHERE id=?',(row['last_seen'],existing['id']))
        oid=self.c.execute('SELECT id FROM opportunities WHERE url=?',(url,)).fetchone()[0]
        self.c.execute('''UPDATE opportunities SET work_domain=?,task_type=?,operations_json=?,input_formats_json=?,output_formats_json=?,requirements_json=?,qa_requirements_json=?,manual_execution_possible=?,automation_status=?,automation_provider_ids_json=?,suitability_status=?,recommendation_domain=?,blacklist_reason=? WHERE id=? AND state='DISCOVERED' ''', (row['work_domain'],row['task_type'],row['operations_json'],row['input_formats_json'],row['output_formats_json'],row['requirements_json'],row['qa_requirements_json'],row['manual_execution_possible'],row['automation_status'],row['automation_provider_ids_json'],row['suitability_status'],row['recommendation_domain'],('; '.join(reasons) if 'BLACKLIST_ARCHIVE:' in '; '.join(reasons) else row.get('blacklist_reason')),oid))
        if blocked_hits:
            self.c.execute("INSERT OR IGNORE INTO opportunity_blacklist_archive(opportunity_id,reason,observed_at,evidence_json) VALUES(?,?,?,?)", (oid,'EXPLICIT_BLACKLIST:'+','.join(blocked_hits),now,json.dumps({'source':source.get('name'),'country':country,'url':url},ensure_ascii=False)))
        self.c.execute('UPDATE opportunities SET opportunity_type=? WHERE id=?',(row.get('opportunity_type','OPPORTUNITY'),oid))
        self.c.execute('''UPDATE opportunities SET deadline_at=?,deadline_confidence=?,proposal_count=?,proposal_count_confidence=?,client_reputation_score=?,client_reputation_confidence=?,acceptance_probability=?,competition_pressure=?,deadline_urgency=?,expected_value=?,revenue_score=? WHERE id=?''', (row.get('deadline_at'),row.get('deadline_confidence',0),row.get('proposal_count'),row.get('proposal_count_confidence',0),row.get('client_reputation_score',0.45),row.get('client_reputation_confidence',0),row.get('acceptance_probability',0.5),row.get('competition_pressure',0.45),row.get('deadline_urgency',0.45),row.get('expected_value',0),row.get('revenue_score',0),oid))
        profile_level=int(self.profile.get('learning',{}).get('level',3)) if isinstance(self.profile.get('learning'),dict) else int(self.profile.get('level',3) or 3)
        self.c.execute('''INSERT INTO opportunity_rank_history(opportunity_id,observed_at,rank_score,skill_fit,difficulty_score,difficulty_fit,learning_value,competition_score,application_speed_score,freshness_score,recommended_level,track,profile_level,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (oid,now,row['rank_score'],row['skill_fit'],row['difficulty_score'],row['difficulty_fit'],row['learning_value'],row['competition_score'],row['application_speed_score'],row['freshness_score'],row['recommended_level'],row['track'],profile_level,row['application_reason']))
        if row['application_ready']:
            self.c.execute('''INSERT INTO application_queue(opportunity_id,priority,status,ready_at,application_path,authorization_required,reason,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(opportunity_id) DO UPDATE SET priority=excluded.priority,status=CASE WHEN application_queue.status IN ('SUBMITTED','CANCELLED') THEN application_queue.status ELSE excluded.status END,ready_at=excluded.ready_at,application_path=excluded.application_path,reason=excluded.reason,updated_at=excluded.updated_at''', (oid,row['rank_score'],'READY',now,row['application_path'],1,row['application_reason'],now,now))
        self.c.execute('''INSERT INTO opportunity_sources(opportunity_id,source,first_seen,last_seen) VALUES(?,?,?,?)
            ON CONFLICT(opportunity_id,source) DO UPDATE SET last_seen=excluded.last_seen''',(oid,source['name'],now,now))
        # Feed the canonical observation into the goal-completion fabric without allowing it to mutate the actionable snapshot.
        try:
            from .goal_completion import party_from_opportunity, calculate_ttm
            eid = party_from_opportunity(self.c, {**normalized, **row}, oid)
            if eid:
                self.c.execute('UPDATE opportunities SET party_entity_id=? WHERE id=?',(eid,oid))
            pred=calculate_ttm(self.c,oid)
            self.c.execute('UPDATE opportunities SET ttm_confidence=? WHERE id=?',(pred.get('confidence',0),oid))
        except Exception:
            pass
        evidence_ids=[]
        observation_id=None
        if attested:
            observation_row=self.c.execute(
                "SELECT id FROM raw_observations WHERE source=? AND payload_sha256=? AND observation_kind='source_response' AND http_status=200 ORDER BY id DESC LIMIT 1",
                (source.get('name'), acquisition_attested.sha256.lower()),
            ).fetchone()
            if observation_row is not None:
                observation_id=int(observation_row['id'])
        for e in clean_ev:
            eh=hashlib.sha256(json.dumps([oid,e['kind'],source['name'],e['url'],e['finding'],e['confidence'],e['provenance_root']],sort_keys=True).encode()).hexdigest()
            self.c.execute('INSERT OR IGNORE INTO evidence(opportunity_id,observation_id,kind,source,url,finding,confidence,provenance_root,observed_at,evidence_hash) VALUES(?,?,?,?,?,?,?,?,?,?)',(oid,observation_id,e['kind'],source['name'],e['url'],e['finding'],e['confidence'],e['provenance_root'],now,eh))
            evidence_row=self.c.execute('SELECT id FROM evidence WHERE evidence_hash=?',(eh,)).fetchone()
            if evidence_row:
                evidence_ids.append(int(evidence_row['id']))
        # Consequential normalized facts become explicit claims with claim-level provenance.
        claim_specs=[
            ('eligibility',elig,max(0.0,min(1.0,conf))),
            ('payment',pay,max(0.0,min(1.0,conf))),
            ('payment_evidence_state',payment_evidence_state,max(0.0,min(1.0,conf))),
            ('kyc_requirement',normalized.get('kyc_requirement','UNKNOWN'),max(0.0,min(1.0,conf))),
            ('iran_access',normalized.get('iran_access','UNKNOWN'),max(0.0,min(1.0,conf))),
        ]
        if row.get('budget') is not None:
            claim_specs.append(('budget',f"{row.get('budget')} {row.get('currency') or ''}".strip(),max(0.0,min(1.0,conf))))
        for claim_type, claim_value, claim_confidence in claim_specs:
            claim_value = str(claim_value)
            prior = self.c.execute(
                'SELECT id,claim_value,confidence,observed_at FROM claims WHERE opportunity_id=? AND claim_type=? ORDER BY observed_at DESC,id DESC LIMIT 1',
                (oid, claim_type),
            ).fetchone()
            self.c.execute(
                'INSERT OR IGNORE INTO claims(entity_type,entity_id,opportunity_id,claim_type,claim_value,confidence,observed_at,expires_at,policy_version) VALUES(?,?,?,?,?,?,?,?,?)',
                ('Opportunity',oid,oid,claim_type,claim_value,claim_confidence,now,None,POLICY_VERSION if claim_type=='eligibility' else None)
            )
            claim_row=self.c.execute('SELECT id FROM claims WHERE opportunity_id=? AND claim_type=? AND claim_value=?',(oid,claim_type,claim_value)).fetchone()
            if claim_row:
                new_claim_id=int(claim_row['id'])
                for evidence_id in evidence_ids:
                    self.c.execute('INSERT OR IGNORE INTO claim_evidence(claim_id,evidence_id) VALUES(?,?)',(new_claim_id,evidence_id))
                # A changed claim is a first-class temporal event. We never silently
                # overwrite the previous value: both claims remain immutable and the
                # relation is recorded for contradiction/supersession analysis.
                if prior and str(prior['claim_value']) != claim_value and int(prior['id']) != new_claim_id:
                    details=json.dumps({'previous_value':str(prior['claim_value']),'new_value':claim_value,'previous_confidence':float(prior['confidence'] or 0),'new_confidence':claim_confidence},ensure_ascii=False,sort_keys=True)
                    self.c.execute(
                        'INSERT OR IGNORE INTO claim_conflicts(opportunity_id,claim_type,previous_claim_id,new_claim_id,relation,detected_at,details_json) VALUES(?,?,?,?,?,?,?)',
                        (oid,claim_type,int(prior['id']),new_claim_id,'CONTRADICTS',now,details),
                    )
        return row

    def actions(self):
        return self.c.execute("SELECT * FROM opportunities WHERE eligibility IN ('EXECUTE','REVIEW') AND state='DISCOVERED' AND COALESCE(blacklist_reason,'')='' AND COALESCE(automation_status,'') <> 'BLACKLISTED' ORDER BY COALESCE(rank_score,score) DESC,time_to_money DESC LIMIT 7").fetchall()
    def daily_center(self):
        rows=[dict(r) for r in self.actions()]; return {'top7':rows,'do_now':[r for r in rows if r['eligibility']=='EXECUTE'][:3],'learn_apply':[r for r in rows if r['eligibility']=='REVIEW'][:3]}

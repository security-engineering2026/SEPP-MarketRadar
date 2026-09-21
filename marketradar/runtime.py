import json
from .paths import data_root
from datetime import datetime, timezone
from .federation import Federation
from .pipeline import Pipeline, AcquisitionAttestation
from .application import transition, record_revenue
from .android_bridge import AndroidBridge
from .security import ApprovalBroker
from .db import audit, load_dynamic_source_records
from .opportunity_intelligence import analyze_need
from .resume import tailored_resume
from .proposal import generate_proposal
from .application_connectors import ApplicationConnector, GuidedBrowserConnector
from .application_adapters import DEFAULT_ADAPTERS
from .browser_recovery import BrowserRecovery
from .outcome_learning import record_outcome, update_learning_snapshot, learning_summary
from .policy import eligibility
from .market_intelligence import duplicate_groups, market_snapshot, competition_snapshot, distribution_targets
from .learning import load_profile, save_profile, learning_settings
from .goal_completion import run_goal_completion, decision_center, authorize_action, execute_authorized, record_financial, refresh_revenue_intelligence, product_engine, skill_portfolio_engine, workflow_event
from .security_fabric import security_scan
from .operational_completion import ProviderRegistry, submit_with_approval, record_delivery, record_payment, operational_gate
from .application import verify_payment
from .operations import record_contract, schedule_followup, check_payment, project_report, generate_final_report, operation_tick, operation_dashboard, source_application_gate
from .economic_loop import register_tracking, record_status_observation, poll_due_tracking, add_milestone, complete_milestone, add_communication, record_payment_check, register_payment_poll, poll_due_payment_verification
from .finance import add_account, route_source_account, record_entry, record_payment_to_account, period_report, export_report
from .notifications import unread as unread_notifications, mark_read as mark_notification_read
from .email_service import add_account as add_email_account, create_draft as create_email_draft, approve as approve_email_draft, send as send_email_draft, poll_inbox
from .application_package import build_application_package
import os
from .source_health import persist_health
from .adapter_registry import parse as parse_with_adapter, content_type_ok
from .source_verification import SourceVerificationEngine
from .source_search import WebSearchProvider
from .capability_registry import load_provider_config
from .recommendation_engine import daily_center
from .execution_broker import ExecutionBroker

class MarketRadarRuntime:
    """Executable end-to-end core: Federation -> Application -> Android -> Revenue."""
    def __init__(self, connection, source_records, android_secret, http_timeout=5, settings=None):
        self.c = connection
        self.settings = settings or {}
        self.source_records = {s['name']: dict(s) for s in source_records}
        try:
            for s in load_dynamic_source_records(self.c):
                self.source_records.setdefault(s['name'], dict(s))
        except Exception:
            pass
        # Runtime policy state is authoritative for automatic monitoring. Registry JSON
        # remains the discovery contract; persisted verification can move a source into
        # BLOCKED_IRAN / DEAD / LIVE_CONFIRMED without hand-editing the registry.
        try:
            rows = self.c.execute('SELECT source,source_verification_state,iran_eligibility,kyc_requirement,payment_capabilities,payout_evidence_url,kyc_evidence_url,terms_evidence_url,evidence_confidence,policy_lane,execution_ready FROM source_verification_state').fetchall()
            for row in rows:
                rec = self.source_records.get(row['source'])
                if not rec: continue
                rec.update({
                    'source_verification_state': row['source_verification_state'] or rec.get('source_verification_state'),
                    'iran_eligibility': row['iran_eligibility'] or rec.get('iran_eligibility','UNKNOWN'),
                    'kyc_requirement': row['kyc_requirement'] or rec.get('kyc_requirement','UNKNOWN'),
                    'payment_capabilities': json.loads(row['payment_capabilities'] or '[]'),
                    'payout_evidence_url': row['payout_evidence_url'], 'kyc_evidence_url': row['kyc_evidence_url'], 'terms_evidence_url': row['terms_evidence_url'],
                    'evidence_confidence': row['evidence_confidence'] or 0, 'execution_ready': bool(row['execution_ready']),
                    'policy_lane': row['policy_lane'] or rec.get('policy_lane','REVIEW'),
                })
        except Exception:
            # Fresh/legacy databases may not have the runtime table yet. connect() migrates it.
            pass
        try:
            rows = self.c.execute('SELECT name,source_lane,blacklist_reason,blacklisted_at,project_scan_interval_minutes,intelligence_scan_interval_minutes FROM sources').fetchall()
            for row in rows:
                rec=self.source_records.get(row['name'])
                if rec is None: continue
                rec.update({'source_lane':row['source_lane'] or rec.get('source_lane','REVIEW'),'blacklist_reason':row['blacklist_reason'],'blacklisted_at':row['blacklisted_at'],'project_scan_interval_minutes':row['project_scan_interval_minutes'] or 60,'intelligence_scan_interval_minutes':row['intelligence_scan_interval_minutes'] or 720})
        except Exception:
            pass
        try:
            from .paths import app_root
            load_provider_config(app_root() / 'config' / 'capability_providers.json')
        except Exception:
            pass
        all_sources = [self._source_object(s) for s in self.source_records.values()]
        self.federation = Federation([s for s in all_sources if s.status == 'active'], timeout=http_timeout)
        self.verifier = Federation(all_sources, timeout=http_timeout)
        self.settings = dict(self.settings)
        self.settings.setdefault('profile', load_profile(connection, self.settings))
        self.pipeline = Pipeline(connection, settings=self.settings)
        self.android = AndroidBridge(android_secret or os.environ.get('MARKETRADAR_ANDROID_SECRET'), connection)
        self.approvals = ApprovalBroker(connection)
        provider_path = None
        try:
            from .paths import app_root
            provider_path = app_root() / 'config' / 'application_providers.json'
        except Exception:
            provider_path = None
        self.providers = ProviderRegistry(provider_path)
        self.execution_broker = ExecutionBroker(self.c)
        # Goal-completion intelligence fabric: identity/party, trust, demand, TTM, finance, product and durable workflow.
        try:
            run_goal_completion(self.c, profile=self.settings.get("profile"))
            security_scan(self.c)
        except Exception as exc:
            audit(self.c, "goal_completion_bootstrap_failed", "runtime", "startup", {"error": type(exc).__name__ + ": " + str(exc)})
            self.c.commit()

    @staticmethod
    def _source_object(s):
        from .federation import Source
        import re
        import os
        url=s['base_url']
        def substitute(match):
            value=os.environ.get(match.group(1))
            return value if value else match.group(0)
        if '${' in url:
            url=re.sub(r'\$\{([A-Z0-9_]+)\}', substitute, url)
        headers=dict(s.get('headers') or {})
        env_name=s.get('credential_env')
        if env_name:
            token=os.environ.get(env_name)
            if token: headers.setdefault('Authorization','Bearer '+token)
        return Source(
            s['name'], url, s.get('adapter', 'json'), s.get('status', 'candidate'),
            tuple(s.get('allow_hosts', [])), s.get('access_scope', 'public'), tuple(headers.items()), s.get('max_bytes')
        )

    def refresh_intelligence(self):
        return run_goal_completion(self.c, profile=self.settings.get("profile"))

    def daily_center(self):
        return daily_center(self.c, self.settings.get('profile'))


    def finance_add_account(self, **kwargs): return add_account(self.c, **kwargs)
    def finance_route_source(self, source, account_id, reason=None): return route_source_account(self.c, source, account_id, reason)
    def finance_record_entry(self, **kwargs): return record_entry(self.c, **kwargs)
    def finance_record_payment_to_account(self, **kwargs): return record_payment_to_account(self.c, **kwargs)
    def finance_period_report(self, period_type='monthly', out_dir=None):
        report=period_report(self.c,period_type)
        return {'report':report,'exports':export_report(self.c,report,out_dir or (data_root()/'reports'/'finance'))}
    def notifications(self, limit=100): return [dict(x) for x in unread_notifications(self.c,limit)]
    def mark_notification_read(self, notification_id): return mark_notification_read(self.c,notification_id)
    def email_add_account(self, **kwargs): return add_email_account(self.c, **kwargs)
    def email_create_draft(self, **kwargs): return create_email_draft(self.c, **kwargs)
    def email_approve(self, draft_id): return approve_email_draft(self.c,draft_id)
    def email_send(self, draft_id): return send_email_draft(self.c,draft_id)
    def email_poll(self, account_id, limit=20): return poll_inbox(self.c,account_id,limit)
    def application_package(self, opportunity_id, profile=None, language=None, target_amount=None, target_currency=None):
        row=self.c.execute('SELECT * FROM opportunities WHERE id=?',(opportunity_id,)).fetchone()
        if not row: raise ValueError('OPPORTUNITY_NOT_FOUND')
        return build_application_package(profile or self.settings.get('profile') or {},dict(row),language,target_amount,target_currency)

    def save_profile(self, profile):
        result = save_profile(self.c, profile)
        self.settings['profile'] = profile
        return result

    def decision_center(self):
        return decision_center(self.c)

    def authorize_action(self, action, target, parameters, evidence_ids, policy_version, actor, ttl_seconds=300):
        return authorize_action(self.c, action, target, parameters, evidence_ids, policy_version, actor, ttl_seconds)

    def execute_authorized(self, approval_id, action, target, parameters, evidence_ids, executor):
        return execute_authorized(self.c, approval_id, action, target, parameters, evidence_ids, executor)

    def record_financial_observation(self, opportunity_id, gross, currency, **kwargs):
        result = record_financial(self.c, opportunity_id, gross, currency, **kwargs)
        refresh_revenue_intelligence(self.c)
        return result

    def product_recommendations(self):
        return product_engine(self.c)

    def skill_portfolio_recommendations(self, profile=None):
        return skill_portfolio_engine(self.c, profile or self.settings.get("profile"))

    def workflow_event(self, workflow_id, opportunity_id, event_type, state, payload=None, attempt=0):
        return workflow_event(self.c, workflow_id, opportunity_id, event_type, state, payload, attempt)

    def federate(self, name, url=None, dry=False, force=False):
        if name not in self.source_records: raise ValueError('SOURCE_NOT_REGISTERED')
        source=self.source_records[name]
        if source.get('status') == 'disabled': raise ValueError('SOURCE_NOT_ACTIVE')
        state = self.c.execute('''SELECT s.verification_state,s.next_retry_at,s.terms_status,sc.runtime_verification_state
                                       FROM sources s LEFT JOIN source_contracts sc ON sc.source=s.name
                                       WHERE s.name=?''',(name,)).fetchone()
        if state:
            if state['verification_state'] == 'blocked' or state['runtime_verification_state'] == 'blocked' or state['terms_status'] == 'blocked':
                raise ValueError('SOURCE_BLOCKED')
            if not force and state['next_retry_at']:
                try:
                    retry_at=datetime.fromisoformat(state['next_retry_at'])
                    if retry_at > datetime.now(timezone.utc): raise ValueError('SOURCE_RETRY_COOLDOWN')
                except ValueError as exc:
                    if str(exc) == 'SOURCE_RETRY_COOLDOWN': raise
        started=datetime.now(timezone.utc).isoformat()
        obs = None
        try:
            obs=self.federation.fetch(name,url)
            adapter=source.get('adapter','json')
            raw_url = obs['url']
            if not dry:
                self.c.execute('INSERT OR IGNORE INTO raw_observations(source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind) VALUES(?,?,?,?,?,?,?,?)',(name,raw_url,started,obs['body'],obs['sha256'],obs['status'],obs.get('content_type'),'source_response'))
                # Preserve the acquired response before parsing/contract validation.
                self.c.commit()
            if not content_type_ok(adapter, obs.get('content_type')):
                raise ValueError('CONTENT_TYPE_MISMATCH')
            items=parse_with_adapter(adapter,obs['body'],obs['url'],self.federation.parse_json)
            if not isinstance(items,list): raise ValueError('ADAPTER_RESULT_INVALID')
            ingested=0
            for item in items:
                item=dict(item)
                item.setdefault('evidence',[{'kind':'listing','url':item['url'],'finding':'federated source observation','confidence':0.90,'provenance_root':name}])
                if not dry:
                    self.pipeline.ingest(source,item,acquisition_attested=AcquisitionAttestation(name, obs['url'], obs['sha256'], obs['status']))
                ingested+=1
            if dry: return {'source':name,'status':'OK','http_status':obs['status'],'observations':ingested,'sha256':obs['sha256'],'dry_run':True}
            result={'source':name,'status':'OK','http_status':obs['status'],'elapsed_ms':obs['elapsed_ms'],'bytes':obs['bytes'],'sha256':obs['sha256'],'attempts':obs['attempts'],'error':None,'parse_ok':True,'parsed_count':ingested,'parse_error':None}
            persist_health(self.c,source,result); self.c.commit()
            return {'source':name,'status':'OK','http_status':obs['status'],'observations':ingested,'sha256':obs['sha256']}
        except Exception as exc:
            self.c.rollback()
            result={'source':name,'status':'ERROR',
                    'http_status': obs.get('status') if obs is not None else getattr(exc,'code',None),
                    'elapsed_ms': obs.get('elapsed_ms') if obs is not None else None,
                    'bytes': obs.get('bytes',0) if obs is not None else 0,
                    'sha256': obs.get('sha256') if obs is not None else None,
                    'attempts': obs.get('attempts',1) if obs is not None else getattr(exc,'attempts',1),
                    'error':type(exc).__name__+': '+str(exc),
                    'parse_ok':False,'parsed_count':0,
                    'parse_error':type(exc).__name__+': '+str(exc) if obs is not None else None}
            try:
                if not dry:
                    persist_health(self.c,source,result)
                    self.c.commit()
            except Exception:
                self.c.rollback()
                if not dry:
                    self.c.execute('INSERT INTO federation_runs(source,started_at,status,http_status,observation_count,error,snapshot_sha256) VALUES(?,?,?,?,?,?,?)',(name,started,'ERROR',getattr(exc,'code',None),0,result['error'],None))
                    self.c.commit()
            raise


    def verify_registry(self, names=None, progress_callback=None, stop_event=None, persist=True):
        """Verify many registered sources concurrently, then persist health serially."""
        requested = list(names) if names is not None else [n for n, s in self.source_records.items()
                                                              if s.get("status") == "active"]
        selected=[]; preflight=[]
        for name in requested:
            source = self.source_records.get(name)
            if source is None:
                preflight.append({'source':name,'status':'ERROR','http_status':None,'elapsed_ms':None,'bytes':0,'sha256':None,'attempts':0,'error':'SOURCE_NOT_REGISTERED','parse_ok':False,'parsed_count':0,'parse_error':None})
                continue
            if source.get('status') == 'disabled':
                preflight.append({'source':name,'status':'ERROR','http_status':None,'elapsed_ms':None,'bytes':0,'sha256':None,'attempts':0,'error':'SOURCE_NOT_ACTIVE','parse_ok':False,'parsed_count':0,'parse_error':None})
                continue
            state = self.c.execute('''SELECT s.verification_state,s.terms_status,sc.runtime_verification_state
                                      FROM sources s LEFT JOIN source_contracts sc ON sc.source=s.name
                                      WHERE s.name=?''',(name,)).fetchone()
            if state and (state['verification_state']=='blocked' or state['runtime_verification_state']=='blocked' or state['terms_status']=='blocked'):
                preflight.append({'source':name,'status':'ERROR','http_status':None,'elapsed_ms':None,'bytes':0,'sha256':None,'attempts':0,'error':'SOURCE_BLOCKED','parse_ok':False,'parsed_count':0,'parse_error':None})
                continue
            selected.append(name)
        def validate(name, obs):
            source = self.source_records[name]
            items = parse_with_adapter(source.get('adapter', 'json'), obs['body'], obs['url'], self.verifier.parse_json)
            return {'parse_ok': content_type_ok(source.get('adapter','json'), obs.get('content_type')) and isinstance(items, list), 'parsed_count': len(items) if isinstance(items, list) else 0, 'content_type_ok': content_type_ok(source.get('adapter','json'), obs.get('content_type'))}
        results = preflight + self.verifier.verify_many(selected, progress_callback=progress_callback, stop_event=stop_event, validation_callback=validate)
        results.sort(key=lambda x:x['source'])
        if progress_callback:
            for result in preflight: progress_callback(result)
        if persist:
            try:
                for result in results:
                    source = self.source_records[result["source"]]
                    persist_health(self.c, source, result)
                self.c.commit()
            except Exception:
                self.c.rollback()
                raise
        return results

    def verify_source_policies(self, names=None, progress_callback=None, stop_event=None, persist=True):
        """Automatically re-check source availability, Iran policy, KYC and payout signals.

        This is deliberately evidence-first: explicit restriction can auto-block a source;
        silence never auto-allows Iran or proves no-KYC.
        """
        engine = SourceVerificationEngine(self.c, list(self.source_records.values()), timeout=self.federation.timeout, search_provider=WebSearchProvider(timeout=self.federation.timeout), policy_search_interval_days=self.settings.get('policy_search_interval_days',7))
        results = engine.verify(names=names, progress_callback=progress_callback, stop_event=stop_event)
        if persist and results:
            engine.persist(results)
        return results

    def source_discovery_candidates(self, limit=100):
        return discovery_candidates(self.source_records.values(), limit=limit)

    def operational_gate(self):
        return operational_gate(self.c, self.providers)

    def submit_application_operational(self, opportunity_id, evidence_ids, proposal=None, actor='human'):
        row = self.c.execute('SELECT * FROM opportunities WHERE id=?', (opportunity_id,)).fetchone()
        if not row: raise ValueError('OPPORTUNITY_NOT_FOUND')
        opp = dict(row)
        if opp.get('eligibility') != 'EXECUTE': raise ValueError('SUBMISSION_NOT_ELIGIBLE')
        if proposal is None: proposal = generate_proposal(self.settings.get('profile', {}), opp)
        provider = self.providers.resolve(opp.get('source'), opp.get('url',''))
        return submit_with_approval(self.c, opp, self.settings.get('profile', {}), proposal, list(evidence_ids), policy_version='v6', actor=actor, provider=provider)

    def record_delivery_operational(self, opportunity_id, artifact_path, checksum=None, evidence_url=None, actor='human'):
        return record_delivery(self.c, opportunity_id, artifact_path, checksum=checksum, evidence_url=evidence_url, actor=actor)

    def record_payment_operational(self, opportunity_id, amount, currency, payment_ref, network=None, txid=None, actor='human'):
        return record_payment(self.c, opportunity_id, amount, currency, payment_ref, network=network, txid=txid, actor=actor)

    def set_lifecycle_state(self, opportunity_id, new_state, actor='human'):
        return transition(self.c, opportunity_id, new_state, actor=actor)

    def record_project_contract(self, opportunity_id, **kwargs):
        return record_contract(self.c, opportunity_id, **kwargs)

    def schedule_followup(self, opportunity_id, scheduled_at, message, channel='MANUAL', subject=None, requires_approval=1):
        return schedule_followup(self.c, opportunity_id, scheduled_at, message, channel, subject, requires_approval)

    def check_payment(self, opportunity_id, status, amount=None, currency=None, evidence_ref=None, notes=None, actor='human'):
        result=check_payment(self.c, opportunity_id, status, amount, currency, evidence_ref, notes, actor)
        if status == 'VERIFIED':
            ref=self.c.execute('SELECT payment_ref FROM revenue WHERE opportunity_id=? ORDER BY received_at DESC LIMIT 1',(opportunity_id,)).fetchone()
            if ref: verify_payment(self.c, opportunity_id, ref['payment_ref'], 'VERIFIED', actor=actor)
        return result

    def operation_dashboard(self):
        return operation_dashboard(self.c)

    def operation_tick(self):
        reminders = operation_tick(self.c)
        tracking = poll_due_tracking(self.c, timeout=self.settings.get("http_timeout", 10))
        payments = poll_due_payment_verification(self.c, timeout=self.settings.get("http_timeout", 10))
        return {"reminders": [dict(x) for x in reminders], "application_tracking": tracking, "payment_verification": payments}

    def register_application_tracking(self, opportunity_id, external_ref=None, status_url=None, mode="MANUAL_EVIDENCE", poll_interval_minutes=30, credential_env=None):
        return register_tracking(self.c, opportunity_id, self.c.execute("SELECT source FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()[0], external_ref, status_url, mode, poll_interval_minutes, credential_env)

    def record_application_status_evidence(self, opportunity_id, raw_status, confidence=0.8, evidence_url=None, evidence_text=None, external_ref=None, actor="human"):
        source=self.c.execute("SELECT source FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()[0]
        return record_status_observation(self.c, opportunity_id, source, raw_status, confidence, evidence_url, evidence_text, external_ref, actor)

    def add_project_milestone(self, opportunity_id, name, due_at=None, notes=None):
        return add_milestone(self.c, opportunity_id, name, due_at, notes)

    def complete_project_milestone(self, milestone_id, evidence_ref=None, notes=None):
        return complete_milestone(self.c, milestone_id, evidence_ref, notes)

    def add_project_communication(self, opportunity_id, channel, direction, subject=None, body=None, external_ref=None, evidence_ref=None, occurred_at=None):
        return add_communication(self.c, opportunity_id, channel, direction, subject, body, external_ref, evidence_ref, occurred_at)

    def register_payment_verification(self, opportunity_id, payment_ref, status_url, poll_interval_minutes=30, credential_env=None):
        return register_payment_poll(self.c, opportunity_id, payment_ref, status_url, poll_interval_minutes, credential_env)

    def record_payment_verification_attempt(self, opportunity_id, payment_ref, method, status, amount=None, currency=None, evidence_ref=None, external_ref=None, details=None):
        result=record_payment_check(self.c, opportunity_id, payment_ref, method, status, amount, currency, evidence_ref, external_ref, details)
        if status == "VERIFIED":
            from .application import verify_payment
            verify_payment(self.c, opportunity_id, payment_ref, "VERIFIED", actor="payment_verification", commit=True)
        return result

    def project_report(self, opportunity_id):
        return project_report(self.c, opportunity_id)

    def generate_final_report(self, opportunity_id):
        return generate_final_report(self.c, opportunity_id, data_root() / 'reports')

    def source_application_gate(self, source, opportunity_id=None):
        return source_application_gate(self.c, source, opportunity_id)

    def market_intelligence(self, limit=5000):
        rows=self.c.execute('SELECT * FROM opportunities ORDER BY last_seen DESC LIMIT ?', (int(limit),)).fetchall()
        return {'market':market_snapshot(rows),'competition':competition_snapshot(rows),'duplicate_groups':duplicate_groups(rows)}

    def distribution_recommendation(self, opportunity_id):
        row=self.c.execute('SELECT * FROM opportunities WHERE id=?',(opportunity_id,)).fetchone()
        if not row: raise ValueError('OPPORTUNITY_NOT_FOUND')
        source_rows=self.c.execute("SELECT name,base_url,source_role,policy_lane,country,iran_status FROM sources WHERE policy_lane IN ('DAILY_PROJECT_SCAN','GLOBAL_DISCOVERY') ORDER BY CASE policy_lane WHEN 'DAILY_PROJECT_SCAN' THEN 0 ELSE 1 END,name").fetchall()
        return distribution_targets(row['category'], [dict(r) for r in source_rows])

    def analyze_opportunity(self, opportunity_id):
        row=self.c.execute("SELECT * FROM opportunities WHERE id=?",(opportunity_id,)).fetchone()
        if not row: raise ValueError('OPPORTUNITY_NOT_FOUND')
        result=analyze_need(dict(row))
        now=datetime.now(timezone.utc).isoformat()
        self.c.execute("INSERT OR REPLACE INTO tool_proposals(opportunity_id,category,tool_name,purpose,complexity,components,build_recommendation,created_at) VALUES(?,?,?,?,?,?,?,?)",(opportunity_id,result['category'],result['tool_name'],result['purpose'],result['complexity'],json.dumps(result['components']),result['build_recommendation'],now))
        if row['state']=='DISCOVERED':
            self.c.execute("UPDATE opportunities SET need_summary=?,tool_recommendation=? WHERE id=?",(result['purpose'],result['tool_name'],opportunity_id))
        self.c.commit(); return result

    def build_resume_and_proposal(self, opportunity_id, profile):
        row=self.c.execute("SELECT * FROM opportunities WHERE id=?",(opportunity_id,)).fetchone()
        if not row: raise ValueError('OPPORTUNITY_NOT_FOUND')
        opp=dict(row)
        return {'resume':tailored_resume(profile,opp),'proposal':generate_proposal(profile,opp)}

    def execution_options(self, opportunity_id):
        return self.execution_broker.available_modes(opportunity_id)

    def open_application(self, opportunity_id):
        queue_row=self.c.execute("SELECT q.opportunity_id,q.application_path,q.priority,o.url,o.title,o.source FROM application_queue q JOIN opportunities o ON o.id=q.opportunity_id WHERE q.opportunity_id=? AND q.status='READY'",(opportunity_id,)).fetchone()
        if not queue_row:
            raise ValueError('APPLICATION_NOT_READY')
        opp=dict(self.c.execute('SELECT * FROM opportunities WHERE id=?',(opportunity_id,)).fetchone())
        adapter=DEFAULT_ADAPTERS.resolve(opp['source'],opp['url'])
        plan=adapter.plan(opp,self.settings.get('profile',{}),generate_proposal(self.settings.get('profile',{}),opp))
        result=BrowserRecovery(self.c).execute(opportunity_id,adapter,plan)
        now=datetime.now(timezone.utc).isoformat()
        self.c.execute("UPDATE application_queue SET status='OPENED',updated_at=? WHERE opportunity_id=? AND status='READY'",(now,opportunity_id))
        audit(self.c,'application_opened_for_review','opportunity',opportunity_id,{'path':queue_row['application_path'],'priority':queue_row['priority'],'adapter':getattr(adapter,'source_key','generic'),'attempts':result['attempts']})
        self.c.commit()
        return {'status':'OPENED_FOR_REVIEW','opportunity_id':opportunity_id,'title':queue_row['title'],'url':queue_row['url'],'priority':queue_row['priority'],'path':queue_row['application_path'],'requires_user_submit':True,'attempts':result['attempts'],'recovered':result['recovered']}

    def open_next_application(self):
        rows=self.c.execute("SELECT q.opportunity_id FROM application_queue q JOIN opportunities o ON o.id=q.opportunity_id WHERE q.status='READY' ORDER BY q.priority DESC,q.ready_at ASC LIMIT 1").fetchone()
        if not rows:
            return {'status':'EMPTY'}
        return self.open_application(rows['opportunity_id'])

    def create_submission_plan(self, opportunity_id, profile, proposal=None):
        row=self.c.execute("SELECT * FROM opportunities WHERE id=?",(opportunity_id,)).fetchone()
        if not row: raise ValueError('OPPORTUNITY_NOT_FOUND')
        if row['eligibility'] not in {'EXECUTE','REVIEW'}: raise ValueError('SUBMISSION_NOT_ELIGIBLE')
        if proposal is None: proposal=generate_proposal(profile,dict(row))
        connector = DEFAULT_ADAPTERS.resolve(row['source'],row['url']) if row['application_path'] in {'FAST_FORM','STANDARD_FORM','EMAIL_REVIEW'} else ApplicationConnector()
        plan=connector.plan(dict(row),profile,proposal)
        now=datetime.now(timezone.utc).isoformat()
        self.c.execute("INSERT OR REPLACE INTO application_plans(opportunity_id,mode,url,fields_json,authorization_required,created_at) VALUES(?,?,?,?,?,?)",(opportunity_id,plan.mode,plan.url,json.dumps(plan.fields,ensure_ascii=False),int(plan.authorization_required),now))
        self.c.commit(); return plan

    def execute_submission_plan(self, opportunity_id, connector, profile, proposal=None):
        row=self.c.execute("SELECT * FROM opportunities WHERE id=?",(opportunity_id,)).fetchone()
        if not row: raise ValueError('OPPORTUNITY_NOT_FOUND')
        source=dict(self.c.execute("SELECT * FROM sources WHERE name=?",(row['source'],)).fetchone() or {})
        source.update(self.source_records.get(row['source'],{}))
        if source.get('execution_capability') not in {'authorized_api','authorized_integration'}:
            raise ValueError('AUTHORIZED_EXECUTION_NOT_CONFIGURED')
        if str(source.get('terms_status','not_reviewed')).lower() not in {'reviewed','allowed','n/a'}:
            raise ValueError('SOURCE_TERMS_NOT_APPROVED')
        if row['eligibility']!='EXECUTE' or row['state']!='DISCOVERED': raise ValueError('SUBMISSION_NOT_ELIGIBLE')
        if proposal is None: proposal=generate_proposal(profile,dict(row))
        plan=connector.plan(dict(row),profile,proposal)
        result=connector.execute(plan)
        audit(self.c,'authorized_submission_executed','opportunity',opportunity_id,{'connector':connector.family,'status':result.get('status') if isinstance(result,dict) else str(result)})
        return result

    def rank_opportunities(self, limit=50):
        rows=self.c.execute("SELECT * FROM opportunities WHERE state='DISCOVERED' ORDER BY COALESCE(rank_score,score) DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def application_queue(self, limit=20):
        rows=self.c.execute('''SELECT q.*,o.title,o.url,o.source,o.eligibility,o.rank_score,o.track,o.application_path FROM application_queue q JOIN opportunities o ON o.id=q.opportunity_id WHERE q.status='READY' ORDER BY q.priority DESC,q.ready_at ASC LIMIT ?''',(int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def set_learning_profile(self, profile):
        save_profile(self.c, profile)
        self.settings['profile']=profile
        self.pipeline.profile=profile
        return learning_settings(profile)

    def issue_submission_approval(self, opportunity_id, policy_version='v1', ttl=300):
        row=self.c.execute('SELECT * FROM opportunities WHERE id=?',(opportunity_id,)).fetchone()
        if not row or row['state']!='DISCOVERED': raise ValueError('SUBMISSION_NOT_ELIGIBLE')
        source=dict(self.c.execute('SELECT * FROM sources WHERE name=?',(row['source'],)).fetchone() or {})
        source.update(self.source_records.get(row['source'],{}))
        has_policy=any(source.get(k) is not None for k in ('iran_status','kyc_status','payment_status','terms_status'))
        state,reasons=eligibility(source, bool(self.c.execute('SELECT 1 FROM evidence WHERE opportunity_id=? LIMIT 1',(opportunity_id,)).fetchone()), dict(row), self.settings) if has_policy else (row['eligibility'], ['legacy opportunity policy snapshot'])
        if state!='EXECUTE': raise ValueError('SUBMISSION_POLICY_'+state)
        if row['eligibility']!='EXECUTE': raise ValueError('SUBMISSION_NOT_ELIGIBLE')
        evidence=[dict(r) for r in self.c.execute('SELECT kind,source,url,finding,confidence,provenance_root FROM evidence WHERE opportunity_id=? ORDER BY id',(opportunity_id,)).fetchall()]
        parameters={'opportunity_id':row['id'],'title':row['title'],'url':row['url'],'score':row['score']}
        return self.approvals.issue('SUBMIT',str(opportunity_id),parameters,evidence,policy_version,int(datetime.now(timezone.utc).timestamp()),ttl)

    def approve_and_submit(self, opportunity_id, approval, actor='operator', policy_version='v1'):
        row=self.c.execute('SELECT * FROM opportunities WHERE id=?',(opportunity_id,)).fetchone()
        if not row:
            raise ValueError('OPPORTUNITY_NOT_FOUND')
        if row['state'] != 'DISCOVERED':
            raise ValueError('SUBMISSION_NOT_ELIGIBLE')
        source=dict(self.c.execute('SELECT * FROM sources WHERE name=?',(row['source'],)).fetchone() or {})
        source.update(self.source_records.get(row['source'],{}))
        has_policy=any(source.get(k) is not None for k in ('iran_status','kyc_status','payment_status','terms_status'))
        state,reasons=eligibility(source, bool(self.c.execute('SELECT 1 FROM evidence WHERE opportunity_id=? LIMIT 1',(opportunity_id,)).fetchone()), dict(row), self.settings) if has_policy else (row['eligibility'], ['legacy opportunity policy snapshot'])
        if state!='EXECUTE' or row['eligibility']!='EXECUTE':
            raise ValueError('SUBMISSION_POLICY_'+state)
        gate = self.source_application_gate(row['source'], opportunity_id)
        if not gate.get('allowed'):
            raise ValueError('SOURCE_APPLICATION_'+str(gate.get('reason')))
        evidence=[dict(r) for r in self.c.execute('SELECT kind,source,url,finding,confidence,provenance_root FROM evidence WHERE opportunity_id=? ORDER BY id',(opportunity_id,)).fetchall()]
        parameters={'opportunity_id':row['id'],'title':row['title'],'url':row['url'],'score':row['score']}
        now=int(datetime.now(timezone.utc).timestamp())
        ok,reason=self.approvals.authorize(approval,'SUBMIT',str(opportunity_id),parameters,evidence,policy_version,now,commit=False)
        if not ok:
            raise ValueError('APPROVAL_'+reason)
        try:
            for state in ('ELIGIBILITY_CHECK', 'RECOMMENDED', 'APPROVAL_PENDING', 'SUBMITTED'):
                transition(self.c, opportunity_id, state, actor, commit=False)
            payload={'opportunity_id':row['id'],'title':row['title'],'url':row['url'],'score':row['score'],'eligibility':row['eligibility']}
            if self.android.enabled:
                message=self.android.envelope('APPLICATION_SUBMITTED',payload)
                audit(self.c,'android_message_issued','opportunity',opportunity_id,{'kind':message['kind']})
            else:
                message={'kind':'APPLICATION_SUBMITTED', **payload}
                audit(self.c,'application_submitted','opportunity',opportunity_id,{'actor':actor,'policy_version':policy_version})
            self.c.execute("UPDATE application_queue SET status='SUBMITTED',updated_at=? WHERE opportunity_id=?", (datetime.now(timezone.utc).isoformat(), opportunity_id))
            self.c.commit()
            return message
        except Exception:
            self.c.rollback()
            raise

    def record_outcome(self, opportunity_id, outcome, reason=None, amount=None, currency=None, notes=None):
        row=self.c.execute('SELECT state FROM opportunities WHERE id=?',(opportunity_id,)).fetchone()
        if not row: raise ValueError('OPPORTUNITY_NOT_FOUND')
        target=str(outcome).upper()
        if target != row['state']:
            transition(self.c,opportunity_id,target,'outcome_learning',commit=False)
        result=record_outcome(self.c,opportunity_id,target,reason,amount,currency,notes)
        self.c.commit()
        return result

    def outcome_learning(self):
        return learning_summary(self.c)

    def record_payment(self, opportunity_id, amount, currency, received_at, payment_ref, network=None, txid=None, verification_state=None):
        try:
            digest=record_revenue(self.c,opportunity_id,amount,currency,received_at,payment_ref,network=network,txid=txid,verification_state=verification_state,commit=False)
            message=self.android.envelope('REVENUE_RECEIVED',{'opportunity_id':opportunity_id,'amount':amount,'currency':currency,'payment_ref':payment_ref,'payment_network':network,'verification_state':verification_state or ('RECORDED_UNVERIFIED' if str(currency).upper() in {'USDT','USDC','BTC','ETH','TRX','DAI'} else 'RECORDED'),'digest':digest})
            audit(self.c,'android_message_issued','opportunity',opportunity_id,{'kind':message['kind']})
            # A payment claim is not settlement proof. Keep DELIVERED until verification.
            self.c.commit()
            return message
        except Exception:
            self.c.rollback(); raise


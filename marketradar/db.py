from __future__ import annotations
import json, sqlite3
from urllib.parse import urlparse
from datetime import datetime, timezone
from pathlib import Path

SCHEMA='''
CREATE TABLE IF NOT EXISTS sources(id INTEGER PRIMARY KEY,name TEXT UNIQUE,base_url TEXT,adapter TEXT,type TEXT,status TEXT,iran_status TEXT,kyc_status TEXT,payment_status TEXT,execution_mode TEXT,proposal_limit TEXT,last_checked TEXT,health REAL,source_kind TEXT DEFAULT 'website',acquisition TEXT DEFAULT 'http',verification_state TEXT DEFAULT 'unverified',access_scope TEXT DEFAULT 'public',terms_status TEXT DEFAULT 'not_reviewed',failure_count INTEGER DEFAULT 0,last_error TEXT,next_retry_at TEXT,country TEXT,region TEXT,language TEXT,source_family TEXT,execution_capability TEXT DEFAULT 'manual',policy_lane TEXT DEFAULT 'REVIEW',daily_scan INTEGER DEFAULT 0,needs_analysis INTEGER DEFAULT 0,source_role TEXT,iran_policy_basis TEXT,iran_policy_url TEXT,policy_checked_at TEXT,source_origin TEXT,upstream_sources TEXT,source_verification_state TEXT DEFAULT 'DISCOVERED',iran_eligibility TEXT DEFAULT 'UNKNOWN',kyc_requirement TEXT DEFAULT 'UNKNOWN',payment_capabilities TEXT,payout_evidence_url TEXT,kyc_evidence_url TEXT,terms_evidence_url TEXT,last_verified_at TEXT,evidence_confidence REAL DEFAULT 0,market_intelligence_value TEXT DEFAULT 'MEDIUM',execution_ready INTEGER DEFAULT 0,discovery_basis TEXT,source_lane TEXT DEFAULT 'REVIEW',blacklist_reason TEXT,blacklisted_at TEXT,project_scan_interval_minutes INTEGER DEFAULT 60,intelligence_scan_interval_minutes INTEGER DEFAULT 720);
CREATE TABLE IF NOT EXISTS source_verification_state(source TEXT PRIMARY KEY,checked_at TEXT,http_status INTEGER,source_verification_state TEXT,iran_eligibility TEXT,kyc_requirement TEXT,payment_capabilities TEXT,payout_evidence_url TEXT,kyc_evidence_url TEXT,terms_evidence_url TEXT,evidence_confidence REAL DEFAULT 0,evidence_urls_json TEXT,findings_json TEXT,policy_lane TEXT,execution_ready INTEGER DEFAULT 0,error TEXT);
CREATE TABLE IF NOT EXISTS source_contracts(source TEXT PRIMARY KEY,source_kind TEXT,acquisition TEXT,adapter TEXT,access_scope TEXT,verification_state TEXT,terms_status TEXT,verification_basis TEXT,updated_at TEXT,runtime_verification_state TEXT,country TEXT,region TEXT,language TEXT,source_family TEXT,execution_capability TEXT DEFAULT 'manual',policy_lane TEXT DEFAULT 'REVIEW',daily_scan INTEGER DEFAULT 0,needs_analysis INTEGER DEFAULT 0,source_role TEXT,iran_policy_basis TEXT,iran_policy_url TEXT,policy_checked_at TEXT,source_origin TEXT,upstream_sources TEXT,source_verification_state TEXT DEFAULT 'DISCOVERED',iran_eligibility TEXT DEFAULT 'UNKNOWN',kyc_requirement TEXT DEFAULT 'UNKNOWN',payment_capabilities TEXT,payout_evidence_url TEXT,kyc_evidence_url TEXT,terms_evidence_url TEXT,last_verified_at TEXT,evidence_confidence REAL DEFAULT 0,market_intelligence_value TEXT DEFAULT 'MEDIUM',execution_ready INTEGER DEFAULT 0,discovery_basis TEXT,source_lane TEXT DEFAULT 'REVIEW',blacklist_reason TEXT,blacklisted_at TEXT,project_scan_interval_minutes INTEGER DEFAULT 60,intelligence_scan_interval_minutes INTEGER DEFAULT 720);
CREATE TABLE IF NOT EXISTS raw_observations(id INTEGER PRIMARY KEY,source TEXT,url TEXT,observed_at TEXT,payload BLOB,payload_sha256 TEXT,http_status INTEGER,content_type TEXT,observation_kind TEXT DEFAULT 'normalized_item',UNIQUE(source,url,payload_sha256));
CREATE TABLE IF NOT EXISTS source_candidates(id INTEGER PRIMARY KEY,candidate_key TEXT UNIQUE,base_url TEXT,name TEXT,discovery_basis TEXT,provider TEXT,query TEXT,region TEXT,language TEXT,source_family TEXT,evidence_confidence REAL DEFAULT 0,evidence_json TEXT,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,status TEXT DEFAULT 'CANDIDATE');
CREATE INDEX IF NOT EXISTS idx_source_candidates_status ON source_candidates(status);
CREATE TABLE IF NOT EXISTS source_identity(source TEXT PRIMARY KEY,canonical_host TEXT,organization TEXT,brand TEXT,platform TEXT,endpoint TEXT,regional_variant TEXT,semantic_key TEXT,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_workflows(source TEXT NOT NULL,step_order INTEGER NOT NULL,step TEXT NOT NULL,instruction TEXT,requires_approval INTEGER DEFAULT 0,language TEXT,observed_at TEXT,PRIMARY KEY(source,step_order));
CREATE TABLE IF NOT EXISTS foreign_page_snapshots(id INTEGER PRIMARY KEY,source TEXT,url TEXT,observed_at TEXT,language TEXT,content_sha256 TEXT,payload BLOB,translation_provider TEXT,translation_status TEXT,translation_target TEXT);
CREATE TABLE IF NOT EXISTS engine_manifests(engine_id TEXT PRIMARY KEY,name TEXT NOT NULL,version TEXT NOT NULL,standalone INTEGER DEFAULT 1,connectable INTEGER DEFAULT 1,capabilities_json TEXT NOT NULL,execution_mode TEXT,health TEXT,endpoint TEXT,input_contract TEXT,output_contract TEXT,qa_contract TEXT,authorization_scope TEXT,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS engine_job_runs(job_id TEXT PRIMARY KEY,engine_id TEXT NOT NULL,opportunity_id INTEGER,task_type TEXT,status TEXT NOT NULL,job_json TEXT,result_json TEXT,qa_json TEXT,error TEXT,started_at TEXT,finished_at TEXT);

CREATE TABLE IF NOT EXISTS opportunities(id INTEGER PRIMARY KEY,source TEXT,title TEXT,url TEXT UNIQUE,description TEXT,category TEXT,budget REAL,currency TEXT,payment TEXT,evidence_confidence REAL,quality_score REAL,eligibility TEXT,score REAL,time_to_money REAL,state TEXT,rejection_reason TEXT,first_seen TEXT,last_seen TEXT,country TEXT,region TEXT,iran_access TEXT DEFAULT 'UNKNOWN',blacklist_reason TEXT,need_summary TEXT,tool_recommendation TEXT,automation_mode TEXT DEFAULT 'MANUAL',payment_network TEXT,payment_verified INTEGER DEFAULT 0,skill_fit REAL DEFAULT 0,difficulty_score REAL DEFAULT 1,difficulty_fit REAL DEFAULT 0,learning_value REAL DEFAULT 0,competition_score REAL DEFAULT 0,application_speed_score REAL DEFAULT 0,freshness_score REAL DEFAULT 0,recommended_level INTEGER DEFAULT 3,track TEXT DEFAULT 'software_engineering',application_path TEXT DEFAULT 'MANUAL_REVIEW',skill_gap_json TEXT,rank_score REAL DEFAULT 0,application_ready INTEGER DEFAULT 0,application_reason TEXT,kyc_requirement TEXT DEFAULT 'UNKNOWN',opportunity_type TEXT DEFAULT 'OPPORTUNITY',party_entity_id INTEGER,market_signal_confidence REAL DEFAULT 0,ttm_confidence REAL DEFAULT 0,work_domain TEXT,task_type TEXT,operations_json TEXT,input_formats_json TEXT,output_formats_json TEXT,requirements_json TEXT,qa_requirements_json TEXT,manual_execution_possible INTEGER DEFAULT 1,automation_status TEXT DEFAULT 'MANUAL_OR_UNKNOWN',automation_provider_ids_json TEXT,suitability_status TEXT DEFAULT 'UNASSESSED',recommendation_domain TEXT);
CREATE TABLE IF NOT EXISTS opportunity_sources(opportunity_id INTEGER NOT NULL,source TEXT NOT NULL,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,PRIMARY KEY(opportunity_id,source));
CREATE INDEX IF NOT EXISTS idx_opportunity_sources_source ON opportunity_sources(source);
CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY,opportunity_id INTEGER,kind TEXT,source TEXT,url TEXT,finding TEXT,confidence REAL,provenance_root TEXT,observed_at TEXT,evidence_hash TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,at TEXT,event TEXT,entity_type TEXT,entity_id TEXT,details TEXT);
CREATE TABLE IF NOT EXISTS claim_conflicts(id INTEGER PRIMARY KEY,opportunity_id INTEGER NOT NULL,claim_type TEXT NOT NULL,previous_claim_id INTEGER NOT NULL,new_claim_id INTEGER NOT NULL,relation TEXT NOT NULL,detected_at TEXT NOT NULL,details_json TEXT NOT NULL,UNIQUE(previous_claim_id,new_claim_id,relation));
CREATE TABLE IF NOT EXISTS application_events(id INTEGER PRIMARY KEY,opportunity_id INTEGER,from_state TEXT,to_state TEXT,actor TEXT,at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS revenue(id INTEGER PRIMARY KEY,opportunity_id INTEGER,amount REAL,currency TEXT,received_at TEXT,payment_ref TEXT UNIQUE,digest TEXT UNIQUE,payment_network TEXT,verification_state TEXT DEFAULT 'RECORDED');
CREATE TABLE IF NOT EXISTS approvals(approval_id TEXT PRIMARY KEY,action TEXT NOT NULL,target TEXT NOT NULL,parameters_digest TEXT NOT NULL,evidence_digest TEXT NOT NULL,policy_version TEXT NOT NULL,issued_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,used_at INTEGER);
CREATE TABLE IF NOT EXISTS android_messages(message_id TEXT PRIMARY KEY,kind TEXT NOT NULL,issued_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,consumed_at INTEGER);
CREATE TABLE IF NOT EXISTS federation_runs(id INTEGER PRIMARY KEY,source TEXT,started_at TEXT,status TEXT,http_status INTEGER,observation_count INTEGER,error TEXT,snapshot_sha256 TEXT);
CREATE TABLE IF NOT EXISTS source_health_history(id INTEGER PRIMARY KEY,source TEXT,checked_at TEXT,status TEXT,http_status INTEGER,health REAL,verification_state TEXT,parse_ok INTEGER,parsed_count INTEGER,error TEXT,snapshot_sha256 TEXT,failure_count INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS source_onboarding_events(id INTEGER PRIMARY KEY,source TEXT,at TEXT,event TEXT,ok INTEGER,errors TEXT,warnings TEXT);
CREATE TABLE IF NOT EXISTS source_endpoints(id INTEGER PRIMARY KEY,source TEXT NOT NULL,url TEXT NOT NULL,endpoint_kind TEXT NOT NULL,status TEXT DEFAULT 'DISCOVERED',http_status INTEGER,last_checked_at TEXT,evidence_confidence REAL DEFAULT 0,content_sha256 TEXT,UNIQUE(source,url));
CREATE TABLE IF NOT EXISTS source_constraints(id INTEGER PRIMARY KEY,source TEXT NOT NULL,constraint_key TEXT NOT NULL,value_int INTEGER,value_text TEXT,confidence REAL DEFAULT 0,evidence_url TEXT,checked_at TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'CONFIRMED',UNIQUE(source,constraint_key));
CREATE TABLE IF NOT EXISTS source_review_queue(id INTEGER PRIMARY KEY,source TEXT UNIQUE NOT NULL,reason TEXT NOT NULL,question TEXT,created_at TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'OPEN',resolved_at TEXT,resolution TEXT,evidence_url TEXT);
CREATE INDEX IF NOT EXISTS idx_source_review_queue_status ON source_review_queue(status);
CREATE INDEX IF NOT EXISTS idx_source_constraints_source ON source_constraints(source);
CREATE INDEX IF NOT EXISTS idx_source_endpoints_source ON source_endpoints(source);
CREATE TABLE IF NOT EXISTS source_discovery_evidence(id INTEGER PRIMARY KEY,source TEXT NOT NULL,observed_at TEXT NOT NULL,query TEXT,query_family TEXT,country TEXT,region TEXT,language TEXT,provider TEXT,result_url TEXT,title TEXT,snippet TEXT,discovery_method TEXT NOT NULL,evidence_hash TEXT UNIQUE);
CREATE INDEX IF NOT EXISTS idx_discovery_evidence_source ON source_discovery_evidence(source);
CREATE INDEX IF NOT EXISTS idx_discovery_evidence_country ON source_discovery_evidence(country,query_family);
CREATE TABLE IF NOT EXISTS discovery_runs(id INTEGER PRIMARY KEY,started_at TEXT NOT NULL,finished_at TEXT,status TEXT,queries_planned INTEGER DEFAULT 0,queries_executed INTEGER DEFAULT 0,results_seen INTEGER DEFAULT 0,candidates_found INTEGER DEFAULT 0,new_sources INTEGER DEFAULT 0,errors INTEGER DEFAULT 0,coverage_entities INTEGER DEFAULT 0,coverage_entities_queried INTEGER DEFAULT 0,provider TEXT,notes TEXT);
CREATE TABLE IF NOT EXISTS discovery_query_observations(id INTEGER PRIMARY KEY,query_id TEXT,observed_at TEXT NOT NULL,query TEXT,query_family TEXT,operator_mode TEXT,country TEXT,language TEXT,provider TEXT,result_url TEXT,title TEXT,snippet TEXT,community_signal INTEGER DEFAULT 0,policy_signal INTEGER DEFAULT 0,engine_count INTEGER DEFAULT 0,result_hash TEXT UNIQUE);
CREATE INDEX IF NOT EXISTS idx_discovery_query_family ON discovery_query_observations(query_family,operator_mode);
CREATE TABLE IF NOT EXISTS intelligence_nodes(id INTEGER PRIMARY KEY,node_type TEXT NOT NULL,node_key TEXT NOT NULL,label TEXT,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,weight REAL DEFAULT 0,UNIQUE(node_type,node_key));
CREATE TABLE IF NOT EXISTS intelligence_edges(id INTEGER PRIMARY KEY,source_key TEXT NOT NULL,target_key TEXT NOT NULL,edge_type TEXT NOT NULL,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,weight REAL DEFAULT 0,UNIQUE(source_key,target_key,edge_type));
CREATE TABLE IF NOT EXISTS community_signals(id INTEGER PRIMARY KEY,source TEXT,observed_at TEXT NOT NULL,signal TEXT NOT NULL,polarity TEXT DEFAULT 'neutral',confidence REAL DEFAULT 0,evidence_url TEXT,evidence_hash TEXT UNIQUE);
CREATE INDEX IF NOT EXISTS idx_intelligence_nodes_type ON intelligence_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_intelligence_edges_source ON intelligence_edges(source_key);
CREATE TABLE IF NOT EXISTS user_profile(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tool_proposals(id INTEGER PRIMARY KEY,opportunity_id INTEGER UNIQUE NOT NULL,category TEXT,tool_name TEXT,purpose TEXT,complexity TEXT,components TEXT,build_recommendation TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS application_plans(id INTEGER PRIMARY KEY,opportunity_id INTEGER UNIQUE NOT NULL,mode TEXT NOT NULL,url TEXT NOT NULL,fields_json TEXT NOT NULL,authorization_required INTEGER NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS opportunity_rank_history(id INTEGER PRIMARY KEY,opportunity_id INTEGER NOT NULL,observed_at TEXT NOT NULL,rank_score REAL,skill_fit REAL,difficulty_score REAL,difficulty_fit REAL,learning_value REAL,competition_score REAL,application_speed_score REAL,freshness_score REAL,recommended_level INTEGER,track TEXT,profile_level INTEGER,reason TEXT);
CREATE TABLE IF NOT EXISTS application_queue(id INTEGER PRIMARY KEY,opportunity_id INTEGER UNIQUE NOT NULL,priority REAL NOT NULL,status TEXT NOT NULL,ready_at TEXT,application_path TEXT,authorization_required INTEGER DEFAULT 1,reason TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS operational_action_log(id INTEGER PRIMARY KEY,opportunity_id INTEGER NOT NULL,provider TEXT,mode TEXT,status TEXT,external_ref TEXT,response_sha256 TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS delivery_evidence(id INTEGER PRIMARY KEY,opportunity_id INTEGER NOT NULL,artifact_path TEXT NOT NULL,artifact_sha256 TEXT NOT NULL,evidence_url TEXT,observed_at TEXT NOT NULL,actor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payment_verification(id INTEGER PRIMARY KEY,opportunity_id INTEGER NOT NULL,payment_ref TEXT NOT NULL,status TEXT NOT NULL,network TEXT,txid TEXT,checked_at TEXT NOT NULL,actor TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS idx_delivery_once ON delivery_evidence(opportunity_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_ref ON payment_verification(payment_ref);
CREATE TRIGGER operational_action_log_no_update BEFORE UPDATE ON operational_action_log BEGIN SELECT RAISE(ABORT,'operational action log is immutable'); END;
CREATE TRIGGER operational_action_log_no_delete BEFORE DELETE ON operational_action_log BEGIN SELECT RAISE(ABORT,'operational action log is immutable'); END;
CREATE TRIGGER delivery_evidence_no_update BEFORE UPDATE ON delivery_evidence BEGIN SELECT RAISE(ABORT,'delivery evidence is immutable'); END;
CREATE TRIGGER delivery_evidence_no_delete BEFORE DELETE ON delivery_evidence BEGIN SELECT RAISE(ABORT,'delivery evidence is immutable'); END;
CREATE TRIGGER payment_verification_no_update BEFORE UPDATE ON payment_verification BEGIN SELECT RAISE(ABORT,'payment verification is immutable'); END;
CREATE TRIGGER payment_verification_no_delete BEFORE DELETE ON payment_verification BEGIN SELECT RAISE(ABORT,'payment verification is immutable'); END;
CREATE TABLE IF NOT EXISTS opportunity_outcomes(id INTEGER PRIMARY KEY,opportunity_id INTEGER NOT NULL,observed_at TEXT NOT NULL,outcome TEXT NOT NULL,reason TEXT,amount REAL,currency TEXT,notes TEXT);
CREATE TABLE IF NOT EXISTS outcome_reason_learning(reason TEXT NOT NULL,outcome TEXT NOT NULL,count INTEGER NOT NULL DEFAULT 0,last_seen TEXT,PRIMARY KEY(reason,outcome));
CREATE TABLE IF NOT EXISTS opportunity_learning(opportunity_id INTEGER PRIMARY KEY,acceptance_probability REAL DEFAULT 0.5,source_acceptance_rate REAL DEFAULT 0.5,category_acceptance_rate REAL DEFAULT 0.5,global_acceptance_rate REAL DEFAULT 0.5,expected_value REAL DEFAULT 0,observed_revenue REAL DEFAULT 0,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS application_attempts(id INTEGER PRIMARY KEY,opportunity_id INTEGER NOT NULL,attempt_no INTEGER NOT NULL,started_at TEXT NOT NULL,status TEXT,error TEXT,UNIQUE(opportunity_id,attempt_no));
CREATE TABLE IF NOT EXISTS source_scan_state(source TEXT PRIMARY KEY,last_project_scan_at TEXT,last_intelligence_scan_at TEXT,next_project_scan_at TEXT,next_intelligence_scan_at TEXT,project_scan_count INTEGER DEFAULT 0,intelligence_scan_count INTEGER DEFAULT 0,last_status TEXT,last_error TEXT);
CREATE TABLE IF NOT EXISTS source_blacklist_archive(id INTEGER PRIMARY KEY,source TEXT NOT NULL,reason TEXT NOT NULL,observed_at TEXT NOT NULL,evidence_json TEXT,UNIQUE(source,reason));
CREATE TABLE IF NOT EXISTS opportunity_blacklist_archive(id INTEGER PRIMARY KEY,opportunity_id INTEGER NOT NULL,reason TEXT NOT NULL,observed_at TEXT NOT NULL,evidence_json TEXT,UNIQUE(opportunity_id,reason));
CREATE TABLE IF NOT EXISTS provider_registry(provider_id TEXT PRIMARY KEY,name TEXT NOT NULL,version TEXT,standalone INTEGER DEFAULT 1,capabilities_json TEXT NOT NULL,enabled INTEGER DEFAULT 1,health TEXT DEFAULT 'UNKNOWN',installed INTEGER DEFAULT 0,connected INTEGER DEFAULT 0,execution_mode TEXT DEFAULT 'LOCAL',endpoint TEXT,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS daily_recommendations(id INTEGER PRIMARY KEY,generated_at TEXT NOT NULL,domain TEXT NOT NULL,opportunity_id INTEGER,rank INTEGER,scope TEXT NOT NULL,visible_default INTEGER DEFAULT 1,reason_json TEXT,automation_status TEXT,suitability_status TEXT);
CREATE INDEX IF NOT EXISTS idx_daily_recommendations_domain ON daily_recommendations(domain,generated_at DESC);
CREATE TABLE IF NOT EXISTS product_build_specs(id INTEGER PRIMARY KEY,generated_at TEXT NOT NULL,product_key TEXT UNIQUE NOT NULL,product_name TEXT NOT NULL,demand_score REAL DEFAULT 0,opportunity_count INTEGER DEFAULT 0,task_count INTEGER DEFAULT 0,output_count INTEGER DEFAULT 0,suggested_capabilities_json TEXT,requirements_json TEXT,source_evidence_json TEXT,business_models_json TEXT,status TEXT DEFAULT 'PROPOSED');
CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(score DESC);
CREATE INDEX IF NOT EXISTS idx_source_health_source_time ON source_health_history(source,checked_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_revenue_one_per_opportunity ON revenue(opportunity_id);
CREATE TRIGGER raw_no_update BEFORE UPDATE ON raw_observations BEGIN SELECT RAISE(ABORT,'raw observations are immutable'); END;
CREATE TRIGGER raw_no_delete BEFORE DELETE ON raw_observations BEGIN SELECT RAISE(ABORT,'raw observations are immutable'); END;
CREATE TRIGGER evidence_no_update BEFORE UPDATE ON evidence BEGIN SELECT RAISE(ABORT,'evidence records are immutable'); END;
CREATE TRIGGER evidence_no_delete BEFORE DELETE ON evidence BEGIN SELECT RAISE(ABORT,'evidence records are immutable'); END;
CREATE TRIGGER opportunity_source_no_delete BEFORE DELETE ON opportunity_sources BEGIN SELECT RAISE(ABORT,'opportunity source provenance is immutable'); END;
CREATE TRIGGER opportunity_source_binding_immutable BEFORE UPDATE OF opportunity_id,source,first_seen ON opportunity_sources BEGIN SELECT RAISE(ABORT,'opportunity source binding is immutable'); END;
CREATE TRIGGER opportunity_url_immutable BEFORE UPDATE OF url ON opportunities BEGIN SELECT RAISE(ABORT,'opportunity URL is immutable'); END;
CREATE TRIGGER opportunity_first_seen_immutable BEFORE UPDATE OF first_seen ON opportunities BEGIN SELECT RAISE(ABORT,'opportunity first_seen is immutable'); END;
CREATE TRIGGER opportunity_action_snapshot_frozen BEFORE UPDATE OF source,title,description,category,budget,currency,payment,evidence_confidence,quality_score,eligibility,score,time_to_money,rejection_reason ON opportunities WHEN OLD.state <> 'DISCOVERED' BEGIN SELECT RAISE(ABORT,'action snapshot is immutable after execution begins'); END;
CREATE TRIGGER source_no_delete BEFORE DELETE ON sources BEGIN SELECT RAISE(ABORT,'source records are immutable; disable instead'); END;
CREATE TRIGGER source_contract_no_delete BEFORE DELETE ON source_contracts BEGIN SELECT RAISE(ABORT,'source contracts are immutable; disable source instead'); END;
CREATE TRIGGER source_runtime_state_valid BEFORE INSERT ON sources WHEN NEW.verification_state NOT IN ('unverified','documented','verified','degraded','blocked') BEGIN SELECT RAISE(ABORT,'invalid source verification state'); END;
CREATE TRIGGER source_runtime_state_valid_update BEFORE UPDATE OF verification_state ON sources WHEN NEW.verification_state NOT IN ('unverified','documented','verified','degraded','blocked') BEGIN SELECT RAISE(ABORT,'invalid source verification state'); END;
CREATE TRIGGER source_contract_declared_state_valid BEFORE INSERT ON source_contracts WHEN NEW.verification_state NOT IN ('unverified','documented','verified','degraded','blocked') BEGIN SELECT RAISE(ABORT,'invalid declared verification state'); END;
CREATE TRIGGER source_contract_declared_state_valid_update BEFORE UPDATE OF verification_state ON source_contracts WHEN NEW.verification_state NOT IN ('unverified','documented','verified','degraded','blocked') BEGIN SELECT RAISE(ABORT,'invalid declared verification state'); END;
CREATE TRIGGER source_contract_runtime_state_valid BEFORE INSERT ON source_contracts WHEN NEW.runtime_verification_state IS NOT NULL AND NEW.runtime_verification_state NOT IN ('unverified','documented','verified','degraded','blocked') BEGIN SELECT RAISE(ABORT,'invalid runtime verification state'); END;
CREATE TRIGGER source_contract_runtime_state_valid_update BEFORE UPDATE OF runtime_verification_state ON source_contracts WHEN NEW.runtime_verification_state IS NOT NULL AND NEW.runtime_verification_state NOT IN ('unverified','documented','verified','degraded','blocked') BEGIN SELECT RAISE(ABORT,'invalid runtime verification state'); END;
CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'audit records are immutable'); END;
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'audit records are immutable'); END;
CREATE TRIGGER application_events_no_update BEFORE UPDATE ON application_events BEGIN SELECT RAISE(ABORT,'application events are immutable'); END;
CREATE TRIGGER application_events_no_delete BEFORE DELETE ON application_events BEGIN SELECT RAISE(ABORT,'application events are immutable'); END;
CREATE TRIGGER revenue_no_update BEFORE UPDATE ON revenue BEGIN SELECT RAISE(ABORT,'revenue records are immutable'); END;
CREATE TRIGGER revenue_no_delete BEFORE DELETE ON revenue BEGIN SELECT RAISE(ABORT,'revenue records are immutable'); END;
CREATE TRIGGER source_health_history_no_update BEFORE UPDATE ON source_health_history BEGIN SELECT RAISE(ABORT,'source health history is immutable'); END;
CREATE TRIGGER source_health_history_no_delete BEFORE DELETE ON source_health_history BEGIN SELECT RAISE(ABORT,'source health history is immutable'); END;
CREATE TRIGGER federation_runs_no_update BEFORE UPDATE ON federation_runs BEGIN SELECT RAISE(ABORT,'federation runs are immutable'); END;
CREATE TRIGGER federation_runs_no_delete BEFORE DELETE ON federation_runs BEGIN SELECT RAISE(ABORT,'federation runs are immutable'); END;
CREATE TRIGGER source_onboarding_events_no_update BEFORE UPDATE ON source_onboarding_events BEGIN SELECT RAISE(ABORT,'source onboarding events are immutable'); END;
CREATE TRIGGER source_onboarding_events_no_delete BEFORE DELETE ON source_onboarding_events BEGIN SELECT RAISE(ABORT,'source onboarding events are immutable'); END;
CREATE TRIGGER tool_proposals_no_update BEFORE UPDATE ON tool_proposals BEGIN SELECT RAISE(ABORT,'tool proposals are immutable'); END;
CREATE TRIGGER opportunity_outcomes_no_update BEFORE UPDATE ON opportunity_outcomes BEGIN SELECT RAISE(ABORT,'opportunity outcomes are immutable'); END;
CREATE TRIGGER opportunity_outcomes_no_delete BEFORE DELETE ON opportunity_outcomes BEGIN SELECT RAISE(ABORT,'opportunity outcomes are immutable'); END;
CREATE TRIGGER outcome_reason_learning_no_delete BEFORE DELETE ON outcome_reason_learning BEGIN SELECT RAISE(ABORT,'outcome reason learning is immutable'); END;
CREATE TRIGGER application_attempts_no_update BEFORE UPDATE ON application_attempts BEGIN SELECT RAISE(ABORT,'application attempts are immutable'); END;
CREATE TRIGGER application_attempts_no_delete BEFORE DELETE ON application_attempts BEGIN SELECT RAISE(ABORT,'application attempts are immutable'); END;
CREATE TRIGGER tool_proposals_no_delete BEFORE DELETE ON tool_proposals BEGIN SELECT RAISE(ABORT,'tool proposals are immutable'); END;
CREATE TRIGGER application_plans_no_update BEFORE UPDATE ON application_plans BEGIN SELECT RAISE(ABORT,'application plans are immutable'); END;
CREATE TRIGGER application_plans_no_delete BEFORE DELETE ON application_plans BEGIN SELECT RAISE(ABORT,'application plans are immutable'); END;
CREATE TRIGGER approvals_no_delete BEFORE DELETE ON approvals BEGIN SELECT RAISE(ABORT,'approval records are immutable'); END;
CREATE TRIGGER approvals_binding_immutable BEFORE UPDATE OF action,target,parameters_digest,evidence_digest,policy_version,issued_at,expires_at ON approvals BEGIN SELECT RAISE(ABORT,'approval binding is immutable'); END;
CREATE TRIGGER approvals_used_once BEFORE UPDATE OF used_at ON approvals WHEN OLD.used_at IS NOT NULL OR (NEW.used_at IS NULL AND OLD.used_at IS NOT NULL) BEGIN SELECT RAISE(ABORT,'approval replay state is immutable'); END;
CREATE TRIGGER android_messages_no_delete BEFORE DELETE ON android_messages BEGIN SELECT RAISE(ABORT,'android messages are immutable'); END;
CREATE TRIGGER android_messages_binding_immutable BEFORE UPDATE OF message_id,kind,issued_at,expires_at ON android_messages BEGIN SELECT RAISE(ABORT,'android message binding is immutable'); END;
CREATE TRIGGER android_messages_consume_once BEFORE UPDATE OF consumed_at ON android_messages WHEN OLD.consumed_at IS NOT NULL OR NEW.consumed_at IS NULL BEGIN SELECT RAISE(ABORT,'android message replay state is immutable'); END;
CREATE TRIGGER evidence_requires_opportunity BEFORE INSERT ON evidence WHEN (SELECT id FROM opportunities WHERE id=NEW.opportunity_id) IS NULL BEGIN SELECT RAISE(ABORT,'evidence references unknown opportunity'); END;
CREATE TRIGGER application_event_requires_opportunity BEFORE INSERT ON application_events WHEN (SELECT id FROM opportunities WHERE id=NEW.opportunity_id) IS NULL BEGIN SELECT RAISE(ABORT,'application event references unknown opportunity'); END;
CREATE TRIGGER revenue_requires_opportunity BEFORE INSERT ON revenue WHEN (SELECT id FROM opportunities WHERE id=NEW.opportunity_id) IS NULL BEGIN SELECT RAISE(ABORT,'revenue references unknown opportunity'); END;
CREATE TRIGGER revenue_requires_delivered BEFORE INSERT ON revenue WHEN (SELECT state FROM opportunities WHERE id=NEW.opportunity_id) <> 'DELIVERED' BEGIN SELECT RAISE(ABORT,'revenue requires delivered opportunity'); END;
CREATE TRIGGER opportunity_source_requires_opportunity BEFORE INSERT ON opportunity_sources WHEN (SELECT id FROM opportunities WHERE id=NEW.opportunity_id) IS NULL BEGIN SELECT RAISE(ABORT,'opportunity source references unknown opportunity'); END;
CREATE TRIGGER opportunity_state_update_requires_event BEFORE UPDATE OF state ON opportunities WHEN OLD.state <> NEW.state AND NOT EXISTS (SELECT 1 FROM application_events WHERE opportunity_id=NEW.id AND from_state=OLD.state AND to_state=NEW.state) BEGIN SELECT RAISE(ABORT,'opportunity state requires application event'); END;
CREATE TRIGGER opportunity_no_delete BEFORE DELETE ON opportunities BEGIN SELECT RAISE(ABORT,'opportunities are immutable'); END;
CREATE TRIGGER opportunity_state_valid BEFORE UPDATE OF state ON opportunities WHEN NEW.state NOT IN ('DISCOVERED','ELIGIBILITY_CHECK','RECOMMENDED','APPROVAL_PENDING','SUBMITTED','VIEWED','MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','IN_PROGRESS','DELIVERED','PAID','REJECTED','EXPIRED','CANCELLED') BEGIN SELECT RAISE(ABORT,'invalid opportunity state'); END;
CREATE TRIGGER opportunity_transition_valid BEFORE UPDATE OF state ON opportunities WHEN OLD.state <> NEW.state AND NOT ((OLD.state='DISCOVERED' AND NEW.state IN ('ELIGIBILITY_CHECK','REJECTED','EXPIRED')) OR (OLD.state='ELIGIBILITY_CHECK' AND NEW.state IN ('RECOMMENDED','REJECTED')) OR (OLD.state='RECOMMENDED' AND NEW.state IN ('APPROVAL_PENDING','REJECTED')) OR (OLD.state='APPROVAL_PENDING' AND NEW.state IN ('SUBMITTED','CANCELLED')) OR (OLD.state='SUBMITTED' AND NEW.state IN ('VIEWED','MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','REJECTED','EXPIRED')) OR (OLD.state='VIEWED' AND NEW.state IN ('MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','REJECTED')) OR (OLD.state='MESSAGE_RECEIVED' AND NEW.state IN ('NEGOTIATION','ACCEPTED','REJECTED')) OR (OLD.state='NEGOTIATION' AND NEW.state IN ('ACCEPTED','REJECTED','CANCELLED')) OR (OLD.state='ACCEPTED' AND NEW.state IN ('IN_PROGRESS','CANCELLED')) OR (OLD.state='IN_PROGRESS' AND NEW.state IN ('DELIVERED','CANCELLED')) OR (OLD.state='DELIVERED' AND NEW.state='PAID')) BEGIN SELECT RAISE(ABORT,'invalid state transition'); END;
CREATE TRIGGER application_event_transition_valid BEFORE INSERT ON application_events WHEN NEW.from_state NOT IN ('DISCOVERED','ELIGIBILITY_CHECK','RECOMMENDED','APPROVAL_PENDING','SUBMITTED','VIEWED','MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','IN_PROGRESS','DELIVERED','PAID','REJECTED','EXPIRED','CANCELLED') OR NEW.to_state NOT IN ('DISCOVERED','ELIGIBILITY_CHECK','RECOMMENDED','APPROVAL_PENDING','SUBMITTED','VIEWED','MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','IN_PROGRESS','DELIVERED','PAID','REJECTED','EXPIRED','CANCELLED') OR NEW.from_state <> (SELECT state FROM opportunities WHERE id=NEW.opportunity_id) OR NOT ((NEW.from_state='DISCOVERED' AND NEW.to_state IN ('ELIGIBILITY_CHECK','REJECTED','EXPIRED')) OR (NEW.from_state='ELIGIBILITY_CHECK' AND NEW.to_state IN ('RECOMMENDED','REJECTED')) OR (NEW.from_state='RECOMMENDED' AND NEW.to_state IN ('APPROVAL_PENDING','REJECTED')) OR (NEW.from_state='APPROVAL_PENDING' AND NEW.to_state IN ('SUBMITTED','CANCELLED')) OR (NEW.from_state='SUBMITTED' AND NEW.to_state IN ('VIEWED','MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','REJECTED','EXPIRED')) OR (NEW.from_state='VIEWED' AND NEW.to_state IN ('MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','REJECTED')) OR (NEW.from_state='MESSAGE_RECEIVED' AND NEW.to_state IN ('NEGOTIATION','ACCEPTED','REJECTED')) OR (NEW.from_state='NEGOTIATION' AND NEW.to_state IN ('ACCEPTED','REJECTED','CANCELLED')) OR (NEW.from_state='ACCEPTED' AND NEW.to_state IN ('IN_PROGRESS','CANCELLED')) OR (NEW.from_state='IN_PROGRESS' AND NEW.to_state IN ('DELIVERED','CANCELLED')) OR (NEW.from_state='DELIVERED' AND NEW.to_state='PAID')) BEGIN SELECT RAISE(ABORT,'invalid application event transition'); END;
CREATE TRIGGER application_event_applies_state AFTER INSERT ON application_events BEGIN UPDATE opportunities SET state=NEW.to_state WHERE id=NEW.opportunity_id AND state=NEW.from_state; END;
CREATE TRIGGER paid_requires_revenue BEFORE UPDATE OF state ON opportunities WHEN NEW.state='PAID' AND (SELECT count(*) FROM revenue WHERE opportunity_id=NEW.id)=0 BEGIN SELECT RAISE(ABORT,'paid state requires revenue'); END;
CREATE TRIGGER revenue_payment_ref_nonempty BEFORE INSERT ON revenue WHEN trim(COALESCE(NEW.payment_ref,''))='' OR NEW.amount IS NULL OR NEW.amount<=0 BEGIN SELECT RAISE(ABORT,'invalid revenue record'); END;


'''

def _ensure_column(c, table, column, ddl):
    cols={row[1] for row in c.execute(f'PRAGMA table_info({table})')}
    if column not in cols: c.execute(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}')

def _schema_statements(script):
    statement = ''
    for line in script.splitlines(True):
        statement += line
        if sqlite3.complete_statement(statement):
            text = statement.strip()
            if text:
                yield text
            statement = ''
    if statement.strip():
        raise ValueError('SCHEMA_STATEMENT_INCOMPLETE')


from .goal_completion import ensure_schema as ensure_goal_schema
from .operations import ensure_schema as ensure_operations_schema
from .economic_loop import ensure_schema as ensure_economic_schema, ensure_payment_poll_schema
from .finance import ensure_schema as ensure_finance_schema
from .notifications import ensure_schema as ensure_notifications_schema
from .email_service import ensure_schema as ensure_email_schema

def connect(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(path, timeout=15); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA busy_timeout=15000'); c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=NORMAL')
    trigger_names = [line.split()[2] for line in SCHEMA.splitlines() if line.startswith('CREATE TRIGGER ')]
    c.execute('BEGIN IMMEDIATE')
    try:
        # Trigger definitions are part of the application's security boundary.
        # CREATE TRIGGER IF NOT EXISTS would silently preserve an older, weaker
        # definition during upgrades, so every managed trigger is replaced
        # transactionally on connection/migration.
        for name in trigger_names:
            c.execute(f'DROP TRIGGER IF EXISTS {name}')
        statements=list(_schema_statements(SCHEMA))
        # Build/migrate tables and columns before installing triggers, because
        # older databases may not yet contain columns referenced by the newer
        # trigger definitions. Everything remains inside one transaction.
        for statement in statements:
            if not statement.startswith('CREATE TRIGGER '):
                c.execute(statement)
        source_cols=[('source_kind',"TEXT DEFAULT 'website'"),('acquisition',"TEXT DEFAULT 'http'"),('verification_state',"TEXT DEFAULT 'unverified'"),('access_scope',"TEXT DEFAULT 'public'"),('terms_status',"TEXT DEFAULT 'not_reviewed'"),('failure_count',"INTEGER DEFAULT 0"),('last_error',"TEXT"),('next_retry_at',"TEXT"),('country',"TEXT"),('region',"TEXT"),('language',"TEXT"),('source_family',"TEXT"),('execution_capability',"TEXT DEFAULT 'manual'"),('capability_maturity',"TEXT DEFAULT 'REGISTERED'"),('capability_evidence_json',"TEXT DEFAULT '[]'"),('capability_checked_at',"TEXT"),('stale_at',"TEXT")]
        for col,ddl in source_cols: _ensure_column(c,'sources',col,ddl)
        for col,ddl in [('source_verification_state',"TEXT DEFAULT 'DISCOVERED'"),('iran_eligibility',"TEXT DEFAULT 'UNKNOWN'"),('kyc_requirement',"TEXT DEFAULT 'UNKNOWN'"),('payment_capabilities','TEXT'),('payout_evidence_url','TEXT'),('kyc_evidence_url','TEXT'),('terms_evidence_url','TEXT'),('last_verified_at','TEXT'),('evidence_confidence','REAL DEFAULT 0'),('market_intelligence_value',"TEXT DEFAULT 'MEDIUM'"),('execution_ready','INTEGER DEFAULT 0'),('discovery_basis','TEXT')]: _ensure_column(c,'sources',col,ddl)
        for col,ddl in [('source_lane',"TEXT DEFAULT 'REVIEW'"),('blacklist_reason','TEXT'),('blacklisted_at','TEXT'),('project_scan_interval_minutes','INTEGER DEFAULT 60'),('intelligence_scan_interval_minutes','INTEGER DEFAULT 720'),('capability_maturity',"TEXT DEFAULT 'REGISTERED'"),('capability_evidence_json',"TEXT DEFAULT '[]'"),('capability_checked_at','TEXT'),('stale_at','TEXT')]: _ensure_column(c,'sources',col,ddl)
        for col,ddl in [('canonical_host','TEXT'),('organization','TEXT'),('brand','TEXT'),('platform','TEXT'),('endpoint','TEXT'),('regional_variant','TEXT'),('semantic_key','TEXT')]: _ensure_column(c,'sources',col,ddl)

        _ensure_column(c,'evidence','evidence_hash','TEXT')
        _ensure_column(c,'opportunities','quality_score','REAL DEFAULT 0')
        _ensure_column(c,'source_contracts','verification_basis','TEXT')
        _ensure_column(c,'source_contracts','runtime_verification_state','TEXT')
        for col,ddl in [('country','TEXT'),('region','TEXT'),('language','TEXT'),('source_family','TEXT'),('execution_capability',"TEXT DEFAULT 'manual'"),('capability_maturity',"TEXT DEFAULT 'REGISTERED'"),('capability_evidence_json',"TEXT DEFAULT '[]'"),('capability_checked_at','TEXT'),('stale_at','TEXT'),('iran_policy_basis','TEXT'),('iran_policy_url','TEXT'),('policy_checked_at','TEXT'),('source_origin','TEXT'),('upstream_sources','TEXT')]: _ensure_column(c,'source_contracts',col,ddl)
        for col,ddl in [('source_verification_state',"TEXT DEFAULT 'DISCOVERED'"),('iran_eligibility',"TEXT DEFAULT 'UNKNOWN'"),('kyc_requirement',"TEXT DEFAULT 'UNKNOWN'"),('payment_capabilities','TEXT'),('payout_evidence_url','TEXT'),('kyc_evidence_url','TEXT'),('terms_evidence_url','TEXT'),('last_verified_at','TEXT'),('evidence_confidence','REAL DEFAULT 0'),('market_intelligence_value',"TEXT DEFAULT 'MEDIUM'"),('execution_ready','INTEGER DEFAULT 0'),('discovery_basis','TEXT')]: _ensure_column(c,'source_contracts',col,ddl)
        for col,ddl in [('source_lane',"TEXT DEFAULT 'REVIEW'"),('blacklist_reason','TEXT'),('blacklisted_at','TEXT'),('project_scan_interval_minutes','INTEGER DEFAULT 60'),('intelligence_scan_interval_minutes','INTEGER DEFAULT 720'),('capability_maturity',"TEXT DEFAULT 'REGISTERED'"),('capability_evidence_json',"TEXT DEFAULT '[]'"),('capability_checked_at','TEXT'),('stale_at','TEXT')]: _ensure_column(c,'source_contracts',col,ddl)
        for col,ddl in [('canonical_host','TEXT'),('organization','TEXT'),('brand','TEXT'),('platform','TEXT'),('endpoint','TEXT'),('regional_variant','TEXT'),('semantic_key','TEXT')]: _ensure_column(c,'source_contracts',col,ddl)
        _ensure_column(c,'raw_observations','http_status','INTEGER')
        _ensure_column(c,'raw_observations','content_type','TEXT')
        _ensure_column(c,'raw_observations','observation_kind',"TEXT DEFAULT 'normalized_item'")
        for col,ddl in [('country','TEXT'),('region','TEXT'),('iran_access',"TEXT DEFAULT 'UNKNOWN'"),('blacklist_reason','TEXT'),('need_summary','TEXT'),('tool_recommendation','TEXT'),('automation_mode',"TEXT DEFAULT 'MANUAL'"),('payment_network','TEXT'),('payment_verified','INTEGER DEFAULT 0'),('kyc_requirement',"TEXT DEFAULT 'UNKNOWN'")]: _ensure_column(c,'opportunities',col,ddl)
        for col,ddl in [('work_domain','TEXT'),('task_type','TEXT'),('operations_json','TEXT'),('input_formats_json','TEXT'),('output_formats_json','TEXT'),('requirements_json','TEXT'),('qa_requirements_json','TEXT'),('manual_execution_possible','INTEGER DEFAULT 1'),('automation_status',"TEXT DEFAULT 'MANUAL_OR_UNKNOWN'"),('automation_provider_ids_json','TEXT'),('suitability_status',"TEXT DEFAULT 'UNASSESSED'"),('recommendation_domain','TEXT')]: _ensure_column(c,'opportunities',col,ddl)
        for col,ddl in [('skill_fit','REAL DEFAULT 0'),('difficulty_score','REAL DEFAULT 1'),('difficulty_fit','REAL DEFAULT 0'),('learning_value','REAL DEFAULT 0'),('competition_score','REAL DEFAULT 0'),('application_speed_score','REAL DEFAULT 0'),('freshness_score','REAL DEFAULT 0'),('recommended_level','INTEGER DEFAULT 3'),('track',"TEXT DEFAULT 'software_engineering'"),('application_path',"TEXT DEFAULT 'MANUAL_REVIEW'"),('skill_gap_json','TEXT'),('rank_score','REAL DEFAULT 0'),('application_ready','INTEGER DEFAULT 0'),('application_reason','TEXT'),('deadline_at','TEXT'),('deadline_confidence','REAL DEFAULT 0'),('proposal_count','INTEGER'),('proposal_count_confidence','REAL DEFAULT 0'),('client_reputation_score','REAL DEFAULT 0.45'),('client_reputation_confidence','REAL DEFAULT 0'),('acceptance_probability','REAL DEFAULT 0.5'),('competition_pressure','REAL DEFAULT 0.45'),('deadline_urgency','REAL DEFAULT 0.45'),('expected_value','REAL DEFAULT 0'),('revenue_score','REAL DEFAULT 0')]: _ensure_column(c,'opportunities',col,ddl)
        _ensure_column(c,'revenue','payment_network','TEXT')
        for col,ddl in [('opportunity_type',"TEXT DEFAULT 'OPPORTUNITY'"),('party_entity_id','INTEGER'),('market_signal_confidence','REAL DEFAULT 0'),('ttm_confidence','REAL DEFAULT 0')]: _ensure_column(c,'opportunities',col,ddl)
        _ensure_column(c,'revenue','verification_state',"TEXT DEFAULT 'RECORDED'")
        c.execute('CREATE INDEX IF NOT EXISTS idx_sources_country ON sources(country,region)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_opportunities_iran ON opportunities(iran_access,eligibility)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_claim_conflicts_opp ON claim_conflicts(opportunity_id,claim_type,detected_at DESC)')
        c.execute("CREATE TRIGGER IF NOT EXISTS claim_conflicts_no_update BEFORE UPDATE ON claim_conflicts BEGIN SELECT RAISE(ABORT,'claim conflict ledger is immutable'); END")
        c.execute("CREATE TRIGGER IF NOT EXISTS claim_conflicts_no_delete BEFORE DELETE ON claim_conflicts BEGIN SELECT RAISE(ABORT,'claim conflict ledger is immutable'); END")
        for statement in statements:
            if statement.startswith('CREATE TRIGGER '):
                c.execute(statement)
        ensure_goal_schema(c)
        ensure_operations_schema(c)
        ensure_economic_schema(c)
        ensure_payment_poll_schema(c)
        ensure_finance_schema(c)
        ensure_notifications_schema(c)
        ensure_email_schema(c)
        # Re-assert the raw-evidence security boundary after all extension schema hooks.
        # Extension migrations may manage their own DDL; raw observations remain append-only.
        c.execute("CREATE TRIGGER IF NOT EXISTS raw_no_update BEFORE UPDATE ON raw_observations BEGIN SELECT RAISE(ABORT,'raw observations are immutable'); END")
        c.execute("CREATE TRIGGER IF NOT EXISTS raw_no_delete BEFORE DELETE ON raw_observations BEGIN SELECT RAISE(ABORT,'raw observations are immutable'); END")\n        # Payment checks are append-only observations; the same payment may be checked multiple times.
        c.execute('DROP INDEX IF EXISTS idx_payment_ref')
        c.execute('CREATE INDEX IF NOT EXISTS idx_payment_ref_lookup ON payment_verification(payment_ref)')
        c.commit()
    except Exception:
        c.rollback()
        raise
    return c

def sync_source_contracts(c, records):
    now=datetime.now(timezone.utc).isoformat()
    names={s['name'] for s in records}
    try:
        from .source_identity import identity_from_record
        from .source_policy import EXECUTION_ELIGIBLE, MARKET_INTELLIGENCE_ONLY, BLACKLIST_ARCHIVE
        lane_map={'DAILY_PROJECT_SCAN':EXECUTION_ELIGIBLE,'GLOBAL_DISCOVERY':MARKET_INTELLIGENCE_ONLY,'BLOCKED_IRAN':MARKET_INTELLIGENCE_ONLY,'NEEDS_ANALYSIS':MARKET_INTELLIGENCE_ONLY}
        for s in records:
            s = dict(s)
            original_policy_lane = s.get('policy_lane') or s.get('source_lane') or 'REVIEW'
            s['_canonical_lane'] = lane_map.get(original_policy_lane, original_policy_lane)
            ident=identity_from_record(s)
            s.update(ident)
            s['semantic_key']='|'.join(s.get(k,'') for k in ('canonical_host','organization','brand','platform','endpoint','regional_variant'))
            policy_defaults = {
                'iran_status': s.get('iran_status'), 'kyc_status': s.get('kyc_status'),
                'payment_status': s.get('payment_status'), 'execution_mode': s.get('execution_mode'),
                'proposal_limit': s.get('proposal_limit'),
            }
            values=(s['name'],s['base_url'],s.get('adapter','json'),s.get('type','marketplace'),s.get('status','candidate'),
                    policy_defaults['iran_status'],policy_defaults['kyc_status'],policy_defaults['payment_status'],
                    policy_defaults['execution_mode'],policy_defaults['proposal_limit'],s.get('source_kind','website'),
                    s.get('acquisition','http'),s.get('access_scope','public'),s.get('terms_status','not_reviewed'),
                    s.get('country'),s.get('region'),s.get('language'),s.get('source_family',s.get('acquisition','http')),
                    s.get('execution_capability','manual'),s.get('capability_maturity','REGISTERED'),json.dumps(s.get('capability_evidence',[]),ensure_ascii=False),s.get('capability_checked_at'),s.get('stale_at'),original_policy_lane,int(bool(s.get('daily_scan'))),int(bool(s.get('needs_analysis'))),s.get('source_role'),
                    s.get('iran_policy_basis'),s.get('iran_policy_url'),s.get('policy_checked_at'),s.get('source_origin'),json.dumps(s.get('upstream_sources',[]),ensure_ascii=False),
                    s.get('source_verification_state','DISCOVERED'),s.get('iran_eligibility',s.get('iran_status','UNKNOWN')),s.get('kyc_requirement','UNKNOWN'),json.dumps(s.get('payment_capabilities',[]),ensure_ascii=False),
                    s.get('payout_evidence_url'),s.get('kyc_evidence_url'),s.get('terms_evidence_url'),s.get('last_verified_at'),float(s.get('evidence_confidence',0) or 0),s.get('market_intelligence_value','MEDIUM'),int(bool(s.get('execution_ready'))),s.get('discovery_basis'))
            c.execute("""INSERT INTO sources(name,base_url,adapter,type,status,iran_status,kyc_status,payment_status,execution_mode,proposal_limit,source_kind,acquisition,access_scope,terms_status,country,region,language,source_family,execution_capability,capability_maturity,capability_evidence_json,capability_checked_at,stale_at,policy_lane,daily_scan,needs_analysis,source_role,iran_policy_basis,iran_policy_url,policy_checked_at,source_origin,upstream_sources,source_verification_state,iran_eligibility,kyc_requirement,payment_capabilities,payout_evidence_url,kyc_evidence_url,terms_evidence_url,last_verified_at,evidence_confidence,market_intelligence_value,execution_ready,discovery_basis)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                         ON CONFLICT(name) DO UPDATE SET base_url=excluded.base_url, adapter=excluded.adapter, type=excluded.type,
                         status=excluded.status, source_kind=excluded.source_kind, acquisition=excluded.acquisition,
                         access_scope=excluded.access_scope, terms_status=excluded.terms_status,
                         iran_status=COALESCE(excluded.iran_status,sources.iran_status), kyc_status=COALESCE(excluded.kyc_status,sources.kyc_status), payment_status=COALESCE(excluded.payment_status,sources.payment_status),
                         execution_mode=COALESCE(excluded.execution_mode,sources.execution_mode), proposal_limit=COALESCE(excluded.proposal_limit,sources.proposal_limit),country=excluded.country,region=excluded.region,language=excluded.language,source_family=excluded.source_family,execution_capability=excluded.execution_capability,capability_maturity=excluded.capability_maturity,capability_evidence_json=excluded.capability_evidence_json,capability_checked_at=excluded.capability_checked_at,stale_at=excluded.stale_at,
                         policy_lane=excluded.policy_lane,daily_scan=excluded.daily_scan,needs_analysis=excluded.needs_analysis,source_role=excluded.source_role,iran_policy_basis=excluded.iran_policy_basis,iran_policy_url=excluded.iran_policy_url,policy_checked_at=excluded.policy_checked_at,source_origin=excluded.source_origin,upstream_sources=excluded.upstream_sources,
                         source_verification_state=excluded.source_verification_state,iran_eligibility=excluded.iran_eligibility,kyc_requirement=excluded.kyc_requirement,payment_capabilities=excluded.payment_capabilities,payout_evidence_url=excluded.payout_evidence_url,kyc_evidence_url=excluded.kyc_evidence_url,terms_evidence_url=excluded.terms_evidence_url,last_verified_at=excluded.last_verified_at,evidence_confidence=excluded.evidence_confidence,market_intelligence_value=excluded.market_intelligence_value,execution_ready=excluded.execution_ready,discovery_basis=excluded.discovery_basis""", values)
            c.execute("""INSERT INTO source_contracts(source,source_kind,acquisition,adapter,access_scope,verification_state,terms_status,verification_basis,updated_at,runtime_verification_state,country,region,language,source_family,execution_capability,capability_maturity,capability_evidence_json,capability_checked_at,stale_at,policy_lane,daily_scan,needs_analysis,source_role,iran_policy_basis,iran_policy_url,policy_checked_at,source_origin,upstream_sources,source_verification_state,iran_eligibility,kyc_requirement,payment_capabilities,payout_evidence_url,kyc_evidence_url,terms_evidence_url,last_verified_at,evidence_confidence,market_intelligence_value,execution_ready,discovery_basis)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                         ON CONFLICT(source) DO UPDATE SET source_kind=excluded.source_kind, acquisition=excluded.acquisition, adapter=excluded.adapter, access_scope=excluded.access_scope, verification_state=excluded.verification_state, terms_status=excluded.terms_status, verification_basis=excluded.verification_basis, updated_at=excluded.updated_at,country=excluded.country,region=excluded.region,language=excluded.language,source_family=excluded.source_family,execution_capability=excluded.execution_capability,capability_maturity=excluded.capability_maturity,capability_evidence_json=excluded.capability_evidence_json,capability_checked_at=excluded.capability_checked_at,stale_at=excluded.stale_at,policy_lane=excluded.policy_lane,daily_scan=excluded.daily_scan,needs_analysis=excluded.needs_analysis,source_role=excluded.source_role,iran_policy_basis=excluded.iran_policy_basis,iran_policy_url=excluded.iran_policy_url,policy_checked_at=excluded.policy_checked_at,source_origin=excluded.source_origin,upstream_sources=excluded.upstream_sources,source_verification_state=excluded.source_verification_state,iran_eligibility=excluded.iran_eligibility,kyc_requirement=excluded.kyc_requirement,payment_capabilities=excluded.payment_capabilities,payout_evidence_url=excluded.payout_evidence_url,kyc_evidence_url=excluded.kyc_evidence_url,terms_evidence_url=excluded.terms_evidence_url,last_verified_at=excluded.last_verified_at,evidence_confidence=excluded.evidence_confidence,market_intelligence_value=excluded.market_intelligence_value,execution_ready=excluded.execution_ready,discovery_basis=excluded.discovery_basis""",
                      (s['name'],s.get('source_kind','website'),s.get('acquisition','http'),s.get('adapter','json'),s.get('access_scope','public'),s.get('verification_state','unverified'),s.get('terms_status','not_reviewed'),s.get('verification_basis'),now,None,s.get('country'),s.get('region'),s.get('language'),s.get('source_family',s.get('acquisition','http')),s.get('execution_capability','manual'),s.get('capability_maturity','REGISTERED'),json.dumps(s.get('capability_evidence',[]),ensure_ascii=False),s.get('capability_checked_at'),s.get('stale_at'),original_policy_lane,int(bool(s.get('daily_scan'))),int(bool(s.get('needs_analysis'))),s.get('source_role'),s.get('iran_policy_basis'),s.get('iran_policy_url'),s.get('policy_checked_at'),s.get('source_origin'),json.dumps(s.get('upstream_sources',[]),ensure_ascii=False),s.get('source_verification_state','DISCOVERED'),s.get('iran_eligibility',s.get('iran_status','UNKNOWN')),s.get('kyc_requirement','UNKNOWN'),json.dumps(s.get('payment_capabilities',[]),ensure_ascii=False),s.get('payout_evidence_url'),s.get('kyc_evidence_url'),s.get('terms_evidence_url'),s.get('last_verified_at'),float(s.get('evidence_confidence',0) or 0),s.get('market_intelligence_value','MEDIUM'),int(bool(s.get('execution_ready'))),s.get('discovery_basis')))
            c.execute("UPDATE sources SET source_lane=COALESCE(?,source_lane),blacklist_reason=COALESCE(?,blacklist_reason),blacklisted_at=COALESCE(?,blacklisted_at),project_scan_interval_minutes=COALESCE(?,project_scan_interval_minutes),intelligence_scan_interval_minutes=COALESCE(?,intelligence_scan_interval_minutes) WHERE name=?", (s.get('source_lane'),s.get('blacklist_reason'),s.get('blacklisted_at'),s.get('project_scan_interval_minutes'),s.get('intelligence_scan_interval_minutes'),s['name']))
            c.execute("UPDATE sources SET canonical_host=?,organization=?,brand=?,platform=?,endpoint=?,regional_variant=?,semantic_key=?,source_lane=? WHERE name=?", (s.get('canonical_host'),s.get('organization'),s.get('brand'),s.get('platform'),s.get('endpoint'),s.get('regional_variant'),s.get('semantic_key'),s.get('_canonical_lane','REVIEW'),s['name']))
            c.execute("INSERT INTO source_identity(source,canonical_host,organization,brand,platform,endpoint,regional_variant,semantic_key,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET canonical_host=excluded.canonical_host,organization=excluded.organization,brand=excluded.brand,platform=excluded.platform,endpoint=excluded.endpoint,regional_variant=excluded.regional_variant,semantic_key=excluded.semantic_key,updated_at=excluded.updated_at", (s['name'],s.get('canonical_host'),s.get('organization'),s.get('brand'),s.get('platform'),s.get('endpoint'),s.get('regional_variant'),s.get('semantic_key'),now))
            c.execute("UPDATE source_contracts SET source_lane=COALESCE(?,source_lane),blacklist_reason=COALESCE(?,blacklist_reason),blacklisted_at=COALESCE(?,blacklisted_at),project_scan_interval_minutes=COALESCE(?,project_scan_interval_minutes),intelligence_scan_interval_minutes=COALESCE(?,intelligence_scan_interval_minutes) WHERE source=?", (s.get('source_lane'),s.get('blacklist_reason'),s.get('blacklisted_at'),s.get('project_scan_interval_minutes'),s.get('intelligence_scan_interval_minutes'),s['name']))
            c.execute("UPDATE source_contracts SET canonical_host=?,organization=?,brand=?,platform=?,endpoint=?,regional_variant=?,semantic_key=?,source_lane=? WHERE source=?", (s.get('canonical_host'),s.get('organization'),s.get('brand'),s.get('platform'),s.get('endpoint'),s.get('regional_variant'),s.get('semantic_key'),s.get('_canonical_lane','REVIEW'),s['name']))
            c.execute('INSERT INTO source_onboarding_events(source,at,event,ok,errors,warnings) VALUES(?,?,?,?,?,?)', (s['name'],now,'REGISTRY_SYNC',1,'',''))
        if names:
            placeholders=','.join('?' for _ in names)
            c.execute(f"UPDATE sources SET status='disabled' WHERE name NOT IN ({placeholders}) AND COALESCE(source_origin,'') != 'dynamic_discovery'",tuple(names))
            c.execute(f"UPDATE source_contracts SET updated_at=? WHERE source NOT IN ({placeholders})",(now,*tuple(names)))
        else:
            c.execute("UPDATE sources SET status='disabled' WHERE COALESCE(source_origin,'') != 'dynamic_discovery'")
            c.execute("UPDATE source_contracts SET updated_at=?",(now,))
        c.commit()
    except Exception:
        c.rollback()
        raise


def load_dynamic_source_records(c):
    """Return source contracts discovered by the autonomous discovery layer.

    Dynamic candidates live in SQLite so discovery can grow the federation without
    rewriting the shipped config/sources.json. Config remains the declared baseline;
    runtime merges these candidates on startup.
    """
    rows=c.execute("SELECT * FROM sources WHERE source_origin='dynamic_discovery' ORDER BY name").fetchall()
    out=[]
    for row in rows:
        d=dict(row)
        try:
            d['payment_capabilities']=json.loads(d.get('payment_capabilities') or '[]')
        except Exception:
            d['payment_capabilities']=[]
        d['daily_scan']=bool(d.get('daily_scan')); d['needs_analysis']=bool(d.get('needs_analysis')); d['execution_ready']=bool(d.get('execution_ready'))
        d['allow_hosts']=[urlparse(d['base_url']).hostname] if d.get('base_url') and urlparse(d['base_url']).hostname else []
        d.setdefault('headers',{})
        out.append(d)
    return out

def audit(c,event,etype,eid,details):
    safe=json.dumps(details,sort_keys=True,ensure_ascii=False).replace('\\n',' ').replace('\\r',' ')
    c.execute('INSERT INTO audit(at,event,entity_type,entity_id,details) VALUES(?,?,?,?,?)',(datetime.now(timezone.utc).isoformat(),event,etype,str(eid),safe))

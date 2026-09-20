import argparse,json,sys
from . import __version__
from .db import connect, sync_source_contracts, load_dynamic_source_records
from .paths import data_root
from .source_registry import load_source_records
from .source_onboarding import audit_registry

def main():
    p=argparse.ArgumentParser(); p.add_argument('command',choices=['status','demo','actions','scan','verify-sources','discover-sources','autonomous-discovery','test-db','version-check','source-audit','discovery-intelligence','outcome-summary','record-outcome','operational-gate','submit-authorized','record-delivery','record-payment','final-verify','release-hardening','operationalization','daily-center','scheduled-cycle','source-pool','finance-report','android-server','email-draft']); p.add_argument('--apply-discovery',action='store_true'); p.add_argument('--search-provider',choices=['auto','brave','bing','serper','searxng'],default=None); p.add_argument('--max-cycles',type=int,default=3); p.add_argument('--opportunity-id',type=int); p.add_argument('--outcome'); p.add_argument('--reason'); p.add_argument('--amount',type=float); p.add_argument('--currency'); p.add_argument('--mode',choices=['project','intelligence'],default='project'); p.add_argument('--period',choices=['weekly','monthly','quarterly','annual'],default='monthly'); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=8765); p.add_argument('--recipient'); p.add_argument('--subject'); p.add_argument('--body'); a=p.parse_args(); c=connect(data_root()/'marketradar.db')
    try:
        if a.command=='status': print('SEPP-MarketRadar v'+__version__)
        elif a.command=='version-check': print(__version__)
        elif a.command=='release-hardening':
            from .release_hardening import run_release_hardening
            result=run_release_hardening(); print(json.dumps(result,ensure_ascii=False,indent=2))
            if not result.get('pass'): raise SystemExit(2)
        elif a.command=='operationalization':
            from .paths import app_root
            from .operationalization import run_operationalization
            result=run_operationalization(c, app_root(), perform_live_checks=False)
            print(json.dumps(result,ensure_ascii=False,indent=2))
            if not result.get('pass'): raise SystemExit(2)
        elif a.command=='daily-center':
            from .engine import MarketRadar
            c.close()
            with MarketRadar() as mr: print(json.dumps(mr.daily_center(),ensure_ascii=False,indent=2,default=str))
            return
        elif a.command=='scheduled-cycle':
            c.close()
            from tools.scheduled_cycle import main as scheduled_main
            scheduled_main()
            return
        elif a.command=='finance-report':
            from .finance import period_report, export_report
            from .paths import data_root
            r=period_report(c,a.period); out=export_report(c,r,data_root()/'reports'/'finance'); print(json.dumps({'report':r,'exports':out},ensure_ascii=False,indent=2,default=str))
        elif a.command=='android-server':
            from .engine import MarketRadar
            from .android_gateway import serve
            c.close()
            with MarketRadar() as mr: serve(mr.c,mr.runtime,host=a.host,port=a.port)
            return
        elif a.command=='email-draft':
            from .email_service import create_draft
            if not a.recipient or not a.subject or not a.body: raise SystemExit('--recipient --subject --body are required')
            draft=create_draft(c,a.recipient,a.subject,a.body,a.opportunity_id); print(json.dumps({'draft_id':draft,'status':'DRAFT','requires_approval':True},ensure_ascii=False))
        elif a.command=='source-pool':
            rows=c.execute("SELECT source_lane,COUNT(*) FROM sources GROUP BY source_lane ORDER BY source_lane").fetchall()
            unique=c.execute("SELECT COUNT(DISTINCT lower(replace(replace(base_url,'https://',''),'http://',''))) FROM sources WHERE base_url IS NOT NULL").fetchone()[0]
            total=c.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            blacklist=c.execute("SELECT COUNT(*) FROM source_blacklist_archive").fetchone()[0]
            print(json.dumps({'registered_sources':total,'distinct_base_urls':unique,'lanes':{str(r[0] or 'UNKNOWN'):int(r[1]) for r in rows},'blacklist_archive_records':blacklist},ensure_ascii=False,indent=2))
        elif a.command=='final-verify':
            from .final_readiness import run_final_verification
            result=run_final_verification();
            report=__import__('pathlib').Path(__file__).resolve().parents[1]/'reports'/'FINAL_VERIFICATION_16.1.1.json'; report.parent.mkdir(parents=True,exist_ok=True); report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');
            print(json.dumps(result,ensure_ascii=False,indent=2));
            if not result.get('pass'): raise SystemExit(2)
        elif a.command=='test-db': print('database: OK')
        elif a.command=='scan':
            from .engine import MarketRadar
            c.close()
            with MarketRadar() as mr: print(json.dumps(mr.scan(mode=a.mode),ensure_ascii=False,indent=2))
            return
        elif a.command=='discover-sources':
            from .paths import app_root
            from .source_discovery import SourceDiscoveryEngine
            from .source_search import WebSearchProvider
            root=app_root()
            catalogs=json.loads((root/'config'/'discovery_catalogs.json').read_text(encoding='utf-8'))
            queries=json.loads((root/'config'/'discovery_queries.json').read_text(encoding='utf-8'))
            coverage_path=root/'config'/'coverage_entities.json'
            coverage=json.loads(coverage_path.read_text(encoding='utf-8')).get('entities',[]) if coverage_path.exists() else []
            provider=WebSearchProvider(provider=a.search_provider,timeout=10)
            result=SourceDiscoveryEngine(catalogs,queries,provider,timeout=10,coverage_entities=coverage,state_path=root/'data'/'discovery_state.json').discover()
            from .source_discovery import persist_discovery_evidence,persist_source_endpoints,persist_candidates
            from .discovery_intelligence import persist_intelligence, persist_community_signals
            persist_discovery_evidence(c,result); persist_candidates(c,result)
            persist_intelligence(c, result.get('query_observations',[]), result.get('query_observations',[]))
            persist_community_signals(c, result.get('query_observations',[]))
            report=root/'reports'/'DISCOVERY_CANDIDATES.json'; report.parent.mkdir(parents=True,exist_ok=True); report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            imported=0
            if a.apply_discovery and result['candidates']:
                baseline=load_source_records(root/'config'/'sources.json')
                dynamic=load_dynamic_source_records(c)
                union=baseline + [x for x in dynamic if x['name'] not in {b['name'] for b in baseline}]
                existing_names={b['name'] for b in union}
                existing_hosts={__import__('urllib.parse').parse.urlparse(b['base_url']).hostname for b in union if b.get('base_url')}
                imported=0
                for x in result['candidates']:
                    host=__import__('urllib.parse').parse.urlparse(x['base_url']).hostname
                    if host in existing_hosts: continue
                    if x['name'] in existing_names: x['name']=f"{x['name']}_{host.replace('.','_')}"
                    union.append(x); existing_names.add(x['name']); existing_hosts.add(host); imported+=1
                sync_source_contracts(c,union)
                persist_source_endpoints(c,result['candidates'])
            print(json.dumps({'checked_catalogs':result['checked_catalogs'],'search_queries':result['search_queries'],'search_provider_available':result['search_provider_available'],'candidates':len(result['candidates']),'imported':imported,'errors':len(result['errors']),'report':str(report)},ensure_ascii=False,indent=2))
        elif a.command=='autonomous-discovery':
            from .paths import app_root
            from .source_discovery import SourceDiscoveryEngine, persist_discovery_evidence, persist_source_endpoints, persist_candidates
            from .discovery_intelligence import persist_intelligence, persist_community_signals
            from .source_search import WebSearchProvider
            from .source_verification import SourceVerificationEngine
            root=app_root()
            catalogs=json.loads((root/'config'/'discovery_catalogs.json').read_text(encoding='utf-8'))
            queries=json.loads((root/'config'/'discovery_queries.json').read_text(encoding='utf-8'))
            coverage=json.loads((root/'config'/'coverage_entities.json').read_text(encoding='utf-8')).get('entities',[])
            provider=WebSearchProvider(provider=a.search_provider,timeout=10)
            all_new=[]; cycle_reports=[]
            for cycle in range(1,max(1,min(a.max_cycles,10))+1):
                result=SourceDiscoveryEngine(catalogs,queries,provider,timeout=10,coverage_entities=coverage,state_path=root/'data'/'discovery_state.json').discover()
                persist_discovery_evidence(c,result); persist_candidates(c,result); persist_intelligence(c, result.get('query_observations',[]), result.get('query_observations',[])); persist_community_signals(c, result.get('query_observations',[])); persist_source_endpoints(c,result['candidates'])
                baseline=load_source_records(root/'config'/'sources.json'); dynamic=load_dynamic_source_records(c)
                union=baseline+[x for x in dynamic if x['name'] not in {b['name'] for b in baseline}]
                existing_names={b['name'] for b in union}; existing_hosts={__import__('urllib.parse').parse.urlparse(b['base_url']).hostname for b in union if b.get('base_url')}
                new_candidates=[]
                for x in result['candidates']:
                    host=__import__('urllib.parse').parse.urlparse(x['base_url']).hostname
                    if host in existing_hosts: continue
                    if x['name'] in existing_names: x['name']=f"{x['name']}_{host.replace('.','_')}"
                    union.append(x); existing_names.add(x['name']); existing_hosts.add(host); new_candidates.append(x)
                if new_candidates:
                    sync_source_contracts(c,union)
                    eng=SourceVerificationEngine(c,union,timeout=10,max_workers=12,max_policy_pages=4,search_provider=provider)
                    verification=eng.verify([x['name'] for x in new_candidates]); eng.persist(verification)
                else:
                    verification=[]
                cycle_reports.append({'cycle':cycle,'queries':result['search_queries'],'coverage_entities_queried':result['coverage_entities_queried'],'candidates':len(result['candidates']),'new_sources':len(new_candidates),'verified':len(verification),'blocked':sum(x.get('iran_eligibility')=='BLOCK' for x in verification),'live':sum(x.get('source_verification_state')=='LIVE_CONFIRMED' for x in verification),'errors':len(result['errors'])})
                all_new.extend(new_candidates)
                if not new_candidates: break
            out=root/'reports'/'AUTONOMOUS_DISCOVERY_CYCLE.json'; out.write_text(json.dumps({'version':__version__,'cycles':cycle_reports,'new_sources_total':len(all_new),'generated_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()},ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({'cycles':cycle_reports,'new_sources_total':len(all_new),'report':str(out)},ensure_ascii=False,indent=2))
        elif a.command=='verify-sources':
            from .runtime import MarketRadarRuntime
            from .paths import app_root
            records=load_source_records(app_root()/'config'/'sources.json')
            dynamic=load_dynamic_source_records(c)
            records=records+[x for x in dynamic if x['name'] not in {r['name'] for r in records}]
            sync_source_contracts(c,records)
            runtime=MarketRadarRuntime(c,records,None,http_timeout=10,settings=json.loads((app_root()/'config'/'settings.json').read_text(encoding='utf-8')))
            result=runtime.verify_source_policies()
            print(json.dumps({'checked':len(result),'blocked':sum(x.get('iran_eligibility')=='BLOCK' for x in result),'live':sum(x.get('source_verification_state')=='LIVE_CONFIRMED' for x in result),'execution_ready':sum(bool(x.get('execution_ready')) for x in result)},ensure_ascii=False,indent=2))
        elif a.command=='discovery-intelligence':
            from .discovery_intelligence import intelligence_snapshot
            print(json.dumps(intelligence_snapshot(c, limit=50), ensure_ascii=False, indent=2))
        elif a.command=='operational-gate':
            from .runtime import MarketRadarRuntime
            from .paths import app_root
            records=load_source_records(app_root()/'config'/'sources.json')
            dynamic=load_dynamic_source_records(c); records += [x for x in dynamic if x['name'] not in {r['name'] for r in records}]
            runtime=MarketRadarRuntime(c,records,None,http_timeout=10,settings=json.loads((app_root()/'config'/'settings.json').read_text(encoding='utf-8')))
            print(json.dumps(runtime.operational_gate(),ensure_ascii=False,indent=2))
        elif a.command=='submit-authorized':
            if not a.opportunity_id or not a.reason: raise SystemExit('--opportunity-id and --reason (comma-separated evidence ids) are required')
            from .runtime import MarketRadarRuntime
            from .paths import app_root
            records=load_source_records(app_root()/'config'/'sources.json'); dynamic=load_dynamic_source_records(c); records += [x for x in dynamic if x['name'] not in {r['name'] for r in records}]
            runtime=MarketRadarRuntime(c,records,None,http_timeout=10,settings=json.loads((app_root()/'config'/'settings.json').read_text(encoding='utf-8')))
            ids=[int(x) for x in a.reason.split(',') if x.strip()]
            print(json.dumps(runtime.submit_application_operational(a.opportunity_id,ids),ensure_ascii=False,indent=2))
        elif a.command=='record-delivery':
            if not a.opportunity_id or not a.reason: raise SystemExit('--opportunity-id and --reason (artifact path) are required')
            from .runtime import MarketRadarRuntime
            from .paths import app_root
            records=load_source_records(app_root()/'config'/'sources.json'); dynamic=load_dynamic_source_records(c); records += [x for x in dynamic if x['name'] not in {r['name'] for r in records}]
            runtime=MarketRadarRuntime(c,records,None,http_timeout=10,settings=json.loads((app_root()/'config'/'settings.json').read_text(encoding='utf-8')))
            print(json.dumps(runtime.record_delivery_operational(a.opportunity_id,a.reason),ensure_ascii=False,indent=2))
        elif a.command=='record-payment':
            if not a.opportunity_id or not a.amount or not a.currency or not a.reason: raise SystemExit('--opportunity-id --amount --currency --reason(payment ref) are required')
            from .runtime import MarketRadarRuntime
            from .paths import app_root
            records=load_source_records(app_root()/'config'/'sources.json'); dynamic=load_dynamic_source_records(c); records += [x for x in dynamic if x['name'] not in {r['name'] for r in records}]
            runtime=MarketRadarRuntime(c,records,None,http_timeout=10,settings=json.loads((app_root()/'config'/'settings.json').read_text(encoding='utf-8')))
            print(json.dumps(runtime.record_payment_operational(a.opportunity_id,a.amount,a.currency,a.reason),ensure_ascii=False,indent=2))
        elif a.command=='outcome-summary':
            from .outcome_learning import learning_summary
            print(json.dumps(learning_summary(c),ensure_ascii=False,indent=2))
        elif a.command=='record-outcome':
            if not a.opportunity_id or not a.outcome: raise SystemExit('--opportunity-id and --outcome are required')
            from .outcome_learning import record_outcome, update_learning_snapshot
            from .application import transition
            row=c.execute('SELECT state FROM opportunities WHERE id=?',(a.opportunity_id,)).fetchone()
            if not row: raise SystemExit('OPPORTUNITY_NOT_FOUND')
            if row['state'] != a.outcome.upper(): transition(c,a.opportunity_id,a.outcome.upper(),'cli',commit=False)
            result=record_outcome(c,a.opportunity_id,a.outcome,a.reason,a.amount,a.currency)
            result.update(update_learning_snapshot(c,a.opportunity_id)); c.commit(); print(json.dumps(result,ensure_ascii=False,indent=2))
        elif a.command=='source-audit':
            records=load_source_records(__import__('pathlib').Path(__file__).resolve().parents[1]/'config'/'sources.json'); report=audit_registry(records)
            print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False,indent=2))
            for r in report['results']:
                if not r.ok: print(r.name+': INVALID '+','.join(r.errors))
                elif r.warnings: print(r.name+': WARNING '+','.join(r.warnings))
            if report['invalid']:
                raise SystemExit(2)
        else:
            from .demo import seed
            from .pipeline import Pipeline
            if a.command=='demo': seed(c)
            print(json.dumps(Pipeline(c).daily_center(),ensure_ascii=False,indent=2))
    finally: c.close()
if __name__=='__main__': main()

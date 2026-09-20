from __future__ import annotations
import json, ast, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
errors=[]; warnings=[]

def require_file(rel):
    if not (ROOT/rel).exists(): errors.append('MISSING_FILE:'+rel)

def require_text(rel, needle):
    p=ROOT/rel
    if not p.exists(): errors.append('MISSING_FILE:'+rel); return
    if needle not in p.read_text(encoding='utf-8',errors='ignore'): errors.append(f'MISSING_CAPABILITY:{rel}:{needle}')

for rel in ['config/discovery_catalogs.json','config/coverage_targets.json','marketradar/source_verification.py','marketradar/source_discovery.py','tools/scheduled_cycle.py','marketradar/country_policy.py','marketradar/payment.py','marketradar/opportunity_intelligence.py','marketradar/resume.py','marketradar/proposal.py','marketradar/application_connectors.py','config/profile.example.json']:
    require_file(rel)
for rel,needle in [
 ('config/settings.json','\"Iran\"'),
 ('config/settings.json','\"Israel\"'),
 ('config/settings.json','\"scan_policy\": \"twice_daily_when_online\"'),
 ('marketradar/runtime.py','create_submission_plan'),
 ('marketradar/runtime.py','build_resume_and_proposal'),
 ('marketradar/runtime.py','analyze_opportunity'),
 ('marketradar/adapter_registry.py','telegram_bot_json'),
 ('marketradar/adapter_registry.py','html_jobs'),
 ('marketradar/source_parsers.py','parse_hh'),
 ('marketradar/source_parsers.py','parse_telegram_bot'),
 ('marketradar/db.py','CREATE TABLE IF NOT EXISTS tool_proposals'),
 ('marketradar/db.py','CREATE TABLE IF NOT EXISTS application_plans'),
 ('marketradar/runtime.py','market_intelligence'),
 ('marketradar/runtime.py','distribution_recommendation'),
 ('marketradar/market_intelligence.py','duplicate_groups'),
 ('marketradar/scheduler.py','ScanScheduler'),
 ('marketradar/social_connectors.py','CONTRACTS'),
 ('marketradar/source_discovery.py','discovery_candidates'),
 ('marketradar/source_verification.py','SourceVerificationEngine'),
 ('tools/scheduled_cycle.py','verify_source_policies'),
]: require_text(rel,needle)
settings=json.loads((ROOT/'config/settings.json').read_text())
sources=json.loads((ROOT/'config/sources.json').read_text())
black={x.lower() for x in settings.get('execution_blacklist_countries',[])}
if 'israel' not in black or 'iran' in black: errors.append('EXECUTION_BLACKLIST_MUST_EXCLUDE_USER_ORIGIN_IRAN')
regions={s.get('region') for s in sources if s.get('region') and s.get('region') not in {'Global','local'}}
countries={str(s.get('country','')).strip().lower() for s in sources}
required_regions={'Eastern Europe','Middle East','East Asia','Central Asia','Caucasus','Africa','Europe','Oceania','Latin America'}
for reg in required_regions:
    if reg.lower() not in {str(x).lower() for x in regions}: warnings.append('REGION_DISCOVERY_GAP:'+reg)
for country in ['russia','türkiye','uae','qatar','oman','bahrain','china','south korea','japan','taiwan','singapore','malaysia','australia','new zealand']:
    if country not in countries: warnings.append('COUNTRY_DISCOVERY_GAP:'+country)
families={s.get('source_family') for s in sources if s.get('source_family')}
if len(regions)<4: warnings.append('SOURCE_REGION_COVERAGE_LT_4')
if not {'telegram','reddit','x','linkedin'}.issubset(families): errors.append('PLATFORM_FAMILY_COVERAGE_INCOMPLETE')
coverage=json.loads((ROOT/'config/coverage_targets.json').read_text(encoding='utf-8'))
groups=coverage.get('groups',{})
for reg,target in coverage.get('regions',{}).items():
    aliases={str(x).strip().lower() for x in groups.get(reg,[reg])}
    count=sum(1 for s in sources if str(s.get('country','')).strip().lower() in aliases or str(s.get('region','')).strip().lower() in aliases)
    if count < target: warnings.append(f'COVERAGE_TARGET_GAP:{reg}:{count}/{target}')
if sum(1 for s in sources if s.get('source_family')=='bug_bounty') < coverage.get('minimum_bug_bounty_platforms',0): warnings.append('BUG_BOUNTY_DISCOVERY_TARGET_GAP')
if len(sources)<100: errors.append(f'REGISTERED_SOURCE_COVERAGE_LT_100:{len(sources)}')
lanes={s.get('policy_lane') for s in sources}
if 'GLOBAL_DISCOVERY' not in lanes: errors.append('GLOBAL_DISCOVERY_LANE_MISSING')
active_daily=[s for s in sources if s.get('status')=='active' and s.get('policy_lane')=='DAILY_PROJECT_SCAN']
if any(s.get('iran_status')!='ALLOW' for s in active_daily): errors.append('ACTIVE_DAILY_SOURCE_WITHOUT_IRAN_ALLOW')
if not active_daily: errors.append('NO_ACTIVE_IRAN_DAILY_SOURCES')
iran=sum(1 for s in sources if str(s.get('country','')).lower()=='iran')
if iran<10: errors.append(f'IRAN_SOURCE_COVERAGE_LT_10:{iran}')
bug=sum(1 for s in sources if s.get('source_role')=='bug_bounty')
free=sum(1 for s in sources if s.get('source_role') in {'freelance_marketplace','job_marketplace'})
if bug<10: errors.append(f'BUG_BOUNTY_COVERAGE_LT_10:{bug}')
if free<30: errors.append(f'FREELANCE_COVERAGE_LT_30:{free}')
required_social={'telegram','reddit','x','linkedin','instagram','bale','eitaa','soroush'}
if not required_social.issubset(families): errors.append('SOCIAL_FAMILY_COVERAGE_INCOMPLETE')
target=json.loads((ROOT/'config/source_targets.json').read_text())['target_registered_sources']
if len(sources)<target: warnings.append(f'SOURCE_TARGET_GAP:{len(sources)}/{target}')
print(json.dumps({'sources':len(sources),'regions':sorted(regions),'families':sorted(families),'target':target,'warnings':warnings,'errors':errors},ensure_ascii=False,indent=2))
sys.exit(2 if errors else 0)

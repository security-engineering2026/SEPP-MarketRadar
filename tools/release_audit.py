from __future__ import annotations
import json, re, sys
# Release-audit itself must not dirty the release tree with bytecode caches.
sys.dont_write_bytecode = True
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
errors=[]; warnings=[]
# Release hygiene
bad_names={'.pytest_cache','__pycache__'}
for p in ROOT.rglob('*'):
    if p.is_dir() and p.name in bad_names: errors.append(f'CACHE_DIR:{p.relative_to(ROOT)}')
    if p.is_file() and p.suffix in {'.pyc','.pyo','.db','.log'}: errors.append(f'GENERATED_FILE:{p.relative_to(ROOT)}')
# Source contract audit
from marketradar.source_registry import load_source_records
from marketradar.source_onboarding import audit_registry
records=load_source_records(ROOT/'config'/'sources.json'); report=audit_registry(records)
if report['invalid']: errors.append(f'SOURCE_INVALID:{report["invalid"]}')
active=[x for x in records if x.get('status')=='active']
if any(x.get('verification_state')=='unverified' for x in active): errors.append('ACTIVE_UNVERIFIED_SOURCE')
if any(x.get('policy_lane')=='DAILY_PROJECT_SCAN' and x.get('iran_status')!='ALLOW' for x in active): errors.append('ACTIVE_DAILY_SOURCE_WITHOUT_IRAN_ALLOW')
if any(x.get('policy_lane')=='DAILY_PROJECT_SCAN' and not x.get('daily_scan') for x in records): errors.append('DAILY_LANE_WITHOUT_DAILY_SCAN')
target=json.loads((ROOT/'config'/'source_targets.json').read_text(encoding='utf-8'))['target_registered_sources']
if target < 500: errors.append('REGISTRY_TARGET_INVALID')
if len(records) < 5: errors.append('TOO_FEW_ONBOARDED_SOURCES')
# Security static scan
patterns=[r'(?i)dev-secret',r'(?i)password\s*=\s*["\']',r'(?i)verify\s*=\s*false',r'\beval\s*\(',r'\bexec\s*\(',r'\bpickle\.',r'shell\s*=\s*True']
for p in ROOT.rglob('*.py'):
    if any(part in bad_names for part in p.parts) or p.name == 'release_audit.py': continue
    text=p.read_text(encoding='utf-8')
    for pat in patterns:
        if re.search(pat,text): errors.append(f'STATIC_SECURITY:{p.relative_to(ROOT)}:{pat}')
# Packaging consistency
version=re.search(r"__version__\s*=\s*['\"]([^'\"]+)", (ROOT/'marketradar'/'__init__.py').read_text()).group(1)
installer_text=(ROOT/'packaging'/'installer.iss').read_text()
match=re.search(r'#define\s+MyAppVersion\s+\"([^\"]+)\"', installer_text)
if not match or match.group(1) != version: errors.append('INSTALLER_VERSION_MISMATCH')
fed_text=(ROOT/'marketradar'/'federation.py').read_text(encoding='utf-8')
if f'SEPP-MarketRadar/{version}' not in fed_text: errors.append('USER_AGENT_VERSION_MISMATCH')
manifest=ROOT/'android-companion'/'app'/'src'/'main'/'AndroidManifest.xml'
activity=ROOT/'android-companion'/'app'/'src'/'main'/'java'/'com'/'sepp'/'marketradar'/'MainActivity.kt'
styles=ROOT/'android-companion'/'app'/'src'/'main'/'res'/'values'/'styles.xml'
for required in (manifest,activity,styles):
    if not required.exists(): errors.append(f'ANDROID_FILE_MISSING:{required.relative_to(ROOT)}')
gradle=(ROOT/'android-companion'/'app'/'build.gradle.kts').read_text(encoding='utf-8')
if f'versionName="{version}"' not in gradle: errors.append('ANDROID_VERSION_NAME_MISMATCH')
parts = version.split('.')
try:
    major, minor, patch = (int(x) for x in parts[:3])
    expected_code = major * 1000 + minor * 100 + patch * 10
except (ValueError, TypeError):
    expected_code = None
if expected_code is not None:
    code_match = re.search(r'\bversionCode\s*=\s*(\d+)\b', gradle)
    if not code_match or int(code_match.group(1)) != expected_code:
        errors.append(f'ANDROID_VERSION_CODE_MISMATCH:{expected_code}')
print(json.dumps({'version':version,'sources':len(records),'active':len(active),'invalid':report['invalid'],'warnings':report['warnings'],'errors':errors},ensure_ascii=False,indent=2))
sys.exit(1 if errors else 0)

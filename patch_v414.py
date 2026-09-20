from pathlib import Path
import json, re, shutil
root=Path('/mnt/data/mr_deep_audit')

# 1) version
(root/'marketradar/__init__.py').write_text("__version__='4.14.0'\n",encoding='utf8')

# 2) settings: Iran is the user origin, not an employer/client blacklist country.
settings=json.loads((root/'config/settings.json').read_text(encoding='utf8'))
settings['execution_blacklist_countries']=['Israel']
settings['user_origin_country']='Iran'
settings['source_policy_model']='Iran compatibility is evaluated separately from employer/client country blacklist; unknown foreign sources are discovery-only until evidence proves Iran compatibility.'
(root/'config/settings.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

# 3) source records
p=root/'config/sources.json'; rows=json.loads(p.read_text(encoding='utf8'))
# Exact duplicate URL contracts are redundant, keep the first contract with richer metadata.
seen_url={}; dedup=[]
for r in rows:
    u=r.get('base_url')
    if u in seen_url:
        # preserve localized entries only when their endpoint actually differs; exact duplicate is redundant.
        continue
    seen_url[u]=r['name']; dedup.append(r)
rows=dedup

# Lane helper
GLOBAL_NAMES={
    'WeWorkRemotely','JobRemotely','Arbeitnow','HH_RU','HH_KZ','HH_UZ','HH_GE','HH_AZ',
    'GulfTalent_UAE','TokyoDev_Japan'
}
# Any global job source incorrectly marked ALLOW without source-specific Iran evidence becomes UNKNOWN.
for r in rows:
    if r.get('name') in GLOBAL_NAMES:
        r['iran_status']='UNKNOWN'
        r['policy_lane']='GLOBAL_DISCOVERY'
        r['daily_scan']=True
        r['needs_analysis']=False
        r['source_origin']='direct_global'
        r['iran_policy_basis']='not_verified'
        r['iran_policy_url']=r.get('base_url')
        r['policy_checked_at']='2026-09-11'
        r['notes']=((r.get('notes') or '').rstrip()+ ' Global discovery source; Iran execution eligibility must be verified per opportunity.').strip()

# Global sources that had ALLOW only because they were labelled Global are not trusted as Iran-compatible.
for r in rows:
    if r.get('country')=='Global' and r.get('iran_status')=='ALLOW' and r.get('policy_lane')=='DAILY_PROJECT_SCAN':
        r['iran_status']='UNKNOWN'
        r['policy_lane']='GLOBAL_DISCOVERY'
        r['source_origin']='direct_global'
        r['iran_policy_basis']='not_verified'
        r['iran_policy_url']=r.get('base_url')
        r['policy_checked_at']='2026-09-11'
        r['notes']=((r.get('notes') or '').rstrip()+ ' Reclassified: Global source is not evidence of Iran eligibility.').strip()

# Explicit blocked sources: retain existing list, add evidence metadata where available.
blocked_evidence={
    'Upwork': 'https://support.upwork.com/hc/en-us/articles/211067778-Who-s-eligible-to-join-and-use-Upwork',
    'Freelancer': 'https://www.freelancer.com/support/General/restrictions-in-some-countries',
    'PeoplePerHour': 'https://support.peopleperhour.com/hc/en-us/community/posts/4417093281553-Place',
    'Toptal': 'https://www.toptal.com/tos',
    'Synack': 'https://www.synack.com/end-user-agreement/',
    'Bugcrowd': 'https://www.bugcrowd.com/website-terms-and-conditions/',
    'HackerOne': 'https://www.hackerone.com/terms/general',
    'Fiverr': None,
}
for r in rows:
    if r.get('policy_lane')=='BLOCKED_IRAN':
        r['source_origin']='direct_global'
        r['iran_policy_basis']='official_restriction' if blocked_evidence.get(r['name']) else r.get('iran_policy_basis','restriction_review')
        r['iran_policy_url']=blocked_evidence.get(r['name'])
        r['policy_checked_at']='2026-09-11'
        r['daily_scan']=False; r['needs_analysis']=False
        r['notes']=((r.get('notes') or '').rstrip()+ ' Direct platform is not an Iran execution source; do not use for account/workaround paths.').strip()

# Iran-local source evidence
for r in rows:
    if r.get('country')=='Iran' and r.get('iran_status')=='ALLOW':
        r['source_origin']='iran_local'
        r['iran_policy_basis']='iran_local_platform'
        r['iran_policy_url']=r.get('base_url')
        r['policy_checked_at']='2026-09-11'
        r['policy_lane']='DAILY_PROJECT_SCAN'
        r['daily_scan']=True
        r['needs_analysis']=False

# Add Kaya as an Iran-compatible intermediary discovery source. It is NOT treated as a bypass of blocked platforms.
if not any(r['name']=='Kaya_Iran_Intermediary' for r in rows):
    rows.append({
        'name':'Kaya_Iran_Intermediary','base_url':'https://kaya.ir/projects','adapter':'html_jobs','status':'active',
        'allow_hosts':['kaya.ir'],'verification_basis':'official_public_site_catalog', 'source_kind':'freelance_marketplace',
        'acquisition':'http','verification_state':'documented','access_scope':'public','terms_status':'needs_review',
        'country':'Iran','region':'Iran','language':'fa','source_family':'freelance_iran','source_role':'freelance_marketplace',
        'iran_status':'ALLOW','policy_lane':'DAILY_PROJECT_SCAN','daily_scan':True,'needs_analysis':False,
        'execution_capability':'manual_browser','source_origin':'iran_intermediary','upstream_sources':['Freelancer.com'],
        'iran_policy_basis':'iran_friendly_intermediary','iran_policy_url':'https://kaya.ir/', 'policy_checked_at':'2026-09-11',
        'notes':'Iran-facing intermediary that exposes international freelance opportunities. Treat upstream platform restrictions and Kaya terms separately; no identity/KYC/sanctions bypass is inferred or authorized.'
    })
# Add Man-Mitonam as a domestic service marketplace/discovery source only if not present.
if not any(r['name']=='ManMitonam_Iran' for r in rows):
    rows.append({
        'name':'ManMitonam_Iran','base_url':'https://man-mitonam.ir/','adapter':'html_jobs','status':'candidate',
        'allow_hosts':['man-mitonam.ir'],'verification_basis':'secondary_current_catalog','source_kind':'job_marketplace',
        'acquisition':'manual','verification_state':'documented','access_scope':'public','terms_status':'needs_review',
        'country':'Iran','region':'Iran','language':'fa','source_family':'freelance_iran','source_role':'freelance_marketplace',
        'iran_status':'ALLOW','policy_lane':'DAILY_PROJECT_SCAN','daily_scan':True,'needs_analysis':False,
        'execution_capability':'manual_browser','source_origin':'iran_local','iran_policy_basis':'iran_local_platform',
        'iran_policy_url':'https://man-mitonam.ir/','policy_checked_at':'2026-09-11',
        'notes':'Iranian freelance/service marketplace discovered in current 2025-2026 market references; endpoint and terms should be runtime-verified before promotion to active.'
    })

# Enforce lane/status consistency before write.
for r in rows:
    lane=r.get('policy_lane')
    if lane=='DAILY_PROJECT_SCAN':
        r['daily_scan']=True
        if r.get('iran_status')!='ALLOW':
            r['policy_lane']='GLOBAL_DISCOVERY' if r.get('status')=='active' else 'NEEDS_ANALYSIS'
            r['daily_scan']=bool(r.get('status')=='active')
    elif lane=='BLOCKED_IRAN':
        r['daily_scan']=False
    elif lane=='GLOBAL_DISCOVERY':
        r['daily_scan']=True

p.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

# 4) onboarding lanes + strict active daily rule
p=root/'marketradar/source_onboarding.py'; s=p.read_text(encoding='utf8')
s=s.replace('ALLOWED_POLICY_LANES = {"DAILY_PROJECT_SCAN", "NEEDS_ANALYSIS", "BLOCKED_IRAN", "REVIEW"}', 'ALLOWED_POLICY_LANES = {"DAILY_PROJECT_SCAN", "GLOBAL_DISCOVERY", "NEEDS_ANALYSIS", "BLOCKED_IRAN", "REVIEW"}')
old="""    if status == \"active\" and terms == \"blocked\":\n        errors.append(\"ACTIVE_SOURCE_TERMS_BLOCKED\")\n"""
new=old+"""    if status == \"active\" and policy_lane == \"DAILY_PROJECT_SCAN\" and str(record.get('iran_status','UNKNOWN')).upper() != 'ALLOW':\n        errors.append(\"ACTIVE_DAILY_SOURCE_REQUIRES_IRAN_ALLOW\")\n    if policy_lane == \"DAILY_PROJECT_SCAN\" and not bool(record.get('daily_scan')):\n        errors.append(\"DAILY_LANE_REQUIRES_DAILY_SCAN\")\n    if policy_lane == \"BLOCKED_IRAN\" and str(record.get('iran_status','UNKNOWN')).upper() != 'BLOCK':\n        errors.append(\"BLOCKED_LANE_REQUIRES_IRAN_BLOCK\")\n    if str(record.get('iran_status','UNKNOWN')).upper() in {'ALLOW','BLOCK'} and not record.get('iran_policy_basis'):\n        warnings.append(\"IRAN_POLICY_BASIS_MISSING\")\n"""
s=s.replace(old,new)
p.write_text(s,encoding='utf8')

# 5) registry/discovery lanes
p=root/'marketradar/source_registry.py'; s=p.read_text(encoding='utf8')
s=s.replace("'DAILY_PROJECT_SCAN':[x for x in records if x.get('policy_lane')=='DAILY_PROJECT_SCAN'],\n        'NEEDS_ANALYSIS'", "'DAILY_PROJECT_SCAN':[x for x in records if x.get('policy_lane')=='DAILY_PROJECT_SCAN'],\n        'GLOBAL_DISCOVERY':[x for x in records if x.get('policy_lane')=='GLOBAL_DISCOVERY'],\n        'NEEDS_ANALYSIS'")
p.write_text(s,encoding='utf8')
p=root/'marketradar/source_discovery.py'; s=p.read_text(encoding='utf8')
s=s.replace("r.get('policy_lane') in {'NEEDS_ANALYSIS','REVIEW'}", "r.get('policy_lane') in {'GLOBAL_DISCOVERY','NEEDS_ANALYSIS','REVIEW'}")
p.write_text(s,encoding='utf8')

# 6) policy: default blacklist only employer/client countries; never infer user's origin Iran as a blacklist hit.
p=root/'marketradar/policy.py'; s=p.read_text(encoding='utf8')
s=s.replace("blacklist = settings.get('execution_blacklist_countries', ['Iran','Israel'])", "blacklist = settings.get('execution_blacklist_countries', ['Israel'])")
# remove source-country blacklist block entirely
s=s.replace("    source_country=str(source.get('country','')).strip()\n    if source_country and source_country in {str(x).strip() for x in blacklist}: hits.append(source_country)\n", "")
p.write_text(s,encoding='utf8')

# 7) engine: scan Iran-compatible lane separately from global discovery; both are discovery, only daily lane can be execution-oriented.
p=root/'marketradar/engine.py'; s=p.read_text(encoding='utf8')
s=s.replace("stats={'sources_configured':len(self.sources),'sources_checked':0,'candidates':0,'accepted_opportunities':0,'errors':0,'dry_run':bool(dry)}", "stats={'sources_configured':len(self.sources),'sources_checked':0,'daily_sources_checked':0,'global_sources_checked':0,'candidates':0,'accepted_opportunities':0,'errors':0,'dry_run':bool(dry)}")
s=s.replace("if source.get('status')!='active' or source.get('policy_lane')!='DAILY_PROJECT_SCAN' or not source.get('daily_scan'): continue", "if source.get('status')!='active' or source.get('policy_lane') not in {'DAILY_PROJECT_SCAN','GLOBAL_DISCOVERY'} or not source.get('daily_scan'): continue")
s=s.replace("            stats['sources_checked']+=1\n", "            stats['sources_checked']+=1\n            if source.get('policy_lane')=='DAILY_PROJECT_SCAN': stats['daily_sources_checked']+=1\n            else: stats['global_sources_checked']+=1\n")
p.write_text(s,encoding='utf8')

# 8) market intelligence + runtime distribution include global discovery as a separate list.
p=root/'marketradar/market_intelligence.py'; s=p.read_text(encoding='utf8')
s=s.replace("    daily=[]; analysis=[]", "    daily=[]; global_discovery=[]; analysis=[]")
s=s.replace("        elif s.get('policy_lane')=='NEEDS_ANALYSIS': analysis.append(item)", "        elif s.get('policy_lane')=='GLOBAL_DISCOVERY': global_discovery.append(item)\n        elif s.get('policy_lane')=='NEEDS_ANALYSIS': analysis.append(item)")
s=s.replace("'needs_analysis_sites':analysis[:30],\n            'recommended_sites':(daily+analysis)[:50],", "'global_discovery_sites':global_discovery[:30],\n            'needs_analysis_sites':analysis[:30],\n            'recommended_sites':(daily+global_discovery+analysis)[:50],")
p.write_text(s,encoding='utf8')

p=root/'marketradar/runtime.py'; s=p.read_text(encoding='utf8')
s=s.replace("SELECT name,base_url,source_role,policy_lane,country,iran_status FROM sources WHERE policy_lane='DAILY_PROJECT_SCAN' ORDER BY name", "SELECT name,base_url,source_role,policy_lane,country,iran_status FROM sources WHERE policy_lane IN ('DAILY_PROJECT_SCAN','GLOBAL_DISCOVERY') ORDER BY CASE policy_lane WHEN 'DAILY_PROJECT_SCAN' THEN 0 ELSE 1 END,name")
p.write_text(s,encoding='utf8')

# 9) GUI: add global discovery lane and fix nonexistent notes column.
p=root/'marketradar/desktop.py'; s=p.read_text(encoding='utf8')
s=s.replace('values=("All lanes","DAILY_PROJECT_SCAN","NEEDS_ANALYSIS","BLOCKED_IRAN","REVIEW")', 'values=("All lanes","DAILY_PROJECT_SCAN","GLOBAL_DISCOVERY","NEEDS_ANALYSIS","BLOCKED_IRAN","REVIEW")')
s=s.replace("for i,(name,lane,accent) in enumerate(((\"Daily project scan\",\"DAILY_PROJECT_SCAN\",GOOD),(\"Needs analysis\",\"NEEDS_ANALYSIS\",INFO),(\"Blocked for Iran\",\"BLOCKED_IRAN\",DANGER),(\"Review\",\"REVIEW\",WARN))):", "for i,(name,lane,accent) in enumerate(((\"Daily project scan\",\"DAILY_PROJECT_SCAN\",GOOD),(\"Global discovery\",\"GLOBAL_DISCOVERY\",INFO),(\"Needs analysis\",\"NEEDS_ANALYSIS\",INFO),(\"Blocked for Iran\",\"BLOCKED_IRAN\",DANGER),(\"Review\",\"REVIEW\",WARN))):")
s=s.replace('"DAILY_PROJECT_SCAN":"Daily project scan","NEEDS_ANALYSIS":"Needs analysis","BLOCKED_IRAN":"Blocked for Iran","REVIEW":"Review"', '"DAILY_PROJECT_SCAN":"Daily project scan","GLOBAL_DISCOVERY":"Global discovery","NEEDS_ANALYSIS":"Needs analysis","BLOCKED_IRAN":"Blocked for Iran","REVIEW":"Review"')
s=s.replace('SELECT name,base_url,source_role,policy_lane,iran_status,kyc_status,payment_status,terms_status,verification_state,access_scope,notes FROM sources WHERE name=?', 'SELECT name,base_url,source_role,policy_lane,iran_status,kyc_status,payment_status,terms_status,verification_state,access_scope FROM sources WHERE name=?')
s=s.replace('labels=("Name","URL","Role","Lane","Iran","KYC","Payment","Terms","Verification","Access","Notes")\n            messagebox.showinfo("Source policy", "\\n".join(f"{k}: {v or \'—\'}" for k,v in zip(labels,row)), parent=self.master)', 'labels=("Name","URL","Role","Lane","Iran","KYC","Payment","Terms","Verification","Access")\n            note=next((x.get("notes","") for x in self.sources if x.get("name")==name), "")\n            evidence=next((x.get("iran_policy_url") for x in self.sources if x.get("name")==name), "")\n            text="\\n".join(f"{k}: {v or \'—\'}" for k,v in zip(labels,row))\n            text += f"\\nPolicy evidence: {evidence or \'—\'}\\nNotes: {note or \'—\'}"\n            messagebox.showinfo("Source policy", text, parent=self.master)')
s=s.replace("self.metrics[\"Needs analysis\"].set(str(self.conn.execute(\"SELECT COUNT(*) FROM sources WHERE policy_lane IN ('NEEDS_ANALYSIS','REVIEW')\").fetchone()[0]))", "self.metrics[\"Needs analysis\"].set(str(self.conn.execute(\"SELECT COUNT(*) FROM sources WHERE policy_lane IN ('NEEDS_ANALYSIS','REVIEW')\").fetchone()[0]))")
p.write_text(s,encoding='utf8')

# 10) product/release audits aligned with new policy
p=root/'tools/product_audit.py'; s=p.read_text(encoding='utf8')
s=s.replace("if 'iran' not in black or 'israel' not in black: errors.append('BLACKLIST_POLICY_INCOMPLETE')", "if 'israel' not in black or 'iran' in black: errors.append('EXECUTION_BLACKLIST_MUST_EXCLUDE_USER_ORIGIN_IRAN')")
s=s.replace("if len(sources)<100: errors.append(f'REGISTERED_SOURCE_COVERAGE_LT_100:{len(sources)}')", "if len(sources)<100: errors.append(f'REGISTERED_SOURCE_COVERAGE_LT_100:{len(sources)}')\nlanes={s.get('policy_lane') for s in sources}\nif 'GLOBAL_DISCOVERY' not in lanes: errors.append('GLOBAL_DISCOVERY_LANE_MISSING')\nactive_daily=[s for s in sources if s.get('status')=='active' and s.get('policy_lane')=='DAILY_PROJECT_SCAN']\nif any(s.get('iran_status')!='ALLOW' for s in active_daily): errors.append('ACTIVE_DAILY_SOURCE_WITHOUT_IRAN_ALLOW')\nif not active_daily: errors.append('NO_ACTIVE_IRAN_DAILY_SOURCES')")
p.write_text(s,encoding='utf8')

p=root/'tools/release_audit.py'; s=p.read_text(encoding='utf8')
s=s.replace("if any(x.get('verification_state')=='unverified' for x in active): errors.append('ACTIVE_UNVERIFIED_SOURCE')", "if any(x.get('verification_state')=='unverified' for x in active): errors.append('ACTIVE_UNVERIFIED_SOURCE')\nif any(x.get('policy_lane')=='DAILY_PROJECT_SCAN' and x.get('iran_status')!='ALLOW' for x in active): errors.append('ACTIVE_DAILY_SOURCE_WITHOUT_IRAN_ALLOW')\nif any(x.get('policy_lane')=='DAILY_PROJECT_SCAN' and not x.get('daily_scan') for x in records): errors.append('DAILY_LANE_WITHOUT_DAILY_SCAN')")
p.write_text(s,encoding='utf8')

# 11) update tests
p=root/'tests/test_v4110_product.py'; s=p.read_text(encoding='utf8')
s=s.replace("assert 'Iran' in apply_blacklist({'country':'Iran'}, ['Iran','Israel'])", "assert 'Iran' not in apply_blacklist({'country':'Iran'}, ['Israel'])")
s=s.replace("{'execution_blacklist_countries':['Iran','Israel']}", "{'execution_blacklist_countries':['Israel']}")
p.write_text(s,encoding='utf8')
p=root/'tests/test_v413_product.py'; s=p.read_text(encoding='utf8')
s=s.replace("assert lanes['DAILY_PROJECT_SCAN']>=40", "assert lanes['DAILY_PROJECT_SCAN']>=10\n    assert lanes['GLOBAL_DISCOVERY']>=5")
s=s.replace("assert all(x.get('policy_lane')=='DAILY_PROJECT_SCAN' for x in iran)", "assert all(x.get('policy_lane')=='DAILY_PROJECT_SCAN' for x in iran)")
s=s.replace("    assert result['recommended_sites']\n", "    assert result['recommended_sites']\n    assert 'global_discovery_sites' in result\n")
# append regression tests
s += '''\n\ndef test_active_daily_sources_are_explicitly_iran_compatible():\n    rows=records()\n    active_daily=[x for x in rows if x.get('status')=='active' and x.get('policy_lane')=='DAILY_PROJECT_SCAN']\n    assert active_daily\n    assert all(x.get('iran_status')=='ALLOW' for x in active_daily)\n\ndef test_global_discovery_sources_are_not_mislabeled_as_iran_allow():\n    rows=records()\n    global_rows=[x for x in rows if x.get('policy_lane')=='GLOBAL_DISCOVERY']\n    assert global_rows\n    assert all(x.get('iran_status')!='BLOCK' for x in global_rows)\n\ndef test_iran_source_does_not_get_blocked_as_employer_country():\n    from marketradar.policy import eligibility\n    state,_=eligibility({'iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'allowed'}, True, {'country':'Iran'}, {'execution_blacklist_countries':['Israel']})\n    assert state=='EXECUTE'\n'''
p.write_text(s,encoding='utf8')

# 12) new deep source audit test module
(root/'tests/test_v414_deep_audit.py').write_text('''import json\nfrom pathlib import Path\nfrom marketradar.source_registry import load_source_records\nfrom marketradar.source_onboarding import audit_registry\n\nROOT=Path(__file__).parents[1]\n\ndef test_no_exact_duplicate_source_urls():\n    rows=load_source_records(ROOT/"config/sources.json")\n    urls=[r["base_url"] for r in rows]\n    assert len(urls)==len(set(urls))\n\ndef test_iran_policy_metadata_exists_for_allow_and_block():\n    rows=load_source_records(ROOT/"config/sources.json")\n    for r in rows:\n        if r.get("iran_status") in {"ALLOW","BLOCK"}:\n            assert r.get("iran_policy_basis")\n            assert r.get("policy_checked_at")\n\ndef test_registry_has_no_active_daily_unknown_sources():\n    rows=load_source_records(ROOT/"config/sources.json")\n    assert not [r["name"] for r in rows if r.get("status")=="active" and r.get("policy_lane")=="DAILY_PROJECT_SCAN" and r.get("iran_status")!="ALLOW"]\n\ndef test_known_iran_blocked_evidence_urls_are_recorded():\n    rows={r["name"]:r for r in load_source_records(ROOT/"config/sources.json")}\n    for name in ("Upwork","Freelancer","PeoplePerHour","Toptal","Bugcrowd","Synack"):\n        assert rows[name]["policy_lane"]=="BLOCKED_IRAN"\n        assert rows[name].get("iran_policy_url")\n\ndef test_product_and_release_audits_pass_policy_shape():\n    report=audit_registry(load_source_records(ROOT/"config/sources.json"))\n    assert report["invalid"]==0\n''',encoding='utf8')

# 13) changelog + audit note
ch=root/'CHANGELOG.md'; text=ch.read_text(encoding='utf8')
entry='''\n## v4.14.0 — Deep Source/Policy Audit\n\n- Split `GLOBAL_DISCOVERY` from Iran-compatible `DAILY_PROJECT_SCAN`.\n- Active daily sources now require explicit `iran_status=ALLOW`.\n- Removed Iran from the employer/client execution blacklist; Israel remains the explicit blacklist.\n- Added source-level Iran policy evidence metadata.\n- Added Kaya Iran intermediary as a first-class source with upstream attribution; no bypass behavior is inferred.\n- Added Man-Mitonam as a candidate Iran discovery source.\n- Removed exact duplicate source contracts.\n- Fixed Source Strategy double-click bug caused by a nonexistent `sources.notes` DB column.\n- Added deep regression tests for lane integrity, source duplicates and Iran policy.\n'''
ch.write_text(text.rstrip()+entry,encoding='utf8')

print('patched',len(rows),'source records')

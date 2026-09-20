from __future__ import annotations
import re
from collections import Counter
from urllib.parse import urlsplit

TOKEN_RE = re.compile(r"[a-z0-9]{3,}", re.I)
DISTRIBUTION = {
    'web_scraping': ['freelance marketplaces', 'automation/data-engineering marketplaces', 'direct client channels'],
    'data_cleaning': ['data/analytics freelance marketplaces', 'spreadsheet automation communities', 'direct B2B outreach'],
    'excel_automation': ['spreadsheet/automation freelance marketplaces', 'business automation marketplaces', 'direct B2B outreach'],
    'python_debugging': ['software development freelance marketplaces', 'programming help marketplaces', 'direct client channels'],
    'api_integration': ['API/integration freelance marketplaces', 'software development marketplaces', 'direct B2B outreach'],
    'telegram_automation': ['Telegram automation communities', 'automation freelance marketplaces', 'direct clients with authorized Telegram integrations'],
    'business_automation': ['business automation marketplaces', 'SMB/B2B direct outreach', 'workflow automation communities'],
    'data_pipeline': ['data engineering marketplaces', 'analytics freelance marketplaces', 'direct B2B outreach'],
    'android': ['Android/mobile freelance marketplaces', 'software development marketplaces', 'direct app clients'],
    'security': ['authorized security consulting/bug-bounty platforms', 'security engineering marketplaces', 'direct authorized clients'],
    'general_software': ['software development marketplaces', 'direct client channels'],
}

def _tokens(text):
    return set(TOKEN_RE.findall(str(text or '').lower()))

def duplicate_groups(rows, threshold=0.72):
    """Return clusters of likely repeated opportunities using title/description token similarity.
    This is deliberately conservative: it does not delete or merge records automatically.
    """
    items=[dict(r) for r in rows]
    groups=[]; used=set()
    for i,a in enumerate(items):
        if i in used: continue
        ta=_tokens(a.get('title','')+' '+a.get('description',''))
        if not ta: continue
        group=[a]
        for j in range(i+1,len(items)):
            if j in used: continue
            b=items[j]; tb=_tokens(b.get('title','')+' '+b.get('description',''))
            union=ta|tb
            sim=(len(ta&tb)/len(union)) if union else 0
            if sim>=threshold:
                group.append(b); used.add(j)
        if len(group)>1:
            used.add(i); groups.append(group)
    return groups

def market_snapshot(rows):
    items=[dict(r) for r in rows]
    categories=Counter(str(x.get('category') or 'general_software') for x in items)
    payments=Counter(str(x.get('payment') or 'UNKNOWN') for x in items)
    countries=Counter(str(x.get('country') or 'UNKNOWN') for x in items)
    budgets=[float(x['budget']) for x in items if isinstance(x.get('budget'),(int,float)) and x.get('budget') is not None]
    return {
        'opportunities':len(items), 'categories':categories.most_common(), 'payments':payments.most_common(),
        'countries':countries.most_common(), 'budget_count':len(budgets),
        'budget_min':min(budgets) if budgets else None, 'budget_max':max(budgets) if budgets else None,
        'budget_avg':round(sum(budgets)/len(budgets),2) if budgets else None,
        'duplicate_groups':len(duplicate_groups(items)),
    }

def competition_snapshot(rows):
    items=[dict(r) for r in rows]
    by_source=Counter(str(x.get('source') or 'UNKNOWN') for x in items)
    return {'source_distribution':by_source.most_common(), 'unique_sources':len(by_source), 'opportunities':len(items)}

def distribution_targets(tool_category, source_records=()):
    daily=[]; global_discovery=[]; analysis=[]
    for s in source_records:
        if not isinstance(s,dict): continue
        item={'name':s.get('name'),'url':s.get('base_url'),'role':s.get('source_role','project_marketplace'),'country':s.get('country'),'iran_status':s.get('iran_status','UNKNOWN'),'lane':s.get('policy_lane','REVIEW')}
        if s.get('policy_lane')=='DAILY_PROJECT_SCAN': daily.append(item)
        elif s.get('policy_lane')=='GLOBAL_DISCOVERY': global_discovery.append(item)
        elif s.get('policy_lane')=='NEEDS_ANALYSIS': analysis.append(item)
    return {'category':tool_category,
            'recommended_channels':DISTRIBUTION.get(tool_category,DISTRIBUTION['general_software']),
            'daily_project_sites':daily[:30],
            'global_discovery_sites':global_discovery[:30],
            'needs_analysis_sites':analysis[:30],
            'recommended_sites':(daily+global_discovery+analysis)[:50],
            'rule':'Recommendations are based on registered source contracts and policy lanes; actual submission still requires user permission and platform authorization.'}

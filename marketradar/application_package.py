from __future__ import annotations
from .opportunity_intelligence import analyze_need
from .resume import tailored_resume
from .proposal import generate_proposal

def language_for(opportunity, default='en'):
    v=(opportunity or {}).get('language') or (opportunity or {}).get('source_language') or default
    return str(v).lower().split('-')[0]

def build_application_package(profile, opportunity, language=None, target_amount=None, target_currency=None):
    lang=language or language_for(opportunity)
    p=dict(profile or {}); need=analyze_need(opportunity)
    missing=[]
    for key in ('name','skills'):
        if not p.get(key): missing.append(key)
    if target_amount is None and opportunity.get('budget') is None: missing.append('target_amount')
    if target_currency is None and not opportunity.get('currency'): missing.append('target_currency')
    resume=tailored_resume(p,opportunity,language=lang)
    proposal=generate_proposal(p,opportunity,language=lang,target_amount=target_amount,target_currency=target_currency)
    return {'language':lang,'required_inputs':['name','skills','portfolio','target_amount','target_currency'],'missing_inputs':missing,'task_understanding':need,'resume':resume,'proposal':proposal,'portfolio_references':p.get('portfolio') or p.get('projects') or []}

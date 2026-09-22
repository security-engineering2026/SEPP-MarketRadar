POLICY_VERSION = 'policy.v1'

from __future__ import annotations
from .country_policy import apply_blacklist, evaluate_iran_access, jurisdiction_hits

def eligibility(source, evidence_ok=True, opportunity=None, settings=None):
    """Deterministic action policy. Discovery is broader than execution."""
    opportunity = opportunity or {}
    settings = settings or {}
    blacklist = settings.get('execution_blacklist_countries', ['Israel'])
    # Hard source/compliance blocks always dominate uncertainty.
    if str(source.get('terms_status','not_reviewed')).lower() == 'blocked':
        return 'BLOCK', ['source terms explicitly blocked']
    if str(source.get('kyc_status','UNKNOWN')).upper() == 'BLOCK':
        return 'BLOCK', ['KYC incompatible']
    if str(source.get('iran_status','UNKNOWN')).upper() == 'BLOCK':
        return 'BLOCK', ['source blocks Iran']
    hits = apply_blacklist(opportunity, blacklist)
    hits.extend(jurisdiction_hits(opportunity, source, blacklist))
    source_country=str(source.get('country','')).strip()
    if source_country and source_country in {str(x).strip() for x in blacklist}: hits.append(source_country)
    hits=list(dict.fromkeys(hits))
    if hits:
        return 'BLOCK', ['blocked operational jurisdiction: '+', '.join(dict.fromkeys(hits))]
    # A verified source-level ALLOW is sufficient when the opportunity itself does not carry contradictory location evidence.
    if str(source.get('iran_status','UNKNOWN')).upper() == 'ALLOW' and str(opportunity.get('iran_access','UNKNOWN')).upper() in {'','UNKNOWN','N/A'}:
        iran_access, iran_reasons = 'ALLOW', ['verified source-level Iran access']
    else:
        iran_access, iran_reasons = evaluate_iran_access(opportunity, source, blacklist)
    if iran_access == 'BLOCK':
        return 'BLOCK', iran_reasons
    if not evidence_ok:
        return 'UNKNOWN', ['insufficient evidence']
    if iran_access != 'ALLOW':
        return 'UNKNOWN', iran_reasons
    if str(source.get('kyc_status','UNKNOWN')).upper() != 'ALLOW':
        return 'REVIEW', ['KYC not fully verified']
    if source.get('payment_status') not in {'USDT','USDC','IRR/local','EVIDENCE'}:
        return 'REVIEW', ['payment path not verified']
    if str(source.get('terms_status','not_reviewed')).lower() not in {'reviewed','allowed','n/a'}:
        return 'REVIEW', ['source terms not reviewed']
    return 'EXECUTE', ['Iran access, KYC, payment and source terms verified']

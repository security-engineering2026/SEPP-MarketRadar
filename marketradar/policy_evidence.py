from __future__ import annotations
import re

NEGATED = re.compile(r'\b(?:not|no|without|never|isn\'t|is not|isnt)\b', re.I)
KYC_TERMS = re.compile(r'\b(?:kyc|know your customer|identity verification|government[- ]issued (?:id|document)|passport|national id)\b|احراز\s+هویت|کارت\s+ملی|پاسپورت', re.I)
REQUIRED_TERMS = re.compile(r'\b(?:required|mandatory|must|need(?:ed)?|necessary)\b|الزام|لازم', re.I)
ALLOW_TERMS = re.compile(r'\b(?:welcome|supported|eligible|available|allowed)\b|مجاز|پشتیبانی|در دسترس', re.I)
BLOCK_TERMS = re.compile(r'\b(?:not supported|unsupported|restricted|prohibited|not available|not permitted|cannot participate|sanctioned|embargoed|cannot (?:use|register|access))\b|ممنوع|پشتیبانی نمی.?شود|در دسترس نیست|تحریم', re.I)

def sentences(text: str):
    return [x.strip() for x in re.split(r'(?<=[.!?。！？])\s+|\n+', str(text or '')) if x.strip()]

def _scope(s):
    low=s.lower()
    if any(x in low for x in ('registration','register','signup','sign up','ثبت نام')): return 'registration'
    if any(x in low for x in ('application','apply','proposal','درخواست')): return 'application'
    if any(x in low for x in ('payout','withdraw','withdrawal','payment','settlement','پرداخت','برداشت')): return 'payout'
    return 'general'

def aggregate_kyc(text: str) -> dict:
    findings=[]
    for s in sentences(text):
        if not KYC_TERMS.search(s): continue
        scope=_scope(s)
        neg=bool(NEGATED.search(s))
        required=bool(REQUIRED_TERMS.search(s)) and not neg
        not_required=neg or bool(re.search(r'\b(?:no kyc|without kyc)\b|بدون\s+احراز',s,re.I))
        status='REQUIRED' if required else 'NOT_REQUIRED' if not_required else 'UNKNOWN'
        findings.append({'status':status,'scope':scope,'sentence':s})
    if not findings: return {'status':'UNKNOWN','scope':'general','findings':[],'conflict':False}
    statuses={x['status'] for x in findings}
    if len(statuses)==1: return {'status':next(iter(statuses)),'scope':findings[0]['scope'],'findings':findings,'conflict':False}
    return {'status':'UNKNOWN','scope':'mixed','findings':findings,'conflict':True}

def iran_policy_claims(text: str) -> dict:
    findings=[]
    for s in sentences(text):
        if not re.search(r'\biran(?:ian)?\b|ایران|ایرانی|иран|иранск|iranlı', s, re.I): continue
        if BLOCK_TERMS.search(s): findings.append({'status':'BLOCK','sentence':s})
        elif ALLOW_TERMS.search(s): findings.append({'status':'ALLOW','sentence':s})
    statuses={x['status'] for x in findings}
    return {'status': next(iter(statuses)) if len(statuses)==1 else 'UNKNOWN','findings':findings,'conflict':len(statuses)>1}

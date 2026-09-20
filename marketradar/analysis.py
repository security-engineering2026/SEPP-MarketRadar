import re
CATS={'web_scraping':['scraping','scraper','crawler','data extraction'],'data_cleaning':['data cleaning','deduplicate','normalize data','data validation','csv','excel'],'excel_automation':['excel','spreadsheet','google sheets'],'python_debugging':['python bug','debug python','fix python','traceback'],'api_integration':['api integration','rest api','webhook','fastapi'],'telegram_automation':['telegram bot','telegram automation'],'business_automation':['business automation','workflow automation'],'data_pipeline':['etl','data pipeline'],'android':['android','kotlin','apk','mobile app'],'security':['pentest','vulnerability','malware','yara','security audit','android security']}
def classify(text):
 t=(text or '').lower(); h={k:sum(w in t for w in v) for k,v in CATS.items()}; b=max(h,key=h.get); return b if h[b] else 'general_software'
def payment_hint(text):
 t=(text or '').lower()
 if re.search(r'\busdt\b',t): return 'USDT'
 if re.search(r'\busdc\b',t): return 'USDC'
 if re.search(r'\birr\b|تومان',t): return 'IRR/local'
 if re.search(r'\busd\b|\$|\beur\b|€|\bgbp\b|£|\binr\b|₹',t): return 'FIAT/UNKNOWN'
 return 'UNKNOWN'
def budget(text):
    t=text or ''
    m=re.search(r'\b(USD|USDT|USDC|EUR|GBP|INR|IRR)\s*([\d,]+(?:\.\d+)?)',t,re.I)
    if m: return float(m.group(2).replace(',','')),m.group(1).upper()
    m=re.search(r'([\d,]+(?:\.\d+)?)\s*(USD|USDT|USDC|EUR|GBP|INR|IRR)\b',t,re.I)
    if m: return float(m.group(1).replace(',','')),m.group(2).upper()
    m=re.search(r'([$€£₹])\s*([\d,]+(?:\.\d+)?)',t)
    if m: return float(m.group(2).replace(',','')),m.group(1)
    return None,None

def _g(x,k): return x.get(k) if isinstance(x,dict) else getattr(x,k)
def ttm(x):
 if _g(x,'budget') is None:return 0
 effort=2; t=_g(x,'description').lower()
 if any(a in t for a in ['complex','large','dashboard','multiple files','database']): effort+=6
 if any(a in t for a in ['simple','small','minor bug','quick fix']): effort=max(1,effort-1)
 award=.5 if _g(x,'evidence_confidence')>=.85 else .25; pay=.95 if _g(x,'payment') in {'USDT','USDC','IRR/local'} else .55; elig={'EXECUTE':1,'REVIEW':.6,'UNKNOWN':.25,'BLOCK':0}.get(_g(x,'eligibility'),0); return round(_g(x,'budget')*award*pay*elig/effort,2)
time_to_money=ttm
def score(x):
 quality=_g(x,'quality_score') if _g(x,'quality_score') is not None else _g(x,'evidence_confidence')
 s=quality*30+_g(x,'evidence_confidence')*10+{'EXECUTE':35,'REVIEW':15,'UNKNOWN':0,'BLOCK':-100}.get(_g(x,'eligibility'),0)+{'USDT':15,'USDC':15,'IRR/local':15,'FIAT/UNKNOWN':4,'UNKNOWN':0}.get(_g(x,'payment'),0)+(10 if _g(x,'budget') is not None else 0)+min(10,_g(x,'time_to_money')/50); return max(0,min(100,round(s,2)))


def opportunity_type(item):
    text=' '.join(str(item.get(k,'')) for k in ('title','description','category','source_family','source')).lower()
    if any(x in text for x in ('bug bounty','vulnerability disclosure','security program','responsible disclosure')): return 'BUG_BOUNTY'
    if any(x in text for x in ('request for proposal','rfp','procurement','tender','bid invitation','purchase request')): return 'PROCUREMENT'
    if any(x in text for x in ('i need someone','need someone to','looking for someone','seeking someone','need a developer','who can build')): return 'DIRECT_INTENT'
    if any(x in text for x in ('agency','intermediary','staffing')): return 'AGENCY'
    if any(x in text for x in ('community','forum','reddit','telegram','linkedin','x.com','social media')): return 'SOCIAL_INTENT'
    if any(x in text for x in ('job board','job opening','career','employment','full-time','part-time')): return 'JOB'
    return 'OPPORTUNITY'

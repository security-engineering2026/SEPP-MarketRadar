from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

_DATE_PATTERNS = [
    re.compile(r'\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b'),
    re.compile(r'\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b'),
]
_PROPOSAL_PATTERNS = [
    re.compile(r'\b(\d+)\s*\+?\s*(?:proposals?|bids?|applicants?|applications?)\b', re.I),
    re.compile(r'\b(?:proposals?|bids?|applicants?|applications?)\s*[:=]?\s*(\d+)\b', re.I),
]

def _text(item):
    return ' '.join(str(item.get(k) or '') for k in ('title','description','client','client_name','reputation','competition','deadline')).strip()

def _parse_dt(year, month, day):
    try:
        return datetime(int(year), int(month), int(day), 23, 59, tzinfo=timezone.utc)
    except ValueError:
        return None

def extract_deadline(item, now=None):
    now = now or datetime.now(timezone.utc)
    explicit = item.get('deadline_at') or item.get('deadline')
    if isinstance(explicit, str):
        try:
            dt=datetime.fromisoformat(explicit.replace('Z','+00:00'))
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            return {'deadline_at':dt.astimezone(timezone.utc).isoformat(),'deadline_confidence':0.98,'deadline_source':'field'}
        except ValueError:
            pass
    t=_text(item).lower()
    if re.search(r'\btoday\b',t):
        dt=now.replace(hour=23,minute=59,second=59,microsecond=0)
        return {'deadline_at':dt.isoformat(),'deadline_confidence':0.80,'deadline_source':'relative_text'}
    if re.search(r'\btomorrow\b',t):
        dt=(now+timedelta(days=1)).replace(hour=23,minute=59,second=59,microsecond=0)
        return {'deadline_at':dt.isoformat(),'deadline_confidence':0.80,'deadline_source':'relative_text'}
    m=re.search(r'\b(?:in|within)\s+(\d{1,3})\s+days?\b',t)
    if m:
        dt=now+timedelta(days=int(m.group(1)))
        return {'deadline_at':dt.isoformat(),'deadline_confidence':0.76,'deadline_source':'relative_text'}
    for p in _DATE_PATTERNS:
        m=p.search(t)
        if not m: continue
        groups=m.groups(); dt=_parse_dt(*groups) if len(groups)==3 and groups[0].startswith('20') else _parse_dt(groups[2],groups[1],groups[0])
        if dt: return {'deadline_at':dt.isoformat(),'deadline_confidence':0.90,'deadline_source':'date_text'}
    return {'deadline_at':None,'deadline_confidence':0.0,'deadline_source':None}

def extract_proposal_count(item):
    for key in ('proposal_count','proposals','bids','applicants','application_count'):
        value=item.get(key)
        if isinstance(value,(int,float)) and not isinstance(value,bool) and value >= 0:
            return {'proposal_count':int(value),'proposal_count_confidence':0.98,'proposal_count_source':'field'}
    text=_text(item)
    for p in _PROPOSAL_PATTERNS:
        m=p.search(text)
        if m: return {'proposal_count':int(m.group(1)),'proposal_count_confidence':0.82,'proposal_count_source':'text'}
    return {'proposal_count':None,'proposal_count_confidence':0.0,'proposal_count_source':None}

def extract_client_reputation(item):
    rating=item.get('client_rating', item.get('rating'))
    reviews=item.get('client_reviews', item.get('reviews'))
    hire=item.get('hire_rate')
    spent=item.get('client_spend', item.get('total_spend'))
    verified=item.get('payment_verified')
    text=_text(item).lower()
    def num(x):
        try:return float(x)
        except (TypeError,ValueError):return None
    rating= num(rating); reviews=num(reviews); hire=num(hire); spent=num(spent)
    if rating is None:
        m=re.search(r'\b(\d(?:\.\d)?)\s*/\s*5\b',text)
        if m: rating=float(m.group(1))
    if reviews is None:
        m=re.search(r'\b(\d+)\s+(?:reviews?|ratings?)\b',text)
        if m: reviews=float(m.group(1))
    components=[]
    if rating is not None: components.append(min(1,max(0,rating/5)))
    if reviews is not None: components.append(min(1,max(0.15,1-(1/(reviews+1)))))
    if hire is not None: components.append(min(1,max(0,hire/100 if hire>1 else hire)))
    if spent is not None: components.append(min(1,max(0.1,1-(1/(spent/1000+1)))))
    if verified is True: components.append(1.0)
    score=round(sum(components)/len(components),3) if components else 0.45
    return {'client_reputation_score':score,'client_rating':rating,'client_reviews':int(reviews) if reviews is not None else None,'hire_rate':hire,'client_spend':spent,'client_payment_verified':bool(verified) if verified is not None else None,'client_reputation_confidence':round(min(1.0,0.35+0.12*len(components)),3)}

def competition_intelligence(item, proposal_count=None):
    p=proposal_count
    if p is None:
        raw=item.get('proposal_count')
        p=int(raw) if isinstance(raw,(int,float)) and raw>=0 else None
    if p is None: score=0.55
    elif p <= 3: score=0.95
    elif p <= 10: score=0.82
    elif p <= 25: score=0.65
    elif p <= 50: score=0.48
    elif p <= 100: score=0.30
    else: score=0.15
    t=_text(item).lower()
    urgency=0.10 if any(x in t for x in ('urgent','asap','immediately','today')) else 0
    return {'competition_score':round(min(1,score+urgency),3),'competition_pressure':round(1-score,3),'proposal_count':p}

def extract_signals(item, now=None):
    d=extract_deadline(item,now); p=extract_proposal_count(item); r=extract_client_reputation(item); c=competition_intelligence(item,p['proposal_count'])
    deadline_at=d['deadline_at']
    urgency=0.45
    if deadline_at:
        try:
            days=(datetime.fromisoformat(deadline_at)- (now or datetime.now(timezone.utc))).total_seconds()/86400
            urgency=1.0 if days<=1 else 0.85 if days<=3 else 0.70 if days<=7 else 0.50 if days<=30 else 0.30
        except ValueError: pass
    return {**d,**p,**r,**c,'deadline_urgency':round(urgency,3)}

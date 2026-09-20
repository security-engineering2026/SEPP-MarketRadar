from __future__ import annotations
import re
from urllib.parse import urlparse

ALIASES = {
    'iran':'Iran','iranian':'Iran','ایران':'Iran','ir':'Iran',
    'israel':'Israel','israeli':'Israel','اسرائیل':'Israel','اسرائيل':'Israel',
    'russia':'Russia','russian':'Russia','روسیه':'Russia',
    'united arab emirates':'United Arab Emirates','uae':'United Arab Emirates','emirates':'United Arab Emirates','امارات':'United Arab Emirates',
    'saudi arabia':'Saudi Arabia','ksa':'Saudi Arabia','عربستان':'Saudi Arabia',
    'qatar':'Qatar','قطر':'Qatar','kuwait':'Kuwait','کویت':'Kuwait','bahrain':'Bahrain','بحرین':'Bahrain',
    'oman':'Oman','عمان':'Oman','jordan':'Jordan','اردن':'Jordan','egypt':'Egypt','مصر':'Egypt',
    'japan':'Japan','ژاپن':'Japan','south korea':'South Korea','korea':'South Korea','کره جنوبی':'South Korea',
    'china':'China','چین':'China','taiwan':'Taiwan','تایوان':'Taiwan','india':'India','هند':'India',
    'turkey':'Türkiye','türkiye':'Türkiye','ترکیه':'Türkiye',
}

def normalize_country(value):
    if not isinstance(value, str): return None
    key = re.sub(r'\s+', ' ', value.strip().lower())
    return ALIASES.get(key, value.strip() if value.strip() else None)

def countries_from_text(text):
    t = str(text or '').lower()
    found=[]
    for key, value in sorted(ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True):
        if re.search(r'(?<!\w)'+re.escape(key)+r'(?!\w)', t):
            if value not in found: found.append(value)
    return found

def infer_country(item):
    """Infer an employer/client/location country conservatively.
    A country mentioned only in an eligibility exclusion (e.g. 'worldwide except Iran')
    is not treated as the opportunity's country.
    """
    for key in ('country','client_country','employer_country','location_country'):
        c=normalize_country(item.get(key)) if isinstance(item,dict) else None
        if c: return c
    loc = item.get('location') if isinstance(item,dict) else None
    if isinstance(loc, dict):
        c=normalize_country(loc.get('country'))
        if c:return c
    loc_text=' '.join(str(item.get(k,'')) for k in ('location','title')) if isinstance(item,dict) else ''
    direct=countries_from_text(loc_text)
    if len(direct)==1: return direct[0]
    desc=str(item.get('description','')) if isinstance(item,dict) else ''
    for country in set(ALIASES.values()):
        c=country.lower()
        positive=(rf'\b(?:based|located|employer|client|company|office|team)\s+(?:in|at)\s+{re.escape(c)}\b',
                  rf'\bfrom\s+{re.escape(c)}\b', rf'\b{re.escape(c)}\s+(?:based|office|company|employer)\b')
        if any(re.search(p,desc.lower()) for p in positive): return country
    return None

def evaluate_iran_access(item, source, blacklist=None):
    blacklist = {normalize_country(x) for x in (blacklist or []) if normalize_country(x)}
    explicit = str(item.get('iran_access','')).upper() if isinstance(item,dict) else ''
    if explicit in {'ALLOW','BLOCK','UNKNOWN'}: return explicit, ['explicit opportunity Iran access']
    source_status = str(source.get('iran_status','UNKNOWN')).upper()
    if source_status in {'ALLOW','BLOCK'}: return source_status, ['source policy']
    text=' '.join(str(item.get(k,'')) for k in ('title','description','location','eligible_countries','work_authorization')) if isinstance(item,dict) else ''
    if 'iran' in text.lower() or 'ایران' in text:
        if any(x in text.lower() for x in ('not available in iran','unavailable in iran','iran excluded','iran residents not eligible','iranian residents not eligible')):
            return 'BLOCK',['opportunity explicitly excludes Iran']
        if any(x in text.lower() for x in ('available in iran','iran accepted','iran residents welcome','iranian applicants welcome')):
            return 'ALLOW',['opportunity explicitly accepts Iran']
    if 'worldwide' in text.lower() or 'global' in text.lower() or 'anywhere' in text.lower():
        return 'UNKNOWN',['worldwide wording does not prove payment/service eligibility from Iran']
    return 'UNKNOWN',['Iran access not explicitly verified']

JURISDICTION_FIELDS = (
    'country','client_country','employer_country','location_country','registration_country',
    'legal_entity_country','hosting_country','ip_country','domain_country','jurisdiction_country'
)

def jurisdiction_hits(item, source=None, blocked=None):
    """Return operational-jurisdiction hits only.

    This deliberately does not infer a person's nationality, ethnicity, religion,
    or ownership nationality. It uses explicit business/location metadata and
    domain jurisdiction signals that can be independently evidenced.
    """
    item = item if isinstance(item, dict) else {}
    source = source if isinstance(source, dict) else {}
    blocked = {normalize_country(x) for x in (blocked or []) if normalize_country(x)}
    values=[]
    for obj in (item, source):
        for key in JURISDICTION_FIELDS:
            value=normalize_country(obj.get(key))
            if value and value not in values: values.append(value)
        url=obj.get('base_url') or obj.get('url')
        if url:
            try:
                host=(urlparse(str(url)).hostname or '').lower().rstrip('.')
                if host.endswith('.il') or host.endswith('.co.il'):
                    if 'Israel' not in values: values.append('Israel')
            except ValueError:
                pass
    return [x for x in values if x in blocked]

def apply_blacklist(item, blacklist):
    """Return blacklist hits only from location-bearing evidence, never arbitrary mentions.
    A word appearing in a description is not sufficient to classify the client/employer country.
    """
    item = item if isinstance(item,dict) else {}
    countries=[]
    for key in ('country','client_country','employer_country','location_country'):
        c=normalize_country(item.get(key))
        if c and c not in countries: countries.append(c)
    loc=item.get('location')
    if isinstance(loc,dict):
        c=normalize_country(loc.get('country'))
        if c and c not in countries: countries.append(c)
    loc_text=' '.join(str(item.get(k,'')) for k in ('location','title'))
    for c in countries_from_text(loc_text):
        if c not in countries: countries.append(c)
    desc=str(item.get('description',''))
    for country in set(ALIASES.values()):
        c=country.lower()
        patterns=(
            rf'\b(?:client|employer|company|team|office|headquarters|hq)\s+(?:is|based|located)\s+(?:in|at)\s+{re.escape(c)}\b',
            rf'\b(?:based|located|headquartered)\s+in\s+{re.escape(c)}\b',
            rf'\bfrom\s+{re.escape(c)}\b',
        )
        if any(re.search(p,desc.lower()) for p in patterns) and country not in countries:
            countries.append(country)
    blocked={normalize_country(x) for x in blacklist if normalize_country(x)}
    return [c for c in countries if c in blocked]

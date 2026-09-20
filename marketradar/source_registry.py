from __future__ import annotations
import json
from urllib.parse import urlparse
from .federation import Source
from .source_onboarding import validate_source
from .source_identity import identity_from_record, same_source


def load_source_records(path):
    with open(path, encoding='utf-8') as f: data=json.load(f)
    if not isinstance(data,list): raise ValueError('SOURCE_REGISTRY_INVALID')
    out=[]; names=set()
    for x in data:
        result=validate_source(x)
        if not result.ok: raise ValueError(result.errors[0])
        if x['name'] in names: raise ValueError('DUPLICATE_SOURCE')
        names.add(x['name']); out.append(dict(x))
    return out


def load_sources(path):
    return [Source(x['name'],x['base_url'],x.get('adapter','json'),x.get('status','candidate'),tuple(x.get('allow_hosts',[])),x.get('access_scope','public')) for x in load_source_records(path)]

def source_lanes(records):
    lanes = {
        'EXECUTION_ELIGIBLE': [],
        'MARKET_INTELLIGENCE_ONLY': [],
        'BLACKLIST_ARCHIVE': [],
        'REVIEW': [],
        # Legacy lanes retained as read-only compatibility buckets.
        'DAILY_PROJECT_SCAN': [], 'GLOBAL_DISCOVERY': [], 'NEEDS_ANALYSIS': [], 'BLOCKED_IRAN': [],
    }
    for x in records:
        lane=str(x.get('policy_lane') or x.get('source_lane') or 'REVIEW')
        canonical={'DAILY_PROJECT_SCAN':'EXECUTION_ELIGIBLE','BLOCKED_IRAN':'MARKET_INTELLIGENCE_ONLY','GLOBAL_DISCOVERY':'MARKET_INTELLIGENCE_ONLY','NEEDS_ANALYSIS':'MARKET_INTELLIGENCE_ONLY'}.get(lane,lane)
        lanes.setdefault(canonical,[]).append(x)
    return lanes


def dedupe_source_records(records):
    """Canonicalize identity without treating regional variants as duplicates."""
    unique=[]; duplicates=[]
    enriched=[]
    for record in records:
        r=dict(record); r.update(identity_from_record(r)); enriched.append(r)
    for record in enriched:
        match=None; evidence=None
        for existing in unique:
            same,ev=same_source(existing,record)
            if same:
                match=existing; evidence=ev; break
        if match:
            dup=dict(record); dup['duplicate_of']=match['name']; dup['duplicate_evidence']=evidence or {}
            duplicates.append(dup)
        else:
            unique.append(record)
    return unique, duplicates

from __future__ import annotations
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse


def normalize_host(url: str) -> str:
    try: return (urlparse(str(url or '')).hostname or '').lower().rstrip('.')
    except ValueError: return ''

def normalize_text(value: str) -> str:
    return re.sub(r'[^a-z0-9]+',' ',str(value or '').lower()).strip()

def identity_from_record(record: dict) -> dict:
    host=normalize_host(record.get('base_url'))
    return {'canonical_host':host,'organization':normalize_text(record.get('organization') or record.get('owner') or record.get('company')),'brand':normalize_text(record.get('brand') or record.get('name')),'platform':normalize_text(record.get('platform') or record.get('source_platform')),'endpoint':normalize_text(record.get('endpoint') or record.get('base_url')),'regional_variant':normalize_text(record.get('regional_variant') or record.get('country') or record.get('region'))}

def semantic_similarity(a: dict,b: dict) -> float:
    fields=('organization','brand','platform','endpoint')
    vals=[]
    for f in fields:
        av=normalize_text(a.get(f,'')); bv=normalize_text(b.get(f,''))
        if av and bv: vals.append(SequenceMatcher(None,av,bv).ratio())
    return sum(vals)/len(vals) if vals else 0.0

def same_source(a: dict,b: dict, threshold=.88) -> tuple[bool, dict]:
    ia,ib=identity_from_record(a),identity_from_record(b)
    ah,bh=ia['canonical_host'],ib['canonical_host']
    regional = ia['regional_variant'] and ib['regional_variant'] and ia['regional_variant'] != ib['regional_variant']
    evidence={'host_match':bool(ah and ah==bh),'semantic_similarity':semantic_similarity(ia,ib),'regional_variant_preserved':bool(regional)}
    if regional: return False,evidence
    same=evidence['host_match'] or evidence['semantic_similarity']>=threshold
    return same,evidence

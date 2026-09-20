from __future__ import annotations
import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_KEYS = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","fbclid","gclid","ref","ref_src"}
BAD_SCHEMES = {"javascript", "data", "file"}

def canonical_url(url: str) -> str:
    if not isinstance(url, str): raise ValueError("URL_INVALID")
    url = url.strip()
    if len(url) > 4096: raise ValueError("URL_TOO_LONG")
    p = urlsplit(url)
    if p.scheme.lower() not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("URL_INVALID")
    host = p.hostname.lower().rstrip(".")
    port = p.port
    host_for_netloc = f'[{host}]' if ':' in host and not host.startswith('[') else host
    netloc = host_for_netloc
    if port and not ((p.scheme.lower() == "http" and port == 80) or (p.scheme.lower() == "https" and port == 443)):
        netloc = f"{host_for_netloc}:{port}"
    path = p.path or "/"
    if len(path) > 2048: raise ValueError("URL_TOO_LONG")
    query = [(k,v) for k,v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in TRACKING_KEYS]
    return urlunsplit((p.scheme.lower(), netloc, path, urlencode(sorted(query)), ""))

def text_quality(title: str, description: str) -> float:
    t = re.sub(r"\s+", " ", title or "").strip()
    d = re.sub(r"\s+", " ", description or "").strip()
    score = 0.0
    if 3 <= len(t) <= 240: score += 0.45
    if 20 <= len(d) <= 10000: score += 0.30
    if len(t.split()) >= 2: score += 0.10
    if len(d.split()) >= 8: score += 0.10
    if "http://" in t or "https://" in t: score -= 0.15
    return max(0.0, min(1.0, round(score, 3)))

def item_quality(item: dict, evidence_confidence: float) -> float:
    tq = text_quality(item.get("title", ""), item.get("description", ""))
    ec = max(0.0, min(1.0, float(evidence_confidence)))
    return round(0.55 * ec + 0.45 * tq, 3)

def fingerprint(item: dict) -> str:
    value = "|".join(str(item.get(k,"")).strip().lower() for k in ("title","description","url"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

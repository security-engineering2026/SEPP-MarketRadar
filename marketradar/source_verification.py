from __future__ import annotations
import json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin, urlparse

from .federation import Federation, Source
from .source_search import WebSearchProvider, SearchProviderError
from .source_constraints import extract_source_constraints, support_question_for_source
from .source_policy import classify_source_lane, BLACKLIST_LANE, EXECUTION_LANE, INTELLIGENCE_LANE, REVIEW_LANE
from .policy_evidence import aggregate_kyc, iran_policy_claims
from .capability import advance_capability, capability_evidence_for_verification

# Strong, source-level signals only. Absence of a match never proves eligibility.
IRAN_BLOCK_PATTERNS = [
    re.compile(r"(?:not\s+(?:available|supported|permitted)|unavailable|unsupported|prohibited|restricted|cannot\s+(?:use|register|access)|do\s+not\s+support).{0,180}\biran(?:ian)?\b", re.I | re.S),
    re.compile(r"\biran(?:ian)?\b.{0,180}(?:not\s+(?:available|supported|permitted)|unavailable|unsupported|prohibited|restricted|cannot\s+(?:use|register|access))", re.I | re.S),
    re.compile(r"\biran\b.{0,220}\b(?:OFAC|sanction|embargo)\w*\b", re.I | re.S),
    re.compile(r"(?:ایران|ایرانی).{0,160}(?:مجاز نیست|ممنوع|پشتیبانی نمی.?شود|در دسترس نیست|قابل استفاده نیست|تحریم)", re.I | re.S),
    re.compile(r"(?:мусульман|иран|иранские|иранцев).{0,160}(?:запрещ|недоступ|не поддерж|санкц)", re.I | re.S),
    re.compile(r"(?:iran|iranlı).{0,160}(?:yasak|desteklenmiyor|kullanılamaz|mevcut değil|yaptırım)", re.I | re.S),
]
IRAN_ALLOW_PATTERNS = [
    re.compile(r"\biran(?:ian)?\b.{0,120}(?:welcome|supported|eligible|available|allowed)\b", re.I | re.S),
    re.compile(r"(?:welcome|supported|eligible|available|allowed).{0,120}\biran(?:ian)?\b", re.I | re.S),
    re.compile(r"(?:ایران|ایرانی).{0,120}(?:مجاز|پشتیبانی|فعال|در دسترس|قابل استفاده)", re.I | re.S),
    re.compile(r"(?:iran|iranlı).{0,120}(?:desteklenir|uygun|kullanılabilir|mevcut)", re.I | re.S),
]
KYC_REQUIRED = re.compile(r"(?:\bkyc|\bknow\s+your\s+customer|\bidentity\s+verification|\bverify\s+(?:your|identity)|\bgovernment[- ]issued\s+(?:id|document)|\bpassport|\bnational\s+id|احراز\s+هویت|کارت\s+ملی|پاسپورت)", re.I)
KYC_NOT_REQUIRED = re.compile(r"(?:\bno\s+kyc|\bkyc\s+(?:not|isn't|is\s+not)\s+required|\bwithout\s+kyc|\bno\s+identity\s+verification|بدون\s+احراز\s+هویت|نیاز(?:ی|)\s+به\s+احراز\s+هویت\s+نیست)", re.I)
CRYPTO = {
    'BTC': re.compile(r"\bbitcoin\b|\bbtc\b", re.I),
    'ETH': re.compile(r"\beth(?:ereum)?\b", re.I),
    'USDT': re.compile(r"\busdt\b|tether", re.I),
    'USDC': re.compile(r"\busdc\b|usd\s*coin", re.I),
    'TRX': re.compile(r"\btrx\b|tron", re.I),
    'DAI': re.compile(r"\bdai\b", re.I),
}
PAYOUT_TERMS = re.compile(r"\b(?:payout|withdraw|withdrawal|payment|paid|pay|earnings|settlement|transfer)\b", re.I)
TERMS_HINTS = re.compile(r"\b(?:terms(?:\s+of\s+service)?|legal|policy|eligibility|acceptable\s+use|user\s+agreement|conditions)\b", re.I)


def _html_text(body: bytes) -> str:
    text = body.decode('utf-8', errors='ignore')
    text = re.sub(r'<script\b[^>]*>.*?</script>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<style\b[^>]*>.*?</style>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', unescape(text)).strip()


def _links(body: bytes, base_url: str) -> list[str]:
    raw = body.decode('utf-8', errors='ignore')
    found = []
    for href in re.findall(r'''(?:href|src)\s*=\s*["']([^"']+)["']''', raw, flags=re.I):
        if not href or href.startswith(('#', 'mailto:', 'javascript:')):
            continue
        url = urljoin(base_url, href)
        low = url.lower()
        if any(k in low for k in ('term', 'legal', 'policy', 'kyc', 'payment', 'payout', 'withdraw', 'faq', 'eligib')):
            if url not in found:
                found.append(url)
        if len(found) >= 8:
            break
    return found


def _surface_links(body: bytes, base_url: str, max_links: int = 80) -> list[str]:
    raw = body.decode('utf-8', errors='ignore')
    base_host=(urlparse(base_url).hostname or '').lower()
    out=[]
    for href in re.findall(r'''(?:href|src)\s*=\s*[\"']([^\"']+)''', raw, flags=re.I):
        if not href or href.startswith(('#','mailto:','javascript:','tel:')): continue
        u=urljoin(base_url,href); pu=urlparse(u)
        if pu.scheme not in {'http','https'} or (pu.hostname or '').lower()!=base_host: continue
        clean=u.split('#',1)[0]
        if clean not in out: out.append(clean)
        if len(out)>=max_links: break
    return out

def _evidence_windows(text: str, patterns: list[re.Pattern]) -> list[str]:
    out=[]
    for p in patterns:
        m=p.search(text)
        if m:
            start=max(0,m.start()-180); end=min(len(text),m.end()+180)
            out.append(text[start:end])
    return out[:4]


def classify_content(text: str, url: str, link_urls: list[str]) -> dict:
    iran_claim=iran_policy_claims(text)
    kyc_claim=aggregate_kyc(text)
    crypto=[name for name, pat in CRYPTO.items() if pat.search(text)]
    payment=[]
    if crypto: payment.extend(crypto)
    if PAYOUT_TERMS.search(text): payment.append('FIAT_OR_PLATFORM_PAYOUT')
    if 'bank transfer' in text.lower() or 'wire transfer' in text.lower(): payment.append('BANK_TRANSFER')
    if 'paypal' in text.lower(): payment.append('PAYPAL')
    if 'payoneer' in text.lower(): payment.append('PAYONEER')
    payment=list(dict.fromkeys(payment))
    verified_links=list(dict.fromkeys(link_urls))
    terms=[u for u in verified_links if TERMS_HINTS.search(u)]
    payout=[u for u in verified_links if re.search(r'payout|withdraw|payment|pay',u,re.I)]
    kyc_links=[u for u in verified_links if re.search(r'kyc|identity|verification',u,re.I)]
    confidence=0.55
    if iran_claim['status'] != 'UNKNOWN': confidence += 0.30
    if kyc_claim['status'] != 'UNKNOWN': confidence += 0.05
    if payment: confidence += 0.05
    if terms: confidence += 0.05
    return {
        'iran_eligibility': iran_claim['status'],
        'iran_findings': iran_claim['findings'],
        'iran_policy_conflict': iran_claim['conflict'],
        'kyc_requirement': kyc_claim['status'],
        'kyc_scope': kyc_claim['scope'],
        'kyc_findings': kyc_claim['findings'],
        'kyc_conflict': kyc_claim['conflict'],
        'payment_capabilities': payment,
        'terms_evidence_url': terms[0] if terms else None,
        'payout_evidence_url': payout[0] if payout else (url if PAYOUT_TERMS.search(text) else None),
        'kyc_evidence_url': kyc_links[0] if kyc_links else (url if kyc_claim['status'] != 'UNKNOWN' else None),
        'verified_terms_urls': terms,
        'evidence_confidence': round(min(confidence,0.99),2),
        'evidence_urls': list(dict.fromkeys([url] + terms[:2] + payout[:2] + kyc_links[:2])),
    }

class SourceVerificationEngine:
    """Automatic source-policy monitor.

    Discovery remains permissive; execution promotion is strict. The engine only
    auto-blocks when it sees explicit source-level Iran restriction evidence.
    It never infers ALLOW or "no KYC" from silence.
    """
    def __init__(self, connection, source_records, timeout=10, max_workers=12, max_policy_pages=2, search_provider=None, policy_search_interval_days=7, surface_scan_pages=24):
        self.c=connection
        self.records={r['name']:r for r in source_records}
        sources=[Source(r['name'],r['base_url'],r.get('adapter','json'),r.get('status','candidate'),tuple(r.get('allow_hosts',[])),r.get('access_scope','public'),tuple((r.get('headers') or {}).items())) for r in source_records]
        self.http=Federation(sources, timeout=timeout, max_workers=max_workers)
        self.max_workers=max(1,min(max_workers,24)); self.max_policy_pages=max(1,min(max_policy_pages,8)); self.surface_scan_pages=max(1,min(int(surface_scan_pages),64)); self.search=search_provider or WebSearchProvider(timeout=timeout); self.policy_search_interval_days=max(1,int(policy_search_interval_days))

    def _policy_search(self, r, text, links):
        """Use a search API only as an evidence locator; final classification still
        requires fetching the actual source/policy page. This closes the blind spot
        where a source homepage omits sanctions/KYC terms that live on another page.
        """
        if not self.search.available(): return [], []
        if r.get('iran_eligibility') not in (None, '', 'UNKNOWN'): return [], []
        host=urlparse(r.get('base_url','')).hostname or ''
        if not host: return [], []
        found=[]; snippets=[]
        for query in (f'site:{host} Iran sanctions terms eligibility', f'site:{host} Iran KYC payout payment'):
            try:
                results=self.search.search(query,5)
            except SearchProviderError:
                continue
            for item in results:
                u=item.get('url')
                if u and urlparse(u).hostname and urlparse(u).hostname.lower().endswith(host.lower()) and u not in found:
                    found.append(u); snippets.append(item.get('snippet',''))
                if len(found)>=4: break
            if len(found)>=4: break
        return found, snippets

    def _one(self, name):
        r=self.records[name]
        try:
            obs=self.http.fetch(name)
            text=_html_text(obs['body'])
            links=_links(obs['body'],obs['url'])
            search_links, search_snippets = self._policy_search(r, text, links)
            links = list(dict.fromkeys(links + search_links))
            # Multi-endpoint source model: retain endpoint roles instead of assuming
            # the homepage is the whole policy surface. This is especially important
            # for forums/platforms where Terms, KYC, payout and eligibility live apart.
            endpoint_rows=[]
            for link in links[:12]:
                low=link.lower()
                kind='policy'
                if any(k in low for k in ('term','legal','agreement')): kind='terms'
                elif any(k in low for k in ('kyc','identity','verification')): kind='kyc'
                elif any(k in low for k in ('pay','payout','withdraw','billing')): kind='payout'
                elif any(k in low for k in ('api','developer','docs')): kind='api'
                elif any(k in low for k in ('forum','community','discussion','thread')): kind='community'
                endpoint_rows.append((link,kind))
            pages=[]
            queue=list(dict.fromkeys([u for u in _surface_links(obs['body'], obs['url'], 40)] + [u for u,_ in endpoint_rows[:self.max_policy_pages + 4]]))[:self.surface_scan_pages]
            seen=set(queue); fetched=0
            # Public internal surfaces are crawled shallowly so account limits, subscriptions, application rules, payout pages and terms are not missed merely because they are not linked from a policy page.
            while queue and fetched < self.surface_scan_pages:
                link=queue.pop(0)
                try:
                    child=self.http.fetch(name, link); fetched += 1
                    child_text=_html_text(child['body']); pages.append((child['url'], child_text))
                    for nxt in _surface_links(child['body'], child['url'], 40):
                        if nxt not in seen and len(seen) < self.surface_scan_pages*4:
                            seen.add(nxt); queue.append(nxt)
                except Exception:
                    continue
            # Search-engine snippets are discovery hints, not authoritative policy
            # evidence. Classification must be based only on content fetched from the
            # source's own pages. This prevents a stale/incorrect search snippet from
            # falsely blocking Iran eligibility or changing KYC/payment state.
            combined=text + ' ' + ' '.join(t for _,t in pages)
            verified_page_urls=[u for u,_ in pages]
            result=classify_content(combined,obs['url'],verified_page_urls)
            evidence_urls=list(dict.fromkeys(result.get('evidence_urls',[]) + search_links + [u for u,_ in pages]))
            result['evidence_urls']=evidence_urls
            constraints=extract_source_constraints(combined,evidence_urls)
            result['source_constraints']=constraints
            result.update({'source':name,'http_status':obs['status'],'bytes':obs['bytes'],'sha256':obs['sha256'],'last_verified_at':datetime.now(timezone.utc).isoformat(),'source_verification_state':'LIVE_CONFIRMED'})
            blocked_countries = self.records.get(name, {}).get('execution_blacklist_countries') or ['Israel']
            classification = classify_source_lane(r, result, blocked_countries)
            result['source_lane'] = classification.lane
            result['source_lane_label_fa'] = classification.lane_label_fa
            result['execution_ready'] = classification.execution_ready
            result['policy_lane'] = 'BLOCKED_IRAN' if result.get('iran_eligibility') == 'BLOCK' else classification.lane
            result['status'] = 'active' if (r.get('status') != 'disabled' and classification.lane != BLACKLIST_LANE) else ('disabled' if r.get('status') == 'disabled' else 'candidate')
            result['terms_status'] = 'reviewed' if result.get('terms_evidence_url') else r.get('terms_status','needs_review')
            result['review_reason'] = classification.reason if classification.lane == REVIEW_LANE else None
            result['blacklist_reason'] = classification.reason if classification.blacklisted else None
            result['blacklisted_at'] = result.get('last_verified_at') if classification.blacklisted else None
            result['project_scan_interval_minutes'] = classification.interval_minutes if classification.lane == EXECUTION_LANE else 0
            result['intelligence_scan_interval_minutes'] = classification.interval_minutes if classification.lane == INTELLIGENCE_LANE else 0
            result['verification_state'] = 'blocked' if classification.blacklisted else ('verified' if result.get('source_verification_state')=='LIVE_CONFIRMED' else 'documented')
            current_maturity = str(r.get('capability_maturity') or 'REGISTERED')
            execution_evidence = bool(
                result.get('source_verification_state') == 'LIVE_CONFIRMED'
                and classification.execution_ready
                and result.get('terms_status') == 'reviewed'
                and bool(result.get('evidence_urls'))
                and bool(r.get('execution_capability') in {'authorized_api', 'authorized_integration'})
            )
            capability_evidence = capability_evidence_for_verification(
                reachable=result.get('source_verification_state') == 'LIVE_CONFIRMED',
                parseable=bool(text.strip()),
                validated=bool(text.strip()) and bool(constraints is not None),
                policy_verified=bool(result.get('source_verification_state') == 'LIVE_CONFIRMED' and classification.lane in {EXECUTION_LANE, INTELLIGENCE_LANE, REVIEW_LANE}),
                execution_ready=execution_evidence,
            )
            result['capability_maturity'] = advance_capability(current_maturity, capability_evidence)
            result['capability_evidence'] = list(dict.fromkeys(result.get('evidence_urls', [])[:12] + list(capability_evidence.reasons)))
            try:
                result['stale_at'] = (datetime.now(timezone.utc) + __import__('datetime').timedelta(days=self.policy_search_interval_days)).isoformat()
            except Exception:
                result['stale_at'] = None
            result['support_question']=support_question_for_source(r.get('country'),result['iran_eligibility'],result['kyc_requirement'],constraints)
            return result
        except Exception as exc:
            return {'source':name,'source_verification_state':'DEAD','status':'candidate','iran_eligibility':'UNKNOWN','kyc_requirement':'UNKNOWN','payment_capabilities':[], 'payout_evidence_url':None,'kyc_evidence_url':None,'terms_evidence_url':None,'evidence_confidence':0.0,'evidence_urls':[],'execution_ready':False,'policy_lane':r.get('policy_lane','REVIEW'),'verification_state':'degraded','terms_status':r.get('terms_status','needs_review'),'error':type(exc).__name__+': '+str(exc),'last_verified_at':datetime.now(timezone.utc).isoformat()}

    def verify(self, names=None, progress_callback=None, stop_event=None):
        selected=list(names) if names is not None else list(self.records)
        results=[]
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures={pool.submit(self._one,n):n for n in selected if n in self.records}
            for f in as_completed(futures):
                if stop_event and stop_event.is_set():
                    for p in futures:
                        if not p.done(): p.cancel()
                    break
                result=f.result(); results.append(result)
                if progress_callback: progress_callback(result)
        results.sort(key=lambda x:x['source'])
        return results

    def persist(self, results):
        now=datetime.now(timezone.utc).isoformat()
        for x in results:
            for item in x.get('source_constraints',[]):
                self.c.execute('''INSERT INTO source_constraints(source,constraint_key,value_int,value_text,confidence,evidence_url,checked_at,status)
                                  VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source,constraint_key) DO UPDATE SET value_int=excluded.value_int,value_text=excluded.value_text,confidence=excluded.confidence,evidence_url=excluded.evidence_url,checked_at=excluded.checked_at,status=excluded.status''',
                               (x['source'],item.get('key'),item.get('value_int'),item.get('value_text'),float(item.get('confidence',0) or 0),item.get('evidence_url'),item.get('checked_at',now),'CONFIRMED'))
            limits={i.get('key'):i for i in x.get('source_constraints',[]) if i.get('key') in {'max_open_projects','max_pending_applications'}}
            if limits:
                open_item=limits.get('max_open_projects'); pending_item=limits.get('max_pending_applications')
                reason='; '.join(str(i.get('value_text') or '') for i in limits.values())[:800]
                self.c.execute('''INSERT INTO source_application_limits(source,max_open_projects,max_pending_applications,reason,evidence_url,checked_at)
                    VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET max_open_projects=excluded.max_open_projects,max_pending_applications=excluded.max_pending_applications,reason=excluded.reason,evidence_url=excluded.evidence_url,checked_at=excluded.checked_at''',
                    (x['source'],open_item.get('value_int') if open_item else None,pending_item.get('value_int') if pending_item else None,reason,(open_item or pending_item or {}).get('evidence_url'),x.get('last_verified_at',now)))
            if x.get('review_reason') and x.get('source_verification_state')=='LIVE_CONFIRMED':
                self.c.execute('''INSERT INTO source_review_queue(source,reason,question,created_at,status,evidence_url) VALUES(?,?,?,?,?,?)
                                  ON CONFLICT(source) DO UPDATE SET reason=excluded.reason,question=excluded.question,status='OPEN',evidence_url=excluded.evidence_url''',
                               (x['source'],x['review_reason'],x.get('support_question'),x.get('last_verified_at',now),'OPEN',(x.get('evidence_urls') or [None])[0]))
            self.c.execute("UPDATE source_review_queue SET status='RESOLVED',resolved_at=?,resolution='AUTOMATIC_POLICY_VERIFICATION' WHERE source=? AND status='OPEN' AND ?=1",(x.get('last_verified_at',now),x['source'],int(bool(x.get('execution_ready')))))
            endpoint_urls=list(dict.fromkeys([u for u in ([x.get('base_url')] + x.get('evidence_urls',[])) if u]))
            for endpoint_url in endpoint_urls:
                low=endpoint_url.lower(); kind='policy'
                if endpoint_url.rstrip('/').lower()==str(self.records.get(x['source'],{}).get('base_url','')).rstrip('/').lower(): kind='home'
                elif any(k in low for k in ('term','legal','agreement')): kind='terms'
                elif any(k in low for k in ('kyc','identity','verification')): kind='kyc'
                elif any(k in low for k in ('pay','payout','withdraw','billing')): kind='payout'
                elif any(k in low for k in ('api','developer','docs')): kind='api'
                elif any(k in low for k in ('forum','community','discussion','thread')): kind='community'
                self.c.execute('''INSERT INTO source_endpoints(source,url,endpoint_kind,status,http_status,last_checked_at,evidence_confidence,content_sha256)
                                  VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source,url) DO UPDATE SET status=excluded.status,http_status=excluded.http_status,last_checked_at=excluded.last_checked_at,evidence_confidence=excluded.evidence_confidence,content_sha256=excluded.content_sha256''',
                               (x['source'],endpoint_url,kind,'LIVE_CONFIRMED' if x.get('source_verification_state')=='LIVE_CONFIRMED' else 'ERROR',x.get('http_status'),x.get('last_verified_at'),float(x.get('evidence_confidence',0) or 0),x.get('sha256')))
            self.c.execute('''INSERT INTO source_verification_state(source,checked_at,http_status,source_verification_state,iran_eligibility,kyc_requirement,payment_capabilities,payout_evidence_url,kyc_evidence_url,terms_evidence_url,evidence_confidence,evidence_urls_json,findings_json,policy_lane,execution_ready,error)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source) DO UPDATE SET checked_at=excluded.checked_at,http_status=excluded.http_status,source_verification_state=excluded.source_verification_state,iran_eligibility=excluded.iran_eligibility,kyc_requirement=excluded.kyc_requirement,payment_capabilities=excluded.payment_capabilities,payout_evidence_url=excluded.payout_evidence_url,kyc_evidence_url=excluded.kyc_evidence_url,terms_evidence_url=excluded.terms_evidence_url,evidence_confidence=excluded.evidence_confidence,evidence_urls_json=excluded.evidence_urls_json,findings_json=excluded.findings_json,policy_lane=excluded.policy_lane,execution_ready=excluded.execution_ready,error=excluded.error''',
                (x['source'],x.get('last_verified_at',now),x.get('http_status'),x.get('source_verification_state','DISCOVERED'),x.get('iran_eligibility','UNKNOWN'),x.get('kyc_requirement','UNKNOWN'),json.dumps(x.get('payment_capabilities',[])),x.get('payout_evidence_url'),x.get('kyc_evidence_url'),x.get('terms_evidence_url'),x.get('evidence_confidence',0),json.dumps(x.get('evidence_urls',[]),ensure_ascii=False),json.dumps(x.get('iran_findings',[]),ensure_ascii=False),x.get('policy_lane','REVIEW'),int(bool(x.get('execution_ready'))),x.get('error')))
            self.c.execute('''UPDATE sources SET status=?,source_verification_state=?,iran_eligibility=?,kyc_requirement=?,payment_capabilities=?,payout_evidence_url=?,kyc_evidence_url=?,terms_evidence_url=?,last_verified_at=?,evidence_confidence=?,execution_ready=?,policy_lane=?,verification_state=?,terms_status=?,capability_maturity=?,capability_evidence_json=?,capability_checked_at=?,stale_at=? WHERE name=?''',
                (x.get('status','candidate'),x.get('source_verification_state','DISCOVERED'),x.get('iran_eligibility','UNKNOWN'),x.get('kyc_requirement','UNKNOWN'),json.dumps(x.get('payment_capabilities',[]),ensure_ascii=False),x.get('payout_evidence_url'),x.get('kyc_evidence_url'),x.get('terms_evidence_url'),x.get('last_verified_at',now),x.get('evidence_confidence',0),int(bool(x.get('execution_ready'))),x.get('policy_lane','REVIEW'),x.get('verification_state','documented'),x.get('terms_status','needs_review'),x.get('capability_maturity','REGISTERED'),json.dumps(x.get('capability_evidence',[]),ensure_ascii=False),x.get('last_verified_at',now),x.get('stale_at'),x['source']))
            self.c.execute("UPDATE sources SET source_lane=?,blacklist_reason=?,blacklisted_at=?,project_scan_interval_minutes=?,intelligence_scan_interval_minutes=? WHERE name=?", (x.get('source_lane','REVIEW'),x.get('blacklist_reason'),x.get('blacklisted_at'),int(x.get('project_scan_interval_minutes',60) or 60),int(x.get('intelligence_scan_interval_minutes',720) or 720),x['source']))
            self.c.execute("UPDATE source_contracts SET source_lane=?,blacklist_reason=?,blacklisted_at=?,project_scan_interval_minutes=?,intelligence_scan_interval_minutes=? WHERE source=?", (x.get('source_lane','REVIEW'),x.get('blacklist_reason'),x.get('blacklisted_at'),int(x.get('project_scan_interval_minutes',60) or 60),int(x.get('intelligence_scan_interval_minutes',720) or 720),x['source']))
            if x.get('source_lane') == BLACKLIST_LANE:
                self.c.execute("INSERT OR IGNORE INTO source_blacklist_archive(source,reason,observed_at,evidence_json) VALUES(?,?,?,?)", (x['source'],x.get('blacklist_reason') or 'BLACKLIST_ARCHIVE',x.get('last_verified_at',now),json.dumps({'evidence_urls':x.get('evidence_urls',[]),'iran_findings':x.get('iran_findings',[])},ensure_ascii=False)))
            self.c.execute('''UPDATE source_contracts SET source_verification_state=?,iran_eligibility=?,kyc_requirement=?,payment_capabilities=?,payout_evidence_url=?,kyc_evidence_url=?,terms_evidence_url=?,last_verified_at=?,evidence_confidence=?,execution_ready=?,policy_lane=?,verification_basis=?,runtime_verification_state=?,capability_maturity=?,capability_evidence_json=?,capability_checked_at=?,stale_at=? WHERE source=?''',
                (x.get('source_verification_state','DISCOVERED'),x.get('iran_eligibility','UNKNOWN'),x.get('kyc_requirement','UNKNOWN'),json.dumps(x.get('payment_capabilities',[]),ensure_ascii=False),x.get('payout_evidence_url'),x.get('kyc_evidence_url'),x.get('terms_evidence_url'),x.get('last_verified_at',now),x.get('evidence_confidence',0),int(bool(x.get('execution_ready'))),x.get('policy_lane','REVIEW'),'automatic_policy_monitor','blocked' if x.get('iran_eligibility')=='BLOCK' else 'verified' if x.get('source_verification_state')=='LIVE_CONFIRMED' else 'degraded',x.get('capability_maturity','REGISTERED'),json.dumps(x.get('capability_evidence',[]),ensure_ascii=False),x.get('last_verified_at',now),x.get('stale_at'),x['source']))
        self.c.commit()
        return results

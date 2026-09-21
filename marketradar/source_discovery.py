from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .federation import Federation, Source
from .source_search import WebSearchProvider, SearchProviderError
from .discovery_intelligence import QueryPlanner, classify_search_result
from .access_broker import plan_for_url

URL_RE = re.compile(r'https?://[^\s\)\]\|<>"\']+')
MD_LINK_RE = re.compile(r'\[[^\]]+\]\((https?://[^\)]+)\)')
TABLE_RE = re.compile(r'^\|\s*([^|]+?)\s*\|\s*(https?://[^|\s]+)', re.M)

FAMILY_HINTS = {
    'bug_bounty': ('bug bounty', 'vulnerability', 'responsible disclosure', 'security.txt', 'vdp', 'security program'),
    'social_platform': ('messaging', 'messenger', 'social network', 'telegram', 'rubika', 'eitaa', 'bale', 'soroush', 'instagram', 'reddit', 'linkedin', 'x.com'),
    'job_marketplace': ('freelance', 'freelancer', 'project marketplace', 'gig', 'outsourc'),
    'job_board': ('job', 'jobs', 'career', 'vacanc', 'employment', 'hiring', 'کاریاب', 'استخدام', 'شغل'),
    'community_forum': ('forum', 'community', 'discussion', 'board', 'thread', 'reddit', 'stackexchange', 'quora', 'discuss'),
    'market_intelligence': ('marketplace', 'classified', 'tender', 'procurement', 'supplier', 'business directory'),
}

ROLE_BY_FAMILY = {
    'bug_bounty': 'bug_bounty',
    'social_platform': 'social_platform',
    'job_marketplace': 'freelance_marketplace',
    'job_board': 'job_board',
    'community_forum': 'community_forum',
    'market_intelligence': 'market_intelligence',
}


class _LinkParser(HTMLParser):
    def __init__(self, base_url: str, max_links: int = 40):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.max_links = max_links
        self.links = []
        self._seen = set()

    def handle_starttag(self, tag, attrs):
        if len(self.links) >= self.max_links:
            return
        attrs = dict(attrs)
        href = attrs.get('href')
        if not href:
            return
        absolute = urljoin(self.base_url, href)
        p = urlparse(absolute)
        if p.scheme not in {'http', 'https'} or not p.hostname:
            return
        clean = f'{p.scheme}://{p.netloc}{p.path}'
        if clean not in self._seen:
            self._seen.add(clean)
            self.links.append(clean)


def _family_for(text: str, planned: str) -> str:
    low = text.lower()
    ordered = [planned, 'bug_bounty', 'community_forum', 'job_marketplace', 'job_board', 'social_platform', 'market_intelligence']
    for family in ordered:
        hints = FAMILY_HINTS.get(family, ())
        if any(h in low for h in hints):
            return family
    return 'community_forum' if planned in {'community', 'policy'} else {'freelance':'job_marketplace','jobs':'job_board','bug_bounty':'bug_bounty','social':'social_platform','market':'market_intelligence'}.get(planned, 'job_board')


def _slug_name(title: str, host: str) -> str:
    text = re.sub(r'\s+', ' ', str(title or '')).strip()
    text = re.split(r'\s+[|\-–—:]\s+', text)[0].strip()
    tokens = re.findall(r'[\w\u0600-\u06ff][\w\u0600-\u06ff.\- ]{1,70}', text, re.UNICODE)
    base = tokens[0].strip() if tokens else (host or 'unknown_source')
    base = re.sub(r'[^\w\u0600-\u06ff.-]+', '_', base, flags=re.UNICODE).strip('_')
    return (base[:70] or host.replace('.', '_'))


class SourceDiscoveryEngine:
    """Autonomous discovery + evidence collection.

    The baseline registry is only one input. Discovery can find candidates from
    catalogs, search engines, community/forum discussions, hashtags and outbound
    links found in public result pages. Every candidate keeps provenance back to
    the query/result that caused its discovery. Discovery never grants execution.
    """
    def __init__(self, catalog_records=None, query_config=None, search_provider=None, timeout=15, coverage_entities=None, state_path=None):
        self.catalogs = catalog_records or []
        self.query_config = query_config or {'queries': [], 'search_limit_per_query': 10}
        self.search = search_provider or WebSearchProvider(timeout=timeout)
        self.timeout = timeout
        self.coverage_entities = coverage_entities or []
        self.state_path = Path(state_path) if state_path else None
        self.sources = [Source(c['name'], c['url'], c.get('adapter','html'), 'active', tuple(c.get('allow_hosts',[urlparse(c['url']).hostname])), 'public') for c in self.catalogs]
        self.http = Federation(self.sources, timeout=timeout, max_workers=4) if self.sources else None
        self._intelligence_rows = []

    @staticmethod
    def _normalize(url):
        p = urlparse(url)
        if p.scheme not in {'http','https'} or not p.hostname:
            return None
        host = p.hostname.lower().rstrip('.')
        if host in {'google.com','bing.com','yahoo.com'}:
            return None
        path = p.path.rstrip('/') or '/'
        return f'{p.scheme}://{host}{path}'

    @staticmethod
    def _candidate(name, url, family, plan, basis, evidence_url, title='', snippet='', score=0.5, discovery_method='search_result'):
        normalized = SourceDiscoveryEngine._normalize(url)
        if not normalized:
            return None
        host = urlparse(normalized).hostname
        role = ROLE_BY_FAMILY.get(family, 'source')
        lane = 'MARKET_INTELLIGENCE_ONLY' if family == 'market_intelligence' else 'GLOBAL_DISCOVERY'
        if family == 'community_forum':
            lane = 'GLOBAL_DISCOVERY'
        if plan.get('country') == 'Iran' and family in {'job_marketplace','job_board','social_platform','community_forum'}:
            lane = 'NEEDS_ANALYSIS'
        return {
            'name': _slug_name(name, host), 'base_url': f'{urlparse(normalized).scheme}://{host}/', 'allow_hosts':[host],
            'adapter':'html', 'status':'candidate', 'source_kind':family, 'acquisition':'http', 'verification_state':'documented',
            'access_scope':'public', 'terms_status':'needs_review', 'country':plan.get('country','Global'), 'region':plan.get('region','Global'),
            'language':plan.get('language','multi'), 'source_family':family, 'source_role':role, 'policy_lane':lane,
            'daily_scan':False, 'needs_analysis':True, 'source_verification_state':'DISCOVERED', 'iran_eligibility':'UNKNOWN',
            'kyc_requirement':'UNKNOWN', 'payment_capabilities':[], 'evidence_confidence':round(min(max(float(score),0.1),0.95),2),
            'market_intelligence_value':'HIGH' if family in {'community_forum','market_intelligence'} else 'MEDIUM', 'execution_ready':False,
            'discovery_basis':basis, 'discovery_evidence_url':evidence_url, 'discovery_method':discovery_method,
            'discovery_title':title[:240], 'discovery_snippet':snippet[:700], 'source_origin':'dynamic_discovery',
            'verification_basis':'automatic_search_discovery', 'upstream_sources':[evidence_url] if evidence_url else [],
            'access_plan': ({'platform': plan_for_url(normalized).platform, 'mode': plan_for_url(normalized).mode.value, 'required_action': plan_for_url(normalized).required_action, 'scope': plan_for_url(normalized).scope} if plan_for_url(normalized) else None),
            'notes':f'Autodiscovered via {discovery_method}; candidate only until automatic source-policy verification.'
        }

    def _parse_markdown(self, text, catalog=None):
        rows=[]
        for name,url in TABLE_RE.findall(text): rows.append((name.strip(),url.strip()))
        for url in MD_LINK_RE.findall(text): rows.append((urlparse(url).hostname or url,url))
        for url in URL_RE.findall(text): rows.append((urlparse(url).hostname or url,url))
        return rows

    @staticmethod
    def _parse_json(text,catalog):
        data=json.loads(text)
        if not isinstance(data,list): return []
        out=[]
        for item in data:
            if not isinstance(item,dict): continue
            url=item.get('url') or item.get('program_url') or item.get('program_link')
            name=item.get('program_name') or item.get('name') or item.get('company_name')
            if url and name: out.append((str(name),str(url),item))
        return out

    def _catalog_discovery(self, discovered, evidence, errors):
        if not self.http: return
        for catalog in self.catalogs:
            try:
                obs=self.http.fetch(catalog['name']); text=obs['body'].decode('utf-8',errors='ignore')
                rows=self._parse_json(text,catalog) if catalog.get('format')=='json' else self._parse_markdown(text,catalog)
                for row in rows:
                    name,url=row[:2]; meta=row[2] if len(row)>2 else {}
                    plan={'country':meta.get('region','Global'),'region':meta.get('region','Global'),'language':'multi'}
                    family='bug_bounty' if ('bug' in catalog['name'].lower() or 'diodb' in catalog['name'].lower()) else 'job_board'
                    candidate=self._candidate(name,url,family,plan,catalog['name'],catalog['url'],name,'catalog result',0.65,'catalog')
                    if candidate: self._merge(discovered,candidate,evidence,{'query':catalog['name'],'provider':'catalog','url':catalog['url'],'title':name,'snippet':'catalog result','country':plan['country'],'language':plan['language'],'method':'catalog'})
            except Exception as exc:
                errors.append({'catalog':catalog['name'],'error':type(exc).__name__+': '+str(exc)})

    def _load_state(self):
        if not self.state_path or not self.state_path.exists(): return {'cursor':0}
        try: return json.loads(self.state_path.read_text(encoding='utf-8'))
        except Exception: return {'cursor':0}

    def _save_state(self, state):
        if not self.state_path: return
        self.state_path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.state_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        tmp.replace(self.state_path)

    def _planned_queries(self):
        entities=self.coverage_entities or self.query_config.get('country_matrix',[])
        history={}
        try:
            # Query history is injected by CLI when a DB-backed planner is used;
            # standalone discovery remains deterministic with an empty history.
            history=self.query_config.get('_query_history',{})
        except Exception:
            history={}
        planner=QueryPlanner(self.query_config,history)
        plans=planner.plan(entities,max_queries=int(self.query_config.get('max_queries_per_cycle',200)))
        batch=int(self.query_config.get('country_batch_size',50))
        if entities:
            state=self._load_state(); cursor=int(state.get('cursor',0)) % len(entities)
            batch_entities=[*entities[cursor:cursor+batch]]
            if len(batch_entities)<batch: batch_entities += entities[:batch-len(batch_entities)]
            templates=self.query_config.get('country_templates',[])
            for entity in batch_entities:
                for template in templates:
                    q=template.get('template','').format(**entity)
                    plans.append({'id':f"{entity.get('iso2',entity.get('country'))}_{template.get('family','jobs')}", 'country':entity.get('country','Global'), 'region':entity.get('region','Global'), 'language':entity.get('language','multi'), 'family':template.get('family','jobs'), 'q':q})
            self._planned_batch_state={'cursor':(cursor+batch)%len(entities),'queried':len(batch_entities),'total':len(entities)}
        else:
            self._planned_batch_state={'cursor':0,'queried':0,'total':0}
        return plans[:int(self.query_config.get('max_queries_per_cycle',200))]

    def _crawl_result_page(self, result, plan, discovered, evidence, errors):
        if not self.query_config.get('crawl_result_pages',True): return
        url=result.get('url','')
        p=urlparse(url)
        if p.scheme not in {'http','https'} or not p.hostname: return
        protected_hosts = {
            'instagram.com','www.instagram.com','linkedin.com','www.linkedin.com',
            'x.com','www.x.com','twitter.com','www.twitter.com',
            'facebook.com','www.facebook.com','t.me','telegram.me',
            'telegram.org','rubika.ir','www.rubika.ir','eitaa.com','www.eitaa.com',
            'eitaa.ir','www.eitaa.ir','splus.ir','www.splus.ir','ble.ir','www.ble.ir'
        }
        if (p.hostname and p.hostname.lower() in protected_hosts):
            # Search/index evidence is valid discovery evidence. Direct crawling of
            # protected platforms is delegated to authorized connectors.
            return
        try:
            req=Request(url,headers={'User-Agent':'SEPP-MarketRadar/16.1.1 DiscoveryCrawler'})
            with urlopen(req,timeout=self.timeout) as resp:
                body=resp.read(300_000)
                final=resp.geturl()
            text=body.decode('utf-8','ignore')
            parser=_LinkParser(final,int(self.query_config.get('max_outbound_links_per_page',40))); parser.feed(text)
            for link in parser.links:
                host=urlparse(link).hostname or ''
                if not host or host == p.hostname: continue
                family=_family_for((result.get('title','')+' '+result.get('snippet','')+' '+link),plan.get('family','community'))
                if family == 'community_forum' and plan.get('family') in {'jobs','bug_bounty','policy'}: family=plan.get('family') if plan.get('family')!='policy' else 'job_marketplace'
                candidate=self._candidate(host,link,family,plan,f"crawl:{plan.get('id','query')}",url,result.get('title',''),result.get('snippet',''),0.62,'forum_outbound_link')
                if candidate:
                    self._merge(discovered,candidate,evidence,{'query':plan.get('q',''),'provider':result.get('_provider','search'),'url':url,'title':result.get('title',''),'snippet':result.get('snippet',''),'country':plan.get('country','Global'),'region':plan.get('region','Global'),'language':plan.get('language','multi'),'method':'forum_outbound_link'})
        except Exception as exc:
            errors.append({'crawl_url':url,'error':type(exc).__name__+': '+str(exc)})

    @staticmethod
    def _merge(discovered,candidate,evidence,ev):
        host=urlparse(candidate['base_url']).hostname
        existing=discovered.get(host)
        if not existing or candidate['evidence_confidence'] > existing.get('evidence_confidence',0):
            discovered[host]=candidate
        source=discovered[host]
        evidence.append({'source':source['name'], **ev, 'result_url':candidate['base_url'], 'title':candidate.get('discovery_title',''), 'snippet':candidate.get('discovery_snippet','')})

    def _bridge_linked_web_endpoints(self, item, plan, discovered, evidence):
        """Use indexed social/channel mentions to discover their companion websites.

        A Telegram/LinkedIn/etc. result may advertise a separate website. We can
        discover that website from the indexed evidence without crawling the
        protected platform itself.
        """
        text = f"{item.get('title','')} {item.get('snippet','')}"
        links = []
        for raw in URL_RE.findall(text):
            link = raw.rstrip('.,;')
            host = (urlparse(link).hostname or '').lower()
            if host and host not in {'google.com','bing.com','yahoo.com'}:
                links.append(link)
        protected = {'instagram.com','www.instagram.com','linkedin.com','www.linkedin.com','x.com','www.x.com','twitter.com','www.twitter.com','facebook.com','www.facebook.com','t.me','telegram.me','telegram.org','rubika.ir','www.rubika.ir','eitaa.com','www.eitaa.com','eitaa.ir','www.eitaa.ir','splus.ir','www.splus.ir','ble.ir','www.ble.ir','bale.ai','www.bale.ai'}
        source_host = (urlparse(item.get('url','')).hostname or '').lower()
        if source_host not in protected and not plan.get('platform'):
            return
        for link in links:
            host = (urlparse(link).hostname or '').lower()
            if not host or host in protected: continue
            family = _family_for(f"{item.get('title','')} {item.get('snippet','')} {link}", plan.get('family','community'))
            candidate = self._candidate(host, link, family, plan, f"linked-endpoint:{plan.get('id','query')}", item.get('url',''), item.get('title',''), item.get('snippet',''), 0.68, 'platform_linked_website')
            if candidate:
                candidate['linked_from_platform'] = plan.get('platform') or source_host
                candidate['linked_from_url'] = item.get('url','')
                self._merge(discovered, candidate, evidence, {'query':plan.get('q',''),'provider':item.get('_provider','search'),'url':item.get('url',''),'title':item.get('title',''),'snippet':item.get('snippet',''),'country':plan.get('country','Global'),'region':plan.get('region','Global'),'language':plan.get('language','multi'),'method':'platform_linked_website'})

    def _search_discovery(self, discovered, evidence, errors):
        plans=self._planned_queries()
        if not self.search.available():
            errors.append({'provider':'search','error':'NO_SEARCH_PROVIDER_CONFIGURED','queries_skipped':len(plans)})
            return plans
        crawl_budget=int(self.query_config.get('max_crawl_pages_per_cycle',80)); crawled=0
        for plan in plans:
            query=plan.get('q','').strip()
            if not query: continue
            try:
                results=self.search.search(query,int(self.query_config.get('search_limit_per_query',10)))
                for item in results:
                    item['_provider']=getattr(self.search,'provider','test')
                    self._intelligence_rows.append((plan,dict(item)))
                    url=item.get('url',''); title=item.get('title',''); snippet=item.get('snippet','')
                    family=_family_for(f'{title} {snippet} {url}',plan.get('family','jobs'))
                    score=0.55 + (0.12 if family==_family_for('',plan.get('family','jobs')) else 0) + (0.08 if url else 0)
                    candidate=self._candidate(title or urlparse(url).hostname,url,family,plan,f"search:{plan.get('id',query)}",url,title,snippet,score,'search_result')
                    if candidate:
                        self._merge(discovered,candidate,evidence,{'query':query,'provider':getattr(self.search,'provider','unknown'),'url':url,'title':title,'snippet':snippet,'country':plan.get('country','Global'),'region':plan.get('region','Global'),'language':plan.get('language','multi'),'method':'search_result'})
                    self._bridge_linked_web_endpoints(item, plan, discovered, evidence)
                    if crawled < crawl_budget and self._looks_like_community(title,snippet,url,plan):
                        self._crawl_result_page(item,plan,discovered,evidence,errors); crawled += 1
            except SearchProviderError as exc:
                errors.append({'query':query,'error':str(exc)})
            except Exception as exc:
                errors.append({'query':query,'error':type(exc).__name__+': '+str(exc)})
        return plans

    @staticmethod
    def _looks_like_community(title,snippet,url,plan):
        low=f'{title} {snippet} {url}'.lower()
        hints=('forum','community','discussion','thread','reddit','stackexchange','quora','talk','board','experience','review')
        return plan.get('family') in {'community','policy'} or any(x in low for x in hints)

    def discover(self, include_catalogs=True, include_search=True):
        discovered={}; evidence=[]; errors=[]
        if include_catalogs: self._catalog_discovery(discovered,evidence,errors)
        plans=self._search_discovery(discovered,evidence,errors) if include_search else []
        used=set()
        for candidate in discovered.values():
            base=candidate['name']; host=(urlparse(candidate['base_url']).hostname or '').replace('.','_'); name=base
            n=2
            while name in used:
                name=f'{base}_{host}_{n}'[:80]; n+=1
            candidate['name']=name; used.add(name)
        if include_search and getattr(self,'_planned_batch_state',None): self._save_state(self._planned_batch_state)
        return {'checked_catalogs':len(self.catalogs),'search_queries':len(plans),'search_provider_available':bool(self.search.available()) if include_search else False,'coverage_entities':len(self.coverage_entities),'coverage_entities_queried':getattr(self,'_planned_batch_state',{}).get('queried',0),'candidates':sorted(discovered.values(),key=lambda x:x['name'].lower()),'evidence':evidence,'errors':errors,'generated_at':datetime.now(timezone.utc).isoformat(),'query_observations':self._intelligence_rows}


def persist_candidates(c, result):
    from .source_identity import identity_from_record
    import hashlib
    now=result.get('generated_at') or datetime.now(timezone.utc).isoformat()
    for item in result.get('candidates', []):
        ident=identity_from_record(item)
        key='|'.join((ident.get('canonical_host',''),ident.get('organization',''),ident.get('platform',''),ident.get('endpoint','')))
        candidate_key=hashlib.sha256(key.encode('utf-8')).hexdigest()
        c.execute("""INSERT INTO source_candidates(candidate_key,base_url,name,discovery_basis,provider,query,region,language,source_family,evidence_confidence,evidence_json,first_seen,last_seen,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(candidate_key) DO UPDATE SET last_seen=excluded.last_seen,evidence_confidence=excluded.evidence_confidence,evidence_json=excluded.evidence_json,status=excluded.status""", (candidate_key,item.get('base_url'),item.get('name'),item.get('discovery_basis'),item.get('provider'),item.get('query'),item.get('region'),item.get('language'),item.get('source_family') or item.get('family'),float(item.get('evidence_confidence',0) or 0),json.dumps({'identity':ident,'candidate':item},ensure_ascii=False),now,now,'CANDIDATE'))
    c.commit()


def persist_discovery_evidence(c, result):
    now=result.get('generated_at') or datetime.now(timezone.utc).isoformat()
    for ev in result.get('evidence',[]):
        raw=json.dumps(ev,sort_keys=True,ensure_ascii=False)
        h=hashlib.sha256(raw.encode()).hexdigest()
        c.execute('''INSERT OR IGNORE INTO source_discovery_evidence(source,observed_at,query,query_family,country,region,language,provider,result_url,title,snippet,discovery_method,evidence_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (ev.get('source'),now,ev.get('query'),ev.get('family') or ev.get('query_family'),ev.get('country'),ev.get('region'),ev.get('language'),ev.get('provider'),ev.get('url') or ev.get('result_url'),ev.get('title'),ev.get('snippet'),ev.get('method','search_result'),h))
    c.commit()


def persist_source_endpoints(c, records):
    now=datetime.now(timezone.utc).isoformat()
    for r in records:
        if not r.get('name') or not r.get('base_url'): continue
        c.execute('''INSERT INTO source_endpoints(source,url,endpoint_kind,status,last_checked_at,evidence_confidence) VALUES(?,?,?,?,?,?) ON CONFLICT(source,url) DO UPDATE SET endpoint_kind=excluded.endpoint_kind,status=excluded.status,last_checked_at=excluded.last_checked_at,evidence_confidence=excluded.evidence_confidence''',
                  (r['name'],r['base_url'],'home','DISCOVERED',now,float(r.get('evidence_confidence',0) or 0)))
    c.commit()


def classify_source_lanes(records):
    from collections import Counter
    return dict(Counter(r.get('policy_lane','REVIEW') for r in records))


def discovery_candidates(records, limit=100):
    out=[]
    for r in records:
        if r.get('status')=='candidate' and r.get('policy_lane') in {'GLOBAL_DISCOVERY','NEEDS_ANALYSIS','MARKET_INTELLIGENCE_ONLY','REVIEW'}:
            out.append({'name':r.get('name'),'url':r.get('base_url'),'reason':r.get('notes',''),'iran_status':r.get('iran_status',r.get('iran_eligibility','UNKNOWN')),'source_role':r.get('source_role')})
    return out[:limit]

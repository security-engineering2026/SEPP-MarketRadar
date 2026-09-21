from __future__ import annotations

import hashlib, json, re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

OPERATOR_RE = re.compile(r'(?P<op>site|intitle|inurl|before|after):(?P<value>[^\s]+)', re.I)

class QueryPlanner:
    """Builds a search plan instead of treating discovery as one raw query.

    The planner emits query variants with explicit operator semantics, language,
    source-family intent, community intent and negative terms. Historical yield
    is used only to prioritize variants; it never changes deterministic policy.
    """
    OPERATOR_FAMILIES = {
        'broad': ['{topic} {country} {signals}'],
        'exact': ['"{topic}" "{signal}" {country}'],
        'site': ['site:{domain} {topic} {signal}'],
        'community': ['{topic} {country} forum discussion experience {signal} -jobs -course'],
        'policy': ['{topic} {country} terms eligibility KYC payout restrictions'],
        'fresh': ['{topic} {country} {signal} after:{year}'],
        'hashtag': ['{hashtags} {country} {signal}'],
        'forum_site': ['site:{domain} {topic} {signal} "{country}" -jobs -course'],
    }

    def __init__(self, config: dict, history=None):
        self.config = config or {}
        self.history = history or {}

    @staticmethod
    def _signals(family):
        return {
            'jobs': ['freelance', 'developer', 'remote work', 'project marketplace'],
            'bug_bounty': ['bug bounty', 'VDP', 'vulnerability disclosure', 'security program'],
            'community': ['KYC', 'payout', 'payment', 'withdrawal', 'country restriction'],
            'policy': ['eligibility', 'KYC', 'payout', 'country restriction'],
            'social': ['messaging', 'community', 'creator', 'platform'],
        }.get(family, ['platform', 'experience'])

    def plan(self, entities=None, max_queries=200):
        entities = entities or []
        base = list(self.config.get('priority_queries', [])) + list(self.config.get('queries', []))
        plans=[]
        for x in base:
            plans.append(dict(x, operator_mode='explicit', operator_score=1.0))
        templates=self.config.get('country_templates', [])
        batch=int(self.config.get('country_batch_size',50))
        platform_targets = self.config.get('platform_targets', [])
        platform_countries = list(self.config.get('platform_priority_countries', []))
        entity_by_country = {str(x.get('country','')).strip(): x for x in entities}
        platform_entities = []
        for country in platform_countries:
            if country in entity_by_country:
                platform_entities.append(entity_by_country[country])
        for entity in entities[:batch]:
            if entity not in platform_entities:
                platform_entities.append(entity)
        for entity in platform_entities:
            country=entity.get('country','Global'); language=entity.get('language','multi')
            for t in templates:
                fam=t.get('family','jobs'); signal=self._signals(fam)[0]
                topic={'jobs':'freelance developer jobs platform','bug_bounty':'bug bounty vulnerability disclosure','community':'freelance platform','policy':'freelance platform','social':'social platform'}.get(fam,fam)
                variants=[
                    ('broad',f'"{country}" {topic} {signal}'),
                    ('exact',f'"{topic}" "{signal}" "{country}"'),
                    ('community',f'"{country}" forum discussion experience {topic} {signal} -course -tutorial'),
                    ('policy',f'"{country}" {topic} terms eligibility KYC payout restrictions'),
                    ('hashtag',f'#{fam.replace("bug_bounty","bugbounty")} #remotework "{country}" {signal}'),
                    ('fresh',f'"{topic}" {signal} "{country}" after:2025'),
                ]
                for domain in self.config.get('community_domains', ['reddit.com','stackoverflow.com','stackexchange.com','quora.com']):
                    variants.append(('forum_site',f'site:{domain} "{topic}" {signal} "{country}" -jobs -course'))
                for mode,q in variants:
                    plans.append({'id':f'{entity.get("iso2",country)}_{fam}_{mode}','country':country,'region':entity.get('region','Global'),'language':language,'family':fam,'q':q,'operator_mode':mode,'operator_score':self._priority(fam,mode)})
        # Platform discovery is generated from platform families, not a hand-curated
        # list of individual opportunities/sites. Search engines/indexers find the
        # actual channels, profiles, groups, pages and communities.
        for target in platform_targets:
            domains = target.get('domains') or []
            terms = target.get('terms') or target.get('name','')
            family = target.get('family','social')
            for entity in platform_entities[:max(1, batch)]:
                country=entity.get('country','Global'); language=entity.get('language','multi')
                for domain in domains:
                    plans.append({
                        'id':f'{entity.get("iso2",country)}_{target.get("id",family)}_site_{domain}',
                        'country':country,'region':entity.get('region','Global'),'language':language,
                        'family':family,
                        'q':f'site:{domain} ({terms}) "{country}" (freelance OR project OR hiring OR job OR contract OR opportunity)',
                        'operator_mode':'platform_site','operator_score':self._priority(family,'site') + 0.12,
                        'platform':target.get('id',family),'platform_discovery':'public_index'
                    })
                plans.append({
                    'id':f'{entity.get("iso2",country)}_{target.get("id",family)}_broad',
                    'country':country,'region':entity.get('region','Global'),'language':language,
                    'family':family,
                    'q':f'"{country}" {terms} (freelance OR project OR hiring OR job OR contract OR opportunity)',
                    'operator_mode':'platform_broad','operator_score':self._priority(family,'broad'),
                    'platform':target.get('id',family),'platform_discovery':'public_index'
                })
        priority_cfg={str(x.get('country')):float(x.get('priority_boost',0)) for x in self.config.get('priority_regions',[]) if x.get('country')}
        for p in plans:
            p['operator_score']=float(p.get('operator_score',0))+priority_cfg.get(str(p.get('country','')),0.0)
        priority_cfg={str(x.get('country')):float(x.get('priority_boost',0)) for x in self.config.get('priority_regions',[]) if x.get('country')}
        for p in plans:
            p['operator_score']=float(p.get('operator_score',0))+priority_cfg.get(str(p.get('country','')),0.0)
        plans.sort(key=lambda p:p.get('operator_score',0), reverse=True)
        return plans[:max_queries]

    def _priority(self, family, mode):
        key=f'{family}:{mode}'
        return float(self.history.get(key, 0.0)) + {'exact':.35,'site':.30,'community':.30,'policy':.28,'hashtag':.22,'fresh':.18,'broad':.10}.get(mode,0)

    @staticmethod
    def explain(query):
        return [{'operator':m.group('op').lower(),'value':m.group('value')} for m in OPERATOR_RE.finditer(query)]


def classify_search_result(result, plan):
    text=f"{result.get('title','')} {result.get('snippet','')} {result.get('url','')}".lower()
    community_terms=('forum','community','discussion','thread','reddit','stackexchange','quora','review','experience','withdrawal','payout')
    policy_terms=('terms','eligibility','kyc','verification','payout','payment','restricted','country')
    signals=[]
    if any(x in text for x in community_terms): signals.append('community')
    if any(x in text for x in policy_terms): signals.append('policy')
    if any(x in text for x in ('bug bounty','vulnerability','vdp','security program')): signals.append('bug_bounty')
    if any(x in text for x in ('freelance','freelancer','gig','project marketplace')): signals.append('freelance')
    return {'signals':signals,'community_signal':('community' in signals),'policy_signal':('policy' in signals),'engine_count':len(result.get('engines') or []),'query_mode':plan.get('operator_mode','unknown')}


def build_graph_observations(result, plan, classification):
    url=result.get('url',''); host=urlparse(url).hostname or ''
    if not host: return []
    now=datetime.now(timezone.utc).isoformat()
    out=[{'node_type':'source_candidate','node_key':host,'label':result.get('title') or host,'observed_at':now,'weight':0.5 + 0.1*min(classification.get('engine_count',0),3)}]
    for signal in classification.get('signals',[]):
        out.append({'node_type':'signal','node_key':signal,'label':signal,'observed_at':now,'weight':1.0})
        out.append({'edge_source':host,'edge_target':signal,'edge_type':'HAS_SIGNAL','weight':1.0,'observed_at':now})
    if plan.get('country'):
        key=str(plan['country']).lower()
        out.append({'node_type':'country','node_key':key,'label':plan['country'],'observed_at':now,'weight':1.0})
        out.append({'edge_source':host,'edge_target':key,'edge_type':'MENTIONED_FOR_COUNTRY','weight':1.0,'observed_at':now})
    return out


def persist_intelligence(c, query_plans, result_rows):
    now=datetime.now(timezone.utc).isoformat()
    for plan, result in result_rows:
        cls=classify_search_result(result, plan)
        raw=json.dumps({'plan':plan,'result':result},sort_keys=True,ensure_ascii=False)
        h=hashlib.sha256(raw.encode()).hexdigest()
        c.execute('''INSERT OR IGNORE INTO discovery_query_observations(query_id,observed_at,query,query_family,operator_mode,country,language,provider,result_url,title,snippet,community_signal,policy_signal,engine_count,result_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (plan.get('id'),now,plan.get('q'),plan.get('family'),plan.get('operator_mode'),plan.get('country'),plan.get('language'),result.get('_provider'),result.get('url'),result.get('title'),result.get('snippet'),int(cls['community_signal']),int(cls['policy_signal']),int(cls['engine_count']),h))
        for item in build_graph_observations(result,plan,cls):
            if 'node_type' in item:
                c.execute('''INSERT OR IGNORE INTO intelligence_nodes(node_type,node_key,label,first_seen,last_seen,weight) VALUES(?,?,?,?,?,?)''', (item['node_type'],item['node_key'],item['label'],now,now,item['weight']))
                c.execute('UPDATE intelligence_nodes SET last_seen=?, weight=MAX(weight,?) WHERE node_type=? AND node_key=?',(now,item['weight'],item['node_type'],item['node_key']))
            else:
                c.execute('''INSERT OR IGNORE INTO intelligence_edges(source_key,target_key,edge_type,first_seen,last_seen,weight) VALUES(?,?,?,?,?,?)''', (item['edge_source'],item['edge_target'],item['edge_type'],now,now,item['weight']))
                c.execute('UPDATE intelligence_edges SET last_seen=?, weight=weight+? WHERE source_key=? AND target_key=? AND edge_type=?',(now,0.1,item['edge_source'],item['edge_target'],item['edge_type']))
    c.commit()


def intelligence_snapshot(c, limit=20):
    nodes=c.execute('SELECT node_type,node_key,label,weight,last_seen FROM intelligence_nodes ORDER BY weight DESC,last_seen DESC LIMIT ?', (limit,)).fetchall()
    edges=c.execute('SELECT source_key,target_key,edge_type,weight,last_seen FROM intelligence_edges ORDER BY weight DESC,last_seen DESC LIMIT ?', (limit,)).fetchall()
    signals=c.execute('SELECT signal,COUNT(*) n FROM community_signals GROUP BY signal ORDER BY n DESC LIMIT ?', (limit,)).fetchall()
    return {'nodes':[dict(x) for x in nodes],'edges':[dict(x) for x in edges],'signals':[dict(x) for x in signals]}

def persist_community_signals(c, query_observations):
    now=datetime.now(timezone.utc).isoformat()
    for plan, result in query_observations:
        cls=classify_search_result(result, plan)
        url=result.get('url') or ''
        host=urlparse(url).hostname or ''
        for signal in cls.get('signals',[]):
            if signal not in {'community','policy'}: continue
            raw=f"{host}|{plan.get('q')}|{signal}|{result.get('title','')}|{result.get('snippet','')}"
            h=hashlib.sha256(raw.encode()).hexdigest()
            c.execute('''INSERT OR IGNORE INTO community_signals(source,observed_at,signal,polarity,confidence,evidence_url,evidence_hash) VALUES(?,?,?,?,?,?,?)''',
                      (host,now,signal,'neutral',0.55 + 0.1*min(cls.get('engine_count',0),3),url,h))
    c.commit()

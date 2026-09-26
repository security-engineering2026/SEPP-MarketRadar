import json
import pytest
from marketradar.source_search import WebSearchProvider, SearchProviderError
from marketradar.source_discovery import SourceDiscoveryEngine

def test_searxng_passes_language_and_normalizes_results(monkeypatch):
    monkeypatch.setenv('SEARXNG_URL','http://searx.local')
    p=WebSearchProvider(provider='searxng')
    seen={}
    def fake_get(url, headers=None):
        seen['url']=url
        return json.dumps({'results':[{'title':'دوچرخه','url':'https://example.test/a','content':'x','engines':['duckduckgo']},{'title':'bad'}]})
    monkeypatch.setattr(p,'_get',fake_get)
    rows=p.search('test',5,language='fa')
    assert 'language=fa' in seen['url']
    assert rows[0]['_provider']=='searxng'
    assert len(rows)==1 and rows[0]['url']=='https://example.test/a'

def test_auto_federation_falls_back_and_keeps_provider_provenance(monkeypatch):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','x')
    monkeypatch.setenv('SEARXNG_URL','http://searx.local')
    p=WebSearchProvider(provider='auto')
    def fake_one(provider, query, limit, language=None):
        if provider=='brave': raise SearchProviderError('boom')
        return [{'title':'ok','url':'https://example.test','snippet':'','_provider':provider}]
    monkeypatch.setattr(p,'_search_one',fake_one)
    rows=p.search('q',3,language='fa')
    assert rows[0]['_provider']=='searxng'

def test_explicit_searxng_invalid_json_is_a_provider_error(monkeypatch):
    monkeypatch.setenv('SEARXNG_URL','http://searx.local')
    p=WebSearchProvider(provider='searxng')
    monkeypatch.setattr(p,'_get',lambda *a,**k:'not-json')
    with pytest.raises(SearchProviderError, match='JSONDecodeError'): p.search('q',3,language='fa')

def test_discovery_propagates_plan_language_to_real_provider(monkeypatch):
    monkeypatch.setenv('SEARXNG_URL','http://searx.local')
    seen={}
    def fake_search(self, query, limit=10, language=None):
        seen['language']=language
        return [{'title':'Iran freelance forum','url':'https://example.test','snippet':'community'}]
    monkeypatch.setattr(WebSearchProvider,'search',fake_search)
    cfg={'queries':[{'id':'fa','country':'Iran','region':'Iran','language':'fa','family':'community','q':'freelance forum Iran'}], 'max_queries_per_cycle':1,'search_limit_per_query':1,'max_crawl_pages_per_cycle':0}
    p=WebSearchProvider(provider='searxng')
    result=SourceDiscoveryEngine([],cfg,p).discover(False,True)
    assert seen['language']=='fa'
    assert result['candidates'][0]['language']=='fa'

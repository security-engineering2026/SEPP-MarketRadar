import sqlite3
from marketradar.discovery_intelligence import QueryPlanner, classify_search_result, build_graph_observations, persist_intelligence, persist_community_signals
from marketradar.source_search import WebSearchProvider


def test_query_planner_has_google_style_operator_modes():
    cfg={'queries':[],'country_batch_size':1,'country_templates':[{'family':'community','template':'x'}], 'community_domains':['reddit.com']}
    plans=QueryPlanner(cfg).plan([{'country':'Iran','iso2':'IR','language':'fa'}],50)
    qs=[p['q'] for p in plans]
    assert any('site:reddit.com' in q for q in qs)
    assert any('"Iran"' in q for q in qs)
    assert any(' -course' in q or ' -jobs' in q for q in qs)
    assert any('after:2025' in q for q in qs)


def test_result_classification_and_graph():
    plan={'country':'Iran','family':'community','operator_mode':'forum_site'}
    result={'url':'https://forum.example/test','title':'Freelance KYC payout discussion','snippet':'forum users discuss payment and withdrawal','engines':['google','brave']}
    cls=classify_search_result(result,plan)
    assert cls['community_signal'] and cls['policy_signal']
    obs=build_graph_observations(result,plan,cls)
    assert any(x.get('edge_type')=='HAS_SIGNAL' for x in obs)
    assert any(x.get('edge_type')=='MENTIONED_FOR_COUNTRY' for x in obs)


def test_searxng_provider_can_be_explicit(monkeypatch):
    monkeypatch.setenv('SEARXNG_URL','http://127.0.0.1:8080')
    p=WebSearchProvider(provider='searxng')
    assert p.available()


def test_intelligence_tables_persist():
    c=sqlite3.connect(':memory:')
    c.executescript('''CREATE TABLE discovery_query_observations(id INTEGER PRIMARY KEY,query_id TEXT,observed_at TEXT NOT NULL,query TEXT,query_family TEXT,operator_mode TEXT,country TEXT,language TEXT,provider TEXT,result_url TEXT,title TEXT,snippet TEXT,community_signal INTEGER,policy_signal INTEGER,engine_count INTEGER,result_hash TEXT UNIQUE); CREATE TABLE intelligence_nodes(id INTEGER PRIMARY KEY,node_type TEXT,node_key TEXT,label TEXT,first_seen TEXT,last_seen TEXT,weight REAL,UNIQUE(node_type,node_key)); CREATE TABLE intelligence_edges(id INTEGER PRIMARY KEY,source_key TEXT,target_key TEXT,edge_type TEXT,first_seen TEXT,last_seen TEXT,weight REAL,UNIQUE(source_key,target_key,edge_type)); CREATE TABLE community_signals(id INTEGER PRIMARY KEY,source TEXT,observed_at TEXT,signal TEXT,polarity TEXT,confidence REAL,evidence_url TEXT,evidence_hash TEXT UNIQUE);''')
    plan={'id':'q1','q':'"Iran" forum freelance KYC -jobs','family':'community','operator_mode':'community','country':'Iran','language':'fa'}
    result={'_provider':'test','url':'https://forum.example/a','title':'Forum payout KYC','snippet':'discussion about payment','engines':['a']}
    persist_intelligence(c,[(plan,result)],[(plan,result)])
    persist_community_signals(c,[(plan,result)])
    assert c.execute('select count(*) from intelligence_nodes').fetchone()[0] >= 2
    assert c.execute('select count(*) from intelligence_edges').fetchone()[0] >= 1
    assert c.execute('select count(*) from community_signals').fetchone()[0] >= 1

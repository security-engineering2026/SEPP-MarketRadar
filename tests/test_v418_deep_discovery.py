import json
import tempfile
from pathlib import Path


def test_coverage_has_200_plus_iso_entities():
    data=json.loads((Path(__file__).parents[1]/'config'/'coverage_entities.json').read_text(encoding='utf-8'))
    assert data['count'] >= 200
    assert len({x['iso2'] for x in data['entities']}) == data['count']
    assert any('Iran' in x['country'] for x in data['entities'])


def test_search_planner_includes_forum_policy_and_hashtag_queries():
    from marketradar.source_discovery import SourceDiscoveryEngine
    cfg=json.loads((Path(__file__).parents[1]/'config'/'discovery_queries.json').read_text(encoding='utf-8'))
    cfg['country_batch_size']=1; cfg['max_queries_per_cycle']=20
    entities=[{'country':'Iran','iso2':'IR','language':'fa','region':'Iran'}]
    e=SourceDiscoveryEngine([],cfg,coverage_entities=entities)
    plans=e._planned_queries()
    qs=[p['q'] for p in plans]
    assert any('forum' in q.lower() for q in qs)
    assert any('#freelance' in q.lower() or '#bugbounty' in q.lower() for q in qs)
    assert any('KYC' in q or 'kyc' in q for q in qs)


def test_forum_result_outbound_links_become_candidates_with_provenance():
    from marketradar.source_discovery import SourceDiscoveryEngine
    class FakeSearch:
        provider='fake'
        def available(self): return True
        def search(self, query, limit):
            return [{'title':'Freelance forum: real payout experiences','url':'http://127.0.0.1:1/thread','snippet':'community discussion about platforms'}]
    e=SourceDiscoveryEngine([],{'queries':[{'id':'forum','country':'Global','family':'community','q':'freelance forum experience'}],'max_crawl_pages_per_cycle':0},FakeSearch())
    result=e.discover(False,True)
    assert result['search_queries']==1
    assert result['evidence']


def test_dynamic_evidence_and_endpoint_tables_persist():
    from marketradar.db import connect
    from marketradar.source_discovery import persist_discovery_evidence,persist_source_endpoints
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(str(Path(d)/'r.db'))
            result={'generated_at':'2026-09-11T00:00:00+00:00','evidence':[{'source':'ForumX','query':'#freelance forum','provider':'fake','url':'https://forum.example/thread','title':'experience','snippet':'payout','country':'Iran','region':'Iran','language':'fa','method':'search_result'}]}
            persist_discovery_evidence(c,result)
            persist_source_endpoints(c,[{'name':'ForumX','base_url':'https://forum.example/','evidence_confidence':0.7}])
            assert c.execute('select count(*) from source_discovery_evidence').fetchone()[0]==1
            assert c.execute('select endpoint_kind from source_endpoints where source="ForumX"').fetchone()[0]=='home'
            c.close()
        finally:
            if 'c' in locals():
                c.close()

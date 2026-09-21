import json
from pathlib import Path


def test_platform_targets_generate_index_discovery_queries_without_manual_source_names():
    from marketradar.discovery_intelligence import QueryPlanner

    cfg=json.loads((Path(__file__).parents[1]/"config"/"discovery_queries.json").read_text(encoding="utf-8"))
    cfg["country_batch_size"]=1
    cfg["max_queries_per_cycle"]=200
    cfg["platform_priority_countries"]=["Iran"]
    entities=[{"country":"Iran","iso2":"IR","language":"fa","region":"Iran"}]
    plans=QueryPlanner(cfg).plan(entities, 200)
    platform_queries=[p for p in plans if p.get("platform_discovery")=="public_index"]
    assert platform_queries
    assert any("site:instagram.com" in p["q"] for p in platform_queries)
    assert any("site:linkedin.com" in p["q"] for p in platform_queries)
    assert any("site:rubika.ir" in p["q"] for p in platform_queries)
    assert any("site:eitaa.com" in p["q"] for p in platform_queries)
    assert any(p["platform"]=="telegram" for p in platform_queries)


def test_protected_platform_result_is_not_directly_crawled():
    from marketradar.source_discovery import SourceDiscoveryEngine

    class FakeSearch:
        provider="fake"
        def available(self): return True
        def search(self, query, limit):
            return [{
                "title":"Instagram freelance opportunity",
                "url":"https://www.instagram.com/example/",
                "snippet":"public indexed result"
            }]

    cfg={
        "queries":[{"id":"social","country":"Iran","region":"Iran","language":"fa","family":"social","q":"Instagram freelance Iran"}],
        "max_crawl_pages_per_cycle":10,
        "crawl_result_pages":True,
    }
    result=SourceDiscoveryEngine([],cfg,FakeSearch()).discover(False,True)
    assert result["candidates"]
    assert not any("crawl_url" in e for e in result["errors"])

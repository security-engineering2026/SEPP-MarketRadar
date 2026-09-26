from marketradar.source_discovery import SourceDiscoveryEngine


def test_indexed_telegram_result_can_discover_companion_website_without_crawling_telegram():
    class FakeSearch:
        provider = "fake"
        def available(self): return True
        def search(self, query, limit):
            return [{
                "title": "Telegram freelance channel",
                "url": "https://t.me/example_channel",
                "snippet": "Projects mirrored at https://example-projects.test/jobs"
            }]

    cfg = {
        "queries": [{"id": "telegram", "country": "Iran", "region": "Iran", "language": "fa", "family": "social", "q": "telegram freelance Iran"}],
        "max_queries_per_cycle": 1,
        "max_crawl_pages_per_cycle": 10,
        "crawl_result_pages": True,
    }
    result = SourceDiscoveryEngine([], cfg, FakeSearch()).discover(False, True)
    urls = {x["base_url"] for x in result["candidates"]}
    assert "https://example-projects.test/" in urls
    assert not any("crawl_url" in e for e in result["errors"])


def test_onion_config_is_known_address_only():
    import json
    from pathlib import Path
    cfg = json.loads((Path(__file__).parents[1] / "config" / "discovery_queries.json").read_text(encoding="utf-8"))
    assert cfg["tor_research"]["mode"] == "KNOWN_ONION_ONLY"
    assert cfg["tor_research"]["automatic_directory_crawling"] is False


def test_opportunity_discovery_includes_deep_dark_web_web_android_lanes():
    import json
    from pathlib import Path
    cfg = json.loads((Path(__file__).parents[1] / 'config' / 'discovery_queries.json').read_text(encoding='utf-8'))
    queries = [x['q'].lower() for x in cfg['queries']]
    assert any('deep web' in q and 'android' in q for q in queries)
    assert any('dark web' in q and 'android' in q for q in queries)
    assert any('.onion' in q and 'bug bounty' in q for q in queries)
    assert cfg['tor_research']['mode'] == 'KNOWN_ONION_ONLY'
    assert cfg['tor_research']['authorized_only'] is True


def test_known_onion_is_classified_and_not_directly_crawled_without_tor_transport():
    from marketradar.source_discovery import SourceDiscoveryEngine
    onion = 'http://exampleexampleexampleexampleexampleexampleexampleexampleexampleexample.onion/'
    cfg = {
        'queries': [],
        'tor_research': {
            'mode': 'KNOWN_ONION_ONLY',
            'authorized_only': True,
            'operator_supplied_onion_urls': [onion],
        },
        'deep_web_research': {'operator_supplied_urls': []},
        'max_crawl_pages_per_cycle': 1,
    }
    e = SourceDiscoveryEngine([], cfg)
    result = e.discover(False, False)
    assert result['candidates']
    candidate = result['candidates'][0]
    assert candidate['network_surface'] == 'DARK_WEB'
    assert candidate['transport_requirement'] == 'TOR'


def test_network_surface_does_not_mislabel_normal_search_results_as_deep_web():
    from marketradar.source_discovery import SourceDiscoveryEngine
    class FakeSearch:
        provider = 'fake'
        def available(self): return True
        def search(self, query, limit):
            return [{'title':'Web freelance projects','url':'https://example.com/jobs','snippet':'Android developer project'}]
    cfg = {'queries':[{'id':'web','country':'Global','region':'Global','language':'multi','family':'freelance','q':'Android freelance project'}], 'max_crawl_pages_per_cycle':0}
    result = SourceDiscoveryEngine([], cfg, FakeSearch()).discover(False, True)
    assert result['candidates'][0]['network_surface'] == 'OPEN_WEB'

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

from marketradar.source_discovery import SourceDiscoveryEngine


def test_platform_linked_website_is_discovered_from_indexed_evidence():
    engine = SourceDiscoveryEngine(catalog_records=[], query_config={"queries": []})
    discovered, evidence = {}, []
    item = {
        "url": "https://www.linkedin.com/posts/example",
        "title": "Python developer community",
        "snippet": "More projects at https://example-opportunities.test/jobs",
    }
    plan = {"id": "social_jobs", "family": "jobs", "platform": "linkedin", "country": "Global", "region": "Global", "language": "en", "q": "python jobs"}
    engine._bridge_linked_web_endpoints(item, plan, discovered, evidence)
    assert "example-opportunities.test" in discovered
    candidate = discovered["example-opportunities.test"]
    assert candidate["linked_from_platform"] == "linkedin"
    assert candidate["discovery_method"] == "platform_linked_website"
    assert any(e["method"] == "platform_linked_website" for e in evidence)


def test_protected_platform_endpoint_is_not_promoted_as_companion_website():
    engine = SourceDiscoveryEngine(catalog_records=[], query_config={"queries": []})
    discovered, evidence = {}, []
    item = {
        "url": "https://www.linkedin.com/posts/example",
        "title": "LinkedIn post",
        "snippet": "See https://www.linkedin.com/company/example",
    }
    plan = {"id": "social", "family": "social", "platform": "linkedin", "country": "Global", "region": "Global", "language": "en", "q": "linkedin"}
    engine._bridge_linked_web_endpoints(item, plan, discovered, evidence)
    assert not discovered
    assert not evidence

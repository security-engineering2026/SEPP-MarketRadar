
    # The static registry is a baseline, not the ceiling. Feed the gate with
    # reviewed discovery catalogs as well, then verify every added candidate before
    # counting it. This prevents registry-count inflation while allowing stale
    # candidates to be replaced by newly discovered, independently verified sources.
    try:
        from marketradar.source_discovery import SourceDiscoveryEngine
        catalog_path = ROOT / "config" / "discovery_catalogs.json"
        query_path = ROOT / "config" / "discovery_queries.json"
        catalogs = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else []
        queries = json.loads(query_path.read_text(encoding="utf-8")) if query_path.exists() else {}
        discovery = SourceDiscoveryEngine(
            catalog_records=catalogs,
            query_config=queries,
            search_provider=WebSearchProvider(timeout=8),
            timeout=8,
        ).discover(include_catalogs=True, include_search=False)
        existing_hosts = {
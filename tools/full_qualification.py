
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
            (urlparse(str(x.get("base_url") or "")).hostname or "").lower().rstrip(".")
            for x in records
            if x.get("base_url")
        }
        discovered = []
        for candidate in discovery.get("candidates", []):
            host = (urlparse(str(candidate.get("base_url") or "")).hostname or "").lower().rstrip(".")
            if not host or host in existing_hosts:
                continue
            existing_hosts.add(host)
            discovered.append(candidate)
        # Keep the qualification bounded even if a catalog grows unexpectedly.
        discovered = discovered[:2000]
        if discovered:
            records = records + discovered
    except Exception:
        # Discovery is an enrichment lane; the baseline registry remains fully
        # testable if a catalog itself is temporarily unavailable.
        discovered = []

    selected = records
    with tempfile.TemporaryDirectory(prefix="mr-sources-") as td:
        conn = connect(Path(td) / "qualification.db")
        sync_source_contracts(conn, selected)
        engine = SourceVerificationEngine(
            conn,
            selected,
            timeout=float(os.environ.get('MR_SOURCE_VERIFY_TIMEOUT', '15')),
            max_workers=int(os.environ.get('MR_SOURCE_VERIFY_WORKERS', '24')),
            max_policy_pages=1,
            surface_scan_pages=2,
            search_provider=WebSearchProvider(timeout=8),
            http_retries=0,
        )
        results = engine.verify([x["name"] for x in selected])
        confirmed = sum(x.get("source_verification_state") == "LIVE_CONFIRMED" for x in results)
        dead = sum(x.get("source_verification_state") == "DEAD" for x in results)
        error_counts = {}
        for item in results:
            if item.get("source_verification_state") != "DEAD":
                continue
            error = str(item.get("error") or "UNKNOWN_ERROR")
            error_counts[error] = error_counts.get(error, 0) + 1
        top_errors = sorted(error_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
        conn.close()

    return gate(
        "LIVE_SOURCE_SCALE_500",
        "PASS" if confirmed >= limit else "OPEN",
        {
            "candidate_registry": len(records),
            "catalog_discovered_candidates": len(discovered),
            "checked": len(results),
            "live_confirmed": confirmed,
            "dead": dead,
            "other": len(results) - confirmed - dead,
            "top_dead_errors": [{"error": k, "count": v} for k, v in top_errors],
            "criterion": f"{limit} LIVE_CONFIRMED sources",
            "method": "all current registry candidates verified; no first-N shortcut",
        },
    )

def live_acquisition_sample_gate(sample_size=20):
    from marketradar.db import connect, sync_source_contracts
    from marketradar.runtime import MarketRadarRuntime
    from marketradar.source_registry import load_source_records
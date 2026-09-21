from marketradar.federation import Federation, Source


def test_verify_many_handles_large_registry_without_db_threads():
    sources = [Source(f"S{i:03}", "http://127.0.0.1:1/feed", status="candidate", allow_hosts=("127.0.0.1",))
               for i in range(50)]
    f = Federation(sources, timeout=0.01, max_workers=8, retries=0)
    results = f.verify_many()
    assert len(results) == 50
    assert all(r["status"] == "ERROR" for r in results)
    assert [r["source"] for r in results] == sorted(r["source"] for r in results)


def test_host_boundary_is_preserved():
    f = Federation([Source("A", "https://example.com/feed", allow_hosts=("example.com",))])
    try:
        f.fetch("A", "https://evil.example/feed")
    except ValueError as exc:
        assert str(exc) == "HOST_BOUNDARY_BLOCK"
    else:
        raise AssertionError("host boundary was bypassed")


def test_verify_many_reports_progress():
    from marketradar.federation import Federation, Source
    seen = []
    f = Federation([Source("x", "http://127.0.0.1:1", allow_hosts=("127.0.0.1",))], retries=0, timeout=0.01)
    results = f.verify_many(progress_callback=seen.append)
    assert len(results) == 1
    assert len(seen) == 1
    assert seen[0]["source"] == "x"


def test_www_redirect_variant_stays_within_host_boundary():
    f = Federation([Source("A", "https://www.example.com/feed", allow_hosts=("www.example.com",))])
    assert f._validate_target(f.sources["A"], "https://example.com/feed").hostname == "example.com"
    try:
        f._validate_target(f.sources["A"], "https://api.example.com/feed")
    except ValueError as exc:
        assert str(exc) == "HOST_BOUNDARY_BLOCK"
    else:
        raise AssertionError("arbitrary subdomain was allowed")

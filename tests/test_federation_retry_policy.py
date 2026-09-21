from urllib.error import HTTPError
from marketradar.federation import Federation, Source
from marketradar.source_verification import SourceVerificationEngine


def _fed(retries=2):
    return Federation(
        [Source("demo", "https://example.com")],
        timeout=0.1,
        max_workers=1,
        retries=retries,
    )


def test_http_403_is_not_retried(monkeypatch):
    fed = _fed(retries=3)
    calls = {"n": 0}

    def fail(_source, _target):
        calls["n"] += 1
        raise HTTPError("https://example.com", 403, "Forbidden", {}, None)

    monkeypatch.setattr(fed, "_open_once", fail)
    try:
        fed.fetch("demo")
    except HTTPError as exc:
        assert exc.code == 403
    else:
        raise AssertionError("expected HTTPError")
    assert calls["n"] == 1


def test_transient_503_is_retried(monkeypatch):
    fed = _fed(retries=2)
    calls = {"n": 0}

    def fail(_source, _target):
        calls["n"] += 1
        raise HTTPError("https://example.com", 503, "Unavailable", {}, None)

    monkeypatch.setattr(fed, "_open_once", fail)
    try:
        fed.fetch("demo")
    except HTTPError as exc:
        assert exc.code == 503
    else:
        raise AssertionError("expected HTTPError")
    assert calls["n"] == 3


def test_source_verification_can_disable_http_retries():
    records = [{"name": "demo", "base_url": "https://example.com"}]
    engine = SourceVerificationEngine(
        None,
        records,
        max_workers=1,
        search_provider=type("NoSearch", (), {"available": lambda self: False})(),
        http_retries=0,
    )
    assert engine.http.retries == 0


def test_source_verification_default_retries_remain_backward_compatible():
    records = [{"name": "demo", "base_url": "https://example.com"}]
    engine = SourceVerificationEngine(
        None,
        records,
        max_workers=1,
        search_provider=type("NoSearch", (), {"available": lambda self: False})(),
    )
    assert engine.http.retries == 2

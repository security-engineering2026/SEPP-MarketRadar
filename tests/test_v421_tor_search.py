import pytest
from marketradar.tor_search import search_onion
from marketradar.tor_transport import TorAccessError


def test_tor_search_requires_explicit_config(monkeypatch):
    monkeypatch.delenv("SEPP_TOR_SEARCH_URL", raising=False)
    with pytest.raises(TorAccessError, match="TOR_SEARCH_URL_NOT_CONFIGURED"):
        search_onion("freelance developer project")


def test_tor_search_rejects_non_onion_endpoint(monkeypatch):
    monkeypatch.setenv("SEPP_TOR_SEARCH_URL", "https://example.com/search")
    with pytest.raises(TorAccessError, match="TOR_SEARCH_ENDPOINT_MUST_BE_ONION"):
        search_onion("freelance developer project")


def test_tor_search_blocks_high_risk_queries(monkeypatch):
    monkeypatch.setenv("SEPP_TOR_SEARCH_URL", "http://search.example.onion")
    with pytest.raises(TorAccessError, match="TOR_QUERY_POLICY_BLOCK"):
        search_onion("stolen account credentials")

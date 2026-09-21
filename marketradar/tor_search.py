from __future__ import annotations

"""Opt-in Tor search against a configured onion search endpoint.

The endpoint must be explicitly configured by the operator. The module does
not enumerate hidden services or follow arbitrary onion links.
"""

import json
import os
from urllib.parse import urlencode, urlparse

from .tor_transport import TorAccessError


def search_onion(query: str, limit: int = 10) -> list[dict]:
    endpoint = os.environ.get("SEPP_TOR_SEARCH_URL", "").strip()
    if not endpoint:
        raise TorAccessError("TOR_SEARCH_URL_NOT_CONFIGURED")
    host = (urlparse(endpoint).hostname or "").lower().rstrip(".")
    if not host.endswith(".onion"):
        raise TorAccessError("TOR_SEARCH_ENDPOINT_MUST_BE_ONION")
    if not query.strip():
        return []
    blocked = ("credentials", "password dump", "stolen account", "credit card", "ransomware", "weapons", "drugs", "malware sale")
    if any(term in query.lower() for term in blocked):
        raise TorAccessError("TOR_QUERY_POLICY_BLOCK")
    try:
        import requests
        proxy = os.environ.get("SEPP_TOR_PROXY", "socks5h://127.0.0.1:9050")
        response = requests.get(
            endpoint.rstrip("/") + "/search?" + urlencode({"q": query, "limit": min(max(limit, 1), 20)}),
            proxies={"http": proxy, "https": proxy},
            timeout=20,
            headers={"User-Agent": "SEPP-MarketRadar/16.1.1 TorResearch"},
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise TorAccessError(f"TOR_SEARCH_FAILED:{type(exc).__name__}:{exc}") from exc
    rows = payload.get("results", []) if isinstance(payload, dict) else []
    return [
        {
            "title": str(x.get("title", "")),
            "url": str(x.get("url", "")),
            "snippet": str(x.get("snippet", x.get("content", ""))),
            "transport": "tor",
            "scope": "configured_search_endpoint",
        }
        for x in rows[:20]
        if isinstance(x, dict)
    ]

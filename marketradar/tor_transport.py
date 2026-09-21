from __future__ import annotations

"""Constrained Tor/onion discovery transport.

This is a research transport, not an illicit-market crawler. It only fetches
explicitly supplied .onion URLs, requires Tor to be reachable locally, and
does not discover or traverse arbitrary onion directories automatically.
"""

import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class TorAccessError(RuntimeError):
    pass


def validate_onion_url(url: str) -> str:
    p = urlparse(url)
    host = (p.hostname or "").lower().rstrip(".")
    if p.scheme not in {"http", "https"} or not host.endswith(".onion"):
        raise TorAccessError("ONION_URL_REQUIRED")
    if p.username or p.password:
        raise TorAccessError("ONION_CREDENTIALS_NOT_ALLOWED")
    return url


def fetch_known_onion(url: str, timeout: int = 20, max_bytes: int = 300_000) -> dict:
    url = validate_onion_url(url)
    proxy = os.environ.get("SEPP_TOR_PROXY", "socks5h://127.0.0.1:9050")
    try:
        import requests
        with requests.Session() as session:
            response = session.get(
                url,
                proxies={"http": proxy, "https": proxy},
                timeout=timeout,
                headers={"User-Agent": "SEPP-MarketRadar/16.1.1 TorResearch"},
            )
            body = response.content[:max_bytes]
            return {
                "url": url,
                "status": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "bytes": len(body),
                "body": body,
                "transport": "tor",
                "scope": "known_onion_only",
            }
    except Exception as exc:
        raise TorAccessError(f"TOR_FETCH_FAILED:{type(exc).__name__}:{exc}") from exc

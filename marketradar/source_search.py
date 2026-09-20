from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import urllib.error


class SearchProviderError(RuntimeError):
    pass


class WebSearchProvider:
    """Small, provider-neutral web search client used by source discovery.

    It never scrapes a search engine result page. A supported search API must be
    configured explicitly. This keeps discovery reproducible and avoids turning
    the product into an undocumented dependency on a search engine's HTML UI.
    """

    def __init__(self, provider=None, timeout=15):
        self.provider = (provider or os.environ.get("MARKETRADAR_SEARCH_PROVIDER", "auto")).lower()
        self.timeout = timeout
        self.brave_key = os.environ.get("BRAVE_SEARCH_API_KEY")
        self.bing_key = os.environ.get("BING_SEARCH_API_KEY")
        self.serper_key = os.environ.get("SERPER_API_KEY")
        self.searxng_url = os.environ.get("SEARXNG_URL", "").rstrip("/")

    def available(self):
        if self.provider == "brave":
            return bool(self.brave_key)
        if self.provider == "bing":
            return bool(self.bing_key)
        if self.provider == "serper":
            return bool(self.serper_key)
        if self.provider == "searxng":
            return bool(self.searxng_url)
        return bool(self.brave_key or self.bing_key or self.serper_key or self.searxng_url)

    def _get(self, url, headers=None):
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "SEPP-MarketRadar/15.1.0 source-discovery"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise SearchProviderError(str(exc)) from exc

    def search(self, query, limit=10):
        if self.provider in {"auto", "brave"} and self.brave_key:
            url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": min(limit, 20)})
            payload = json.loads(self._get(url, {"Accept": "application/json", "X-Subscription-Token": self.brave_key}))
            return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("description", "")} for x in payload.get("web", {}).get("results", [])]
        if self.provider in {"auto", "bing"} and self.bing_key:
            url = "https://api.bing.microsoft.com/v7.0/search?" + urllib.parse.urlencode({"q": query, "count": min(limit, 50), "responseFilter": "Webpages"})
            payload = json.loads(self._get(url, {"Ocp-Apim-Subscription-Key": self.bing_key}))
            return [{"title": x.get("name", ""), "url": x.get("url", ""), "snippet": x.get("snippet", "")} for x in payload.get("webPages", {}).get("value", [])]
        if self.provider in {"auto", "searxng"} and self.searxng_url:
            url = self.searxng_url + "/search?" + urllib.parse.urlencode({"q": query, "format": "json", "categories": "general", "language": "all"})
            payload = json.loads(self._get(url, {"Accept": "application/json", "User-Agent": "SEPP-MarketRadar/15.1.0"}))
            return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("content", ""), "engines": x.get("engines", [])} for x in payload.get("results", [])[:min(limit, 50)]]
        if self.provider in {"auto", "serper"} and self.serper_key:
            body = json.dumps({"q": query, "num": min(limit, 20)}).encode()
            req = urllib.request.Request("https://google.serper.dev/search", data=body, headers={"Content-Type": "application/json", "X-API-KEY": self.serper_key})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            except urllib.error.URLError as exc:
                raise SearchProviderError(str(exc)) from exc
            return [{"title": x.get("title", ""), "url": x.get("link", ""), "snippet": x.get("snippet", "")} for x in payload.get("organic", [])]
        raise SearchProviderError("NO_SEARCH_PROVIDER_CONFIGURED")

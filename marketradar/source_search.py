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

    def _search_searxng(self, query, limit, language=None):
        params = {"q": query, "format": "json", "categories": "general", "language": language or "all"}
        url = self.searxng_url + "/search?" + urllib.parse.urlencode(params)
        payload = json.loads(self._get(url, {"Accept": "application/json", "User-Agent": "SEPP-MarketRadar/15.1.0"}))
        if not isinstance(payload, dict): raise SearchProviderError("INVALID_JSON_PAYLOAD")
        rows = payload.get("results", [])
        if not isinstance(rows, list): raise SearchProviderError("INVALID_RESULTS_PAYLOAD")
        out = []
        for x in rows[:min(limit, 50)]:
            if not isinstance(x, dict): continue
            title, target = x.get("title"), x.get("url")
            if not isinstance(title, str) or not isinstance(target, str) or not target: continue
            out.append({"title": title, "url": target, "snippet": x.get("content", "") if isinstance(x.get("content", ""), str) else "", "engines": x.get("engines", []) if isinstance(x.get("engines", []), list) else [], "_provider": "searxng"})
        return out

    def _search_one(self, provider, query, limit, language=None):
        if provider == "searxng": return self._search_searxng(query, limit, language)
        if provider == "brave":
            url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": min(limit, 20)})
            payload = json.loads(self._get(url, {"Accept": "application/json", "X-Subscription-Token": self.brave_key}))
            return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("description", ""), "_provider": "brave"} for x in payload.get("web", {}).get("results", []) if isinstance(x, dict)]
        if provider == "bing":
            url = "https://api.bing.microsoft.com/v7.0/search?" + urllib.parse.urlencode({"q": query, "count": min(limit, 50), "responseFilter": "Webpages"})
            payload = json.loads(self._get(url, {"Ocp-Apim-Subscription-Key": self.bing_key}))
            return [{"title": x.get("name", ""), "url": x.get("url", ""), "snippet": x.get("snippet", ""), "_provider": "bing"} for x in payload.get("webPages", {}).get("value", []) if isinstance(x, dict)]
        if provider == "serper":
            body = json.dumps({"q": query, "num": min(limit, 20)}).encode()
            req = urllib.request.Request("https://google.serper.dev/search", data=body, headers={"Content-Type": "application/json", "X-API-KEY": self.serper_key})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp: payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            except urllib.error.HTTPError as exc: raise SearchProviderError(f"HTTP_{exc.code}") from exc
            except (urllib.error.URLError, TimeoutError) as exc: raise SearchProviderError(str(exc)) from exc
            return [{"title": x.get("title", ""), "url": x.get("link", ""), "snippet": x.get("snippet", ""), "_provider": "serper"} for x in payload.get("organic", []) if isinstance(x, dict)]
        raise SearchProviderError("UNKNOWN_SEARCH_PROVIDER")

    def _configured_provider_order(self):
        if self.provider != "auto": return [self.provider]
        return [p for p, configured in (("brave", self.brave_key), ("bing", self.bing_key), ("searxng", self.searxng_url), ("serper", self.serper_key)) if configured]

    def search(self, query, limit=10, language=None):
        providers = self._configured_provider_order()
        if not providers: raise SearchProviderError("NO_SEARCH_PROVIDER_CONFIGURED")
        errors = []
        for provider in providers:
            try:
                rows = self._search_one(provider, query, limit, language)
                if rows: return rows
                if self.provider != "auto": return []
            except (SearchProviderError, json.JSONDecodeError, ValueError, KeyError) as exc:
                errors.append(f"{provider}:{type(exc).__name__}:{exc}")
                if self.provider != "auto": raise SearchProviderError(errors[-1]) from exc
        raise SearchProviderError("SEARCH_FEDERATION_FAILED:" + "|".join(errors))

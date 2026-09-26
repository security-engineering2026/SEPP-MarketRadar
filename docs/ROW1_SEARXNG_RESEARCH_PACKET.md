# Row 1 Research Packet — SearXNG / Search Federation

Date: 2026-09-26
Queue row: 1
Execution rule: Baseline-first / Evidence-first / Gap-only

## AS-IS finding

The Windows baseline already contains a provider-neutral `WebSearchProvider`, explicit SearXNG support, federation fallback, language propagation, normalized result fields and downstream provider provenance persistence. Existing tests already cover language propagation, malformed JSON, fallback/provenance and discovery language propagation.

Therefore this row is **not a rebuild**. The identified implementation gap was explicit SearXNG pagination: the provider accepted language/limit but had no page parameter. That gap was completed by adding an optional `page` argument and forwarding SearXNG's documented `pageno` parameter. Existing callers remain compatible.

## Research sources (non-GitHub)

1. SearXNG Search API — https://docs.searxng.org/dev/search_api — q, categories, language, pageno, format, time_range.
2. SearXNG Search processors — https://docs.searxng.org/src/searx.search.processors.html — request parameters and online processor behavior.
3. SearXNG JSON Engine — https://docs.searxng.org/dev/engines/json_engine.html — JSON result mapping and paging configuration.
4. SearXNG engine overview — https://docs.searxng.org/dev/engines/engine_overview.html — adapter/provider architecture.
5. SearXNG engine loader — https://docs.searxng.org/dev/engines/engines.html — engine defaults including paging and language support.
6. SearXNG search settings — https://docs.searxng.org/admin/settings/settings_search.html — language, paging, JSON format, failure suspension.
7. SearXNG configured engines — https://docs.searxng.org/user/configured_engines.html — engine capabilities and paging/locale metadata.
8. SearXNG search syntax — https://docs.searxng.org/user/search-syntax.html — language/engine/category selection semantics.
9. SearXNG administration API — https://docs.searxng.org/admin/api.html — instance configuration/locale visibility.
10. SearXNG developer documentation — https://docs.searxng.org/dev/index.html — request/response and engine implementation boundaries.
11. SearXNG Bing engine documentation — https://docs.searxng.org/dev/engines/online/bing.html — locale handling and paging limitations.
12. OpenSearch search documentation — https://opensearch.org/docs/latest/search-plugins/searching-data/ — provider-independent search/query pattern reference.
13. Microsoft Bing Web Search API documentation — https://learn.microsoft.com/en-us/bing/search-apis/bing-web-search/overview — API-oriented web search integration reference.
14. Google Custom Search JSON API documentation — https://developers.google.com/custom-search/v1/overview — structured search API and pagination reference.
15. Brave Search API documentation — https://api.search.brave.com/app/documentation/web-search/get-started — structured search API reference.
16. Serper API documentation — https://serper.dev/ — structured Google-search result API reference.
17. Tavily API documentation — https://docs.tavily.com/ — search API and result retrieval reference.
18. Exa API documentation — https://docs.exa.ai/reference/search — structured search/retrieval reference.

## Comparable software/products reviewed

1. SearXNG — self-hosted metasearch/federation; adopted adapter/provenance and explicit language/paging semantics.
2. OpenSearch — search backend; adopted explicit query/pagination separation.
3. Typesense — https://typesense.org/docs/29.0/api/search.html — adopted explicit page/per_page contract as a comparable pagination model.
4. Meilisearch — https://www.meilisearch.com/docs/reference/api/search — comparable paginated structured search API.
5. Elasticsearch — https://www.elastic.co/guide/en/elasticsearch/reference/current/search-your-data.html — comparable explicit search request/result model.
6. Algolia — https://www.algolia.com/doc/api-reference/api-methods/search/ — comparable structured multi-index search model.
7. Brave Search API — structured provider API with explicit result limits.
8. Bing Web Search API — structured provider API with pagination/locale concerns.
9. Google Custom Search JSON API — structured provider API with explicit paging.
10. Serper — structured provider aggregation with normalized JSON result consumption.

## Patterns adopted / rejected

### Adopted
- Keep a provider-neutral interface so downstream discovery is not coupled to SearXNG.
- Preserve provider provenance in normalized results.
- Pass search language explicitly.
- Pass page number explicitly rather than encoding pagination into query text.
- Keep provider-specific behavior inside the provider adapter.
- Preserve strict explicit-provider mode and sequential fallback in auto mode.

### Rejected
- Scraping SearXNG HTML UI instead of its documented API.
- Treating result count as proof of source health.
- Rebuilding the existing provider/federation layer.
- Hiding provider failures by changing environments.

## Repository impact

Changed:
- `marketradar/source_search.py`: added optional `page` argument and SearXNG `pageno` propagation.
- `tests/test_search_federation.py`: added regression test for language + pagination.

Preserved:
- Existing provider-neutral architecture.
- Existing language propagation.
- Existing fallback behavior.
- Existing `_provider` provenance consumed by discovery intelligence persistence.

## PASS evidence contract

This research packet is not product PASS by itself.

Row 1 PASS requires:
1. focused regression tests green;
2. full regression suite green;
3. Windows CI evidence;
4. a real configured SearXNG request proving query → JSON → normalized result → provider provenance;
5. language propagation proof;
6. pagination proof;
7. malformed/non-JSON/error handling proof;
8. fallback proof where auto federation is configured;
9. no contradiction with existing baseline evidence.

Current state at packet creation: implementation/test changes are committed, but live runtime evidence is still required.

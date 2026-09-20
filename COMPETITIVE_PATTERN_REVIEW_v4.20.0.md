# Competitive Pattern Review — v4.20.0

MarketRadar is not a direct clone of one product. It sits at the intersection of four adjacent systems: federated search, web extraction, browser automation, and autonomous workflow orchestration.

## 1. SearXNG — search federation

Useful pattern:
- multiple engines behind one interface
- engine/category/language selection
- search syntax and time-range controls
- HTTP API returning normalized results

MarketRadar adoption:
- provider-neutral `WebSearchProvider`
- SearXNG adapter
- operator-aware QueryPlanner
- country/language rotation

Next improvement borrowed from this pattern:
- provider/engine health, latency, result yield and cost should become first-class routing metrics.

## 2. Firecrawl — web context pipeline

Useful pattern:
- Search → Scrape → Parse → Crawl → Map → Interact
- one normalized web-context boundary
- production-oriented extraction and monitoring

MarketRadar adoption:
- search result → bounded page crawl → outbound-link discovery
- raw response preservation
- evidence/provenance persistence

Next improvement:
- separate `Search`, `Extract`, `Map`, and `Interact` capabilities instead of letting discovery own all crawling behavior.

## 3. Browser Use — browser action layer

Useful pattern:
- real browser action space
- navigation/click/type/screenshot
- recovery loops
- form filling
- local/self-hosted execution

MarketRadar adoption:
- guided browser application path
- application queue optimized for fast legitimate action
- no silent external submission

Next improvement:
- source-specific browser adapters with stable selectors and explicit authorization policies.

## 4. OpenHands — orchestration/control plane

Useful pattern:
- separate agent server/control center from UI
- local/self-hosted execution
- scheduled automations
- multiple backends
- explicit repository/responsibility boundaries

MarketRadar adoption:
- Runtime separated from Desktop UI
- scheduled discovery/federation
- provider-neutral interfaces
- approval broker for external actions

Next improvement:
- make command orchestration a service layer rather than a large CLI function.

## 5. Unified provider adapters

The ecosystem increasingly normalizes different web-search providers behind one interface. MarketRadar already follows this pattern instead of binding the product to one vendor.

## Competitive conclusion

MarketRadar should **not** try to become a generic browser agent or generic search engine.

Its differentiator is the complete decision chain:

```text
Discover
  → Verify
  → Understand Opportunity
  → Fit to User Skill Level
  → Rank
  → Select
  → Prepare
  → Fastest Legitimate Application Path
  → Human/Authorized Submission
  → Outcome
  → Learn
```

Source discovery is an input to this chain, not the product's final objective.

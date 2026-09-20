# SEPP-MarketRadar v4.18.0 — Deep Adversarial Discovery Audit

## Objective

Move source discovery from a registry-expansion model to a software-driven discovery model that can find previously unknown sources without a human naming them first.

## Architectural changes

1. **200+ geographic coverage** — 249 ISO-3166 country/territory entities are represented in `config/coverage_entities.json`. Discovery rotates through country batches rather than requiring manual country additions.
2. **Search as a discovery engine** — query planning now combines exact phrases, normal keywords, policy terms, forum/community terms and hashtag-oriented queries. Search-provider access is explicit and provider-neutral.
3. **Community intelligence** — public forum/community/review pages are first-class discovery inputs. A forum result can itself be registered as a community source, while outbound public links discovered on the page can become new platform candidates.
4. **Evidence/provenance** — every discovery observation can be persisted in `source_discovery_evidence`, preserving query, provider, country, language, result URL, title/snippet and discovery method.
5. **Multi-endpoint source model** — `source_endpoints` stores home, terms, KYC, payout, API and community surfaces independently. Verification is no longer limited to the homepage.
6. **Autonomous verification loop** — discovery candidates are imported into the dynamic registry, verified, policy-classified, and can feed the next discovery cycle. No candidate becomes execution-ready merely because it was discovered.

## Adversarial cases covered

- Source not present in the shipped registry.
- Forum result mentioning a platform but not being the platform itself.
- Outbound platform link from a community discussion.
- Duplicate host/name collision.
- Unknown Iran eligibility.
- Explicit Iran restriction.
- KYC required.
- Payment/payout evidence present without permission inference.
- Multiple policy endpoints.
- Search provider unavailable.
- Search provider returns malformed/empty results.
- Country rotation beyond the initial country set.
- Dynamic sources surviving baseline registry synchronization.

## Evidence standard

The product must distinguish:

`DISCOVERED` → `LIVE_CONFIRMED` → policy state → execution gate

Discovery is not authorization. Silence is not ALLOW. A search snippet is a locator/evidence lead, not by itself proof of current policy.

## Test results

- `pytest -q`: PASS — 116 tests, 1 skip.
- `python -m compileall -q marketradar tools`: PASS.
- `python tools/product_audit.py`: PASS with coverage-target warnings only.
- `python tools/release_audit.py`: PASS with `errors=[]`.
- Source automation laboratory: PASS — 3 injected unknown sources, 6 explicit Iran restrictions blocked, 2 allowed/research-safe outcomes, 1 unknown-safe outcome, 0 execution-ready.
- Offline autonomous cycle: executed safely; with no configured external search provider it produced zero fabricated candidates and recorded the provider limitation instead.

## Network boundary

The current development environment cannot be treated as proof of live Internet-wide discovery. Real Internet discovery requires a configured, authorized search provider and outbound network access. The software records this as an operational limitation rather than fabricating results.

## Remaining gaps

- Full live 200+ geographic search requires a configured search provider and a production scheduler.
- Search-provider quotas/rate limits must be managed as runtime resources.
- Source-specific adapters still need to be earned by verification; generic HTML is not a universal runtime contract.
- 500+ operational sources remains a runtime target, not a promise based on registry count.

## Release decision

v4.18.0 is the correct architectural baseline for the next development stage. It is not acceptable to claim that the system has already discovered the whole Internet or verified hundreds of live sources in this offline environment.

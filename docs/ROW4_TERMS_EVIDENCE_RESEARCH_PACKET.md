# Row 4 Research Packet — Active Source Terms/Legal Evidence Closure

Date: 2026-10-26
Queue row: 4 (source gate 38)
Execution rule: Baseline-first / Evidence-first / Gap-only
Status at packet creation: RESEARCH COMPLETE; runtime acceptance remains OPEN until the Windows Row 4 gate passes.

## AS-IS finding

The current acceptance contract is not "the URL exists" or "the source responds". Every source that remains active must have a successfully fetched official Terms/Legal/Privacy page, a non-empty evidence URL, and `terms_status=reviewed`. Search snippets are discovery hints only and cannot themselves be the evidence. HTTP 403 means the request was refused; it does not mean the policy is absent, nor does it justify bypassing the refusal.

The current candidate's Windows workflow previously failed on `Wanted_Korea` with HTTP 403 and then exposed `Jobinja_Iran` as another unresolved source. The Wanted record was updated to declare official policy surfaces on `www.wanted.co.kr` and the official help center. This is a candidate fix, not a PASS claim. The runtime gate is being hardened to continue diagnostics after regression failure, verify persisted state across the three runtime tables, and publish a per-source JSON evidence artifact.

## Research sources (non-GitHub)

Access date for all sources below: 2026-10-26. Sources are not all equivalent in authority: standards and primary product/legal documentation are treated as primary; vendor policies are comparative practice, not legal advice.

1. **IETF RFC 9309 — Robots Exclusion Protocol** — https://www.rfc-editor.org/rfc/rfc9309.html — Standard. Robots rules are crawler guidance, not access authorization; errors and caching have explicit semantics. Decision: do not treat robots.txt or a public homepage as proof of legal permission; retain host boundaries and explicit source policy evidence.
2. **IETF RFC 9110 — HTTP Semantics** — https://www.rfc-editor.org/rfc/rfc9110.html — Standard. HTTP 403 means the server understood but refuses the request; repeating the same request without a meaningful change should not be assumed to succeed. Decision: 403 remains unresolved evidence, never auto-promote a source to reviewed.
3. **MDN — 403 Forbidden** — https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/403 — Technical reference. A 403 is an access refusal and may be application-policy related. Decision: do not label a policy page verified merely because a URL is configured.
4. **Google Search Central — Introduction to robots.txt** — https://developers.google.com/search/docs/crawling-indexing/robots/intro — Primary search-engine documentation. Robots instructions govern crawling behavior, but do not substitute for authorization or terms. Decision: keep crawling policy and terms evidence as distinct checks.
5. **Scrapy — RobotsTxtMiddleware** — https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#robotstxtmiddleware — Product documentation. Crawlers can enforce robots exclusions as a first-class middleware. Decision: access-policy checks belong in the acquisition boundary, not as a note that operators may overlook.
6. **Scrapy — AutoThrottle** — https://docs.scrapy.org/en/latest/topics/autothrottle.html — Product documentation. Crawling rate should adapt to observed latency and avoid overloading sites. Decision: preserve bounded concurrency, page budgets and request timeouts during source review.
7. **Cloudflare — HTTP 403 troubleshooting** — https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-403/ — Infrastructure-vendor documentation. 403 can arise from origin permissions or edge security rules. Decision: record exact failures and seek another official public policy surface; do not implement challenge evasion.
8. **Apify — Acceptable Use Policy** — https://docs.apify.com/legal/acceptable-use-policy — Primary platform policy. Prohibits abusive, illegal, deceptive or rights-violating use and permits restrictions. Decision: preserve explicit authorization/scope boundaries and avoid treating public visibility as blanket permission.
9. **Bright Data — Acceptable Use Policy** — https://brightdata.com/acceptable-use-policy — Primary platform policy. Excludes nonpublic information behind login and prohibits unlawful or abusive use. Decision: keep authenticated/private data outside this Row 4 public-policy fetch path.
10. **Oxylabs — Acceptable Use Policy** — https://oxylabs.io/legal/acceptable-use-terms — Primary platform policy. Requires lawful use and compliance with relevant site terms and third-party rights; distinguishes public data from nonpublic data. Decision: require source-specific policy review and do not infer permission from reachability.
11. **Zyte — Terms of Service** — https://www.zyte.com/terms-policies/terms-of-service/ — Primary vendor legal terms. Emphasizes lawful/ethical use and responsibility for the legality of extraction. Decision: store the source's actual official terms URL and verification timestamp, not only a registry guess.
12. **Diffbot — Terms of Use** — https://www.diffbot.com/company/terms — Primary vendor legal terms. Explicitly prohibits bypassing robots restrictions and unauthorized scraping. Decision: reject stealth/bypass approaches as a means of closing the gate.
13. **European Commission — GDPR principles** — https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/principles-gdpr/overview_en — Primary regulatory guidance. Personal-data processing needs a lawful basis, transparency and purpose limitation. Decision: Row 4 terms review is a source-policy gate, not a claim that all privacy or jurisdiction questions have been resolved.
14. **Python documentation — urllib.error** — https://docs.python.org/3/library/urllib.error.html — Primary runtime documentation. HTTP failures are represented distinctly from transport failures. Decision: retain status/error evidence and do not collapse 403/404/DNS failures into "reviewed".
15. **Python documentation — urllib.request** — https://docs.python.org/3/library/urllib.request.html — Primary runtime documentation. Request headers, handlers and redirects are explicit transport behavior. Decision: keep fallback transport bounded and validate every target/redirect against allowed policy hosts.

## Comparable software/products/platforms reviewed

1. **Scrapy** — https://docs.scrapy.org/en/latest/ — Open-source crawler framework; adopted explicit robots middleware and bounded crawl behavior.
2. **Apify** — https://docs.apify.com/ — Managed scraping/automation platform; adopted explicit acceptable-use constraints and policy-linked review.
3. **Zyte API** — https://www.zyte.com/zyte-api/ — Managed extraction service; comparator for separating fetch transport from extraction and documenting legal responsibility.
4. **Bright Data Web Scraper API** — https://brightdata.com/products/web-scraper — Managed data collection; comparator for explicit acceptable-use policy and blocked-content handling.
5. **Oxylabs Web Scraper API** — https://oxylabs.io/products/scraper-api — Managed data collection; comparator for source-specific terms and lawful-use constraints.
6. **Diffbot** — https://www.diffbot.com/ — Structured web extraction; comparator for explicit restrictions against bypassing robots controls.
7. **Firecrawl** — https://docs.firecrawl.dev/ — Web extraction API; comparator for bounded scrape requests and structured extraction outputs.
8. **ScrapingBee** — https://www.scrapingbee.com/documentation/ — Web scraping API; comparator for explicit request parameters and transport/error handling.

These products are comparable by workflow (fetch → extract → normalize → record policy/error evidence), not identical in deployment model or legal obligations.

## Patterns adopted / rejected

### Adopted
- Declared official `policy_paths` are tried before generic same-origin guesses.
- Cross-host policy pages require explicit `policy_hosts`; operational acquisition allowlists remain separate.
- A Terms status can become `reviewed` only when a policy page was successfully fetched and its URL is retained.
- HTTP 403/404, DNS errors and transport failures remain visible and unresolved; a search snippet or configured URL is not fetched evidence.
- Acceptance checks complete source coverage, unique source results, non-empty evidence URL, and `reviewed` status for every active source.
- Persisted evidence must agree across `sources`, `source_contracts`, and `source_verification_state`.
- Runtime diagnostics run even if regression tests fail, so the report can identify every unresolved source instead of hiding the runtime result.
- The qualification emits `qualification-artifacts/row4_active_source_terms.json` with per-source status, evidence URLs, timestamps and errors.

### Rejected
- Marking a source reviewed because its URL is configured, its homepage is reachable, or a search engine displays a snippet.
- Treating HTTP 403 as proof that the policy does not exist.
- Bypassing anti-bot challenges, authentication, or a site refusal to obtain a green test.
- Removing a source from the active set without recording the evidence-based reason and reactivation condition.
- Passing the gate from in-memory results while database persistence is missing or inconsistent.
- Treating a unit test as equivalent to the all-active-source live qualification.

## Exact repository impact

- `config/sources.json`: declare official Wanted Korea policy hosts and its official Terms/Privacy/help-center URLs. Do not alter operational host permissions to accommodate policy endpoints.
- `marketradar/source_verification.py`: persist `terms_status` and `terms_evidence_url` consistently to `source_contracts`, in addition to the existing runtime tables.
- `tools/full_qualification.py`: require exact active-source coverage, reviewed status and non-empty fetched evidence; verify database persistence; emit per-source diagnostic evidence.
- `tests/test_v415_source_verification.py`: cover the false-positive case where a source is labelled reviewed but has no evidence URL, and the incomplete-coverage case.
- `.github/workflows/row4-qualification.yml`: run runtime diagnostics even after a regression failure and upload the evidence JSON as a workflow artifact.
- `docs/DEBUG_HANDOFF.md`: update only after actual runtime evidence is available; do not mark Row 4 PASS from this research packet.

## PASS evidence contract

Row 4 can close only when the Windows Row 4 runtime qualification reports:
1. every currently active source checked exactly once;
2. no missing, unexpected or duplicate source results;
3. every active source has a fetched official Terms/Legal/Privacy evidence URL;
4. every active source has `terms_status=reviewed`;
5. the evidence URL and reviewed status persist consistently across `sources`, `source_contracts`, and `source_verification_state`;
6. the uploaded `row4_active_source_terms.json` contains the per-source evidence and no unresolved entries;
7. focused regression and the dedicated Row 4 workflow are green.

A source that refuses policy access must remain unresolved until an alternate official public policy surface is fetched, or be explicitly moved to candidate with a documented reason and reactivation condition. This packet is research input only; it is not runtime PASS evidence.

# Market Radar — 31-Row Execution Contract

**Status:** ACTIVE / NORMATIVE  
**Execution:** Row 3 → Row 31, strictly sequential, evidence-gated, autonomous continuation.

## Binding rule

For every row: inspect existing code first; reuse working capabilities; implement missing behavior; complete incomplete behavior; add missing tests; debug actual failures; run relevant tests and regression/qualification checks. A row is **PASS only when implementation + integration + tests + required runtime evidence + acceptance criteria are satisfied**. Documentation/configuration alone is never PASS. Do not advance until PASS. Do not wait for another user message to continue. If a genuine external dependency makes progress impossible, stop only at that exact blocker and state the single required action.

## PASS gate

A PASS requires, as applicable: production implementation, actual execution-path integration, automated tests, regression safety, runtime evidence for external integrations, persistence/restart behavior, failure handling, and CI/qualification evidence. Mock-only tests do not prove real external integrations.

## Mandatory sequence

| # | Capability | PASS definition |
|---:|---|---|
| 3 | SearXNG / Search Federation | SearXNG is a real Runtime provider with query/language/result parsing/provenance/timeout/error/pagination handling and fallback; tested and runtime-validated. |
| 4 | Global Discovery | Worldwide/extensible source-family and multilingual/country discovery is actually planned and executed; no fixed final source ceiling. |
| 5 | Source Pool >500/1000 | Registry grows beyond 500/1000 with bounded, resumable processing, deduplication and persistence. 500 is benchmark only. |
| 6 | Deep Source Study | Evidence is collected for Iran access, payment, KYC, phone/country restrictions, subscriptions/credits, application limits, intermediaries and relevant policies. |
| 7 | Evidence / Provenance | Material claims have traceable evidence, URL/context, timestamp and confidence/status as applicable. |
| 8 | Iran Compatibility Classification | Evidence-backed compatible/incompatible/unknown/domestic classification; incompatible intelligence retained; domestic KYC/fiat is not a rejection criterion. |
| 9 | Market Intelligence | Repeated observations become actionable intelligence on skills, tasks, tools, budgets, experience and demand trends. |
| 10 | Product Build Specification | Evidence-backed product spec contains problem, source family, capabilities, inputs, outputs, integrations, acceptance criteria, scope, evidence and promotion targets. |
| 11 | User Profile / Skills | Persistent skills, proficiency/percentage, learning level, experience, portfolio, resume, certifications and stretch policy. |
| 12 | Proficiency-aware Matching | Matching respects proficiency/requirements and explains rationale. |
| 13 | Opportunity Matching | Recommendations use documented fit/access/budget/deadline/competition/trust/evidence factors without fabricated experience. |
| 14 | Duplicate / Cross-post Detection | Canonical opportunity links cross-posts while preserving source observations and application paths. |
| 15 | Application Constraints | Credits, paid applications, subscriptions, pending/application limits and similar source constraints are detected, persisted and enforced. |
| 16 | Application Package Generation | Proposal/title/description/CV/portfolio mapping is generated without fabricated experience; required assets are represented. |
| 17 | Application Submission | Authorized/permitted submission paths only; no access-control/CAPTCHA bypass. |
| 18 | Opportunity Lifecycle | Submitted/viewed/message/negotiation/accepted/rejected/expired/etc. states persist and update correctly. |
| 19 | Follow-up / Deadline / Payment Tracking | Deadline, follow-up, delivery and payment state are tracked with authorized automation and source constraints. |
| 20 | Adaptive Search | Adding a skill/tool/product capability changes search through data/configuration/profile state, not code edits. |
| 21 | Social / Community Discovery | Public/indexed/authorized social/community discovery works with provenance and no auth/CAPTCHA/access-control bypass. |
| 22 | Intermediary / Broker Intelligence | Agencies/brokers/indirect routes are discovered and studied with evidence and clear access semantics. |
| 23 | Crypto Opportunity Monitoring | Crypto-paying opportunities are a monitored evidence-backed lane; crypto alone never implies compatibility. |
| 24 | Configurable Red-list | Operational blacklist is configurable, evidence-backed, non-destructive and prevents prohibited execution/recommendation paths. |
| 25 | Continuous Monitoring | Required source lanes/cadences execute, persist state and recover from failures; incompatible foreign market-intelligence lane includes twice-daily scanning. |
| 26 | 1000+ Performance | Processing remains bounded, resumable and observable at 1000+ sources; partial failure does not require restarting the universe. |
| 27 | Windows / SearXNG Runtime Validation | Windows execution validates the actual configured SearXNG path end-to-end. |
| 28 | Full Qualification | Full qualification passes with blocking gates satisfied and no known critical regression. |
| 29 | Tests / Regression | Relevant unit/integration/regression/failure/acceptance tests exist and are green. |
| 30 | UI / End-to-End Product Flow | User can operate profile → discovery → study/classify → match → rationale → application workflow → lifecycle end-to-end. |
| 31 | Final Acceptance / Installable Product | Clean install/build artifact installs, starts, supports core E2E flow, and uninstalls; final evidence confirms Rows 3–30 remain satisfied. |

## Product interpretation

The system is not required to prove that it enumerates every Internet site at one instant. It must provide extensible continuous worldwide discovery with no fixed final source ceiling. Sources include freelance, bug bounty/security work, project/job boards, employers, domestic/local platforms, public/indexed social/community surfaces, classifieds, forums, agencies/brokers/intermediaries and crypto-paying opportunities. Incompatible sources remain available for market intelligence.

**500 is only a qualification/scale benchmark. It is not a product ceiling or completion condition.**

## SearXNG contract

SearXNG must be a real Runtime provider. Its documented API supports HTTP search, `q`, `language`, pagination and JSON output when JSON is enabled. Its search syntax supports language selection and engine/category modifiers. These behaviors must be reflected in implementation/tests.

References:
- https://docs.searxng.org/dev/search_api
- https://docs.searxng.org/user/search-syntax.html

## Autonomous state

After each PASS, record: row number, PASS status, commit(s), tests executed, latest CI/qualification result, remaining defects (if any), and exact next row. This document is the binding execution contract for continuation in later chats.

## Final completion statement

Only after Row 31 PASS may the project be described as **Market Radar — installable and end-to-end qualified against the current product contract**. This means the defined contract is satisfied; future sources/opportunities still require continuous monitoring and maintenance.

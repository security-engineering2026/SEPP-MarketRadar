# SEPP-MarketRadar System Manifest v1.0

Status: normative system contract for `main`.
Baseline: SEPP-MarketRadar v16.1.2.
Purpose: define what the product is allowed to mean, store, decide, execute, report, and claim.

## 1. Mission
MarketRadar is an Opportunity Intelligence and Economic Operations System. It converts heterogeneous market observations into evidence-backed opportunities, decisions, authorized actions, outcomes, and learning.

## 2. Core truth model
The system MUST distinguish:
WORLD -> OBSERVATION -> SNAPSHOT -> EVIDENCE -> CLAIM -> DOMAIN STATE -> DECISION -> ACTION -> OUTCOME -> LEARNING.
Evidence is not truth. UNKNOWN is a valid state. Registration is not verification. Reachability is not capability. Recommendation is not authorization. Payment claim is not payment verification.

## 3. Domain contract
Core domain objects include Source, SourceEndpoint, Observation, Snapshot, Evidence, Claim, Entity, Party, Opportunity, Decision, Approval, Action, Workflow, Outcome, FinancialObservation, LearningSignal.
Each object has explicit identity, state, timestamps, provenance, and versioning where applicable.

## 4. Source registry
The registry may contain discovered, documented, reviewed, verified, degraded, blocked, dead, archived and execution-eligible sources.
A source count MUST never be presented as a verified integration count.

## 5. Source adapter contract
Every executable source integration MUST declare:
adapter, acquisition method, endpoint(s), input/output contract, access scope, authentication needs, policy requirements, rate/size limits, parser/normalizer, failure semantics, verification evidence, and capability maturity.
Generic homepage scraping MUST NOT be represented as a mature integration.

## 6. Capability maturity
Source capability states MUST distinguish at least:
REGISTERED, DISCOVERED, DOCUMENTED, REACHABLE, PARSEABLE, VALIDATED, POLICY_VERIFIED, EXECUTION_READY.
Promotion requires evidence for the next state; no silent promotion.

## 7. Source verification
Verification MUST record HTTP evidence, parsing result, policy evidence, eligibility, KYC, payment evidence, terms evidence, timestamp, confidence, and failure reason.
Verification is time-bounded and must become stale.

## 8. Discovery
Discovery may use catalogs, search engines, public pages, communities and explicit companion/project URLs.
Discovery creates candidates and provenance only; it MUST NOT grant execution authority.

## 9. Acquisition
Acquisition MUST be source-bound, host-bound, size-bound, timeout-bound and retry-aware.
Redirects MUST remain within an explicit auditable host policy.
Secrets and authorization headers MUST never be leaked into untrusted targets.

## 10. Immutable raw evidence
Raw payloads MUST be hashable and replayable.
A snapshot identity MUST include source, URL/endpoint, observation time and content digest.
Raw evidence MUST remain distinguishable from normalized interpretation.

## 11. Observation layer
An observation is what was actually received at a point in time.
Observations MUST preserve source, URL, timestamp, HTTP metadata, content type, digest and acquisition provenance.

## 12. Canonical opportunity
Canonical opportunities are normalized domain objects derived from observations.
Normalization MUST retain links to originating observations/evidence and MUST NOT erase contradictory observations.

## 13. Deduplication
Deduplication MUST operate on stable opportunity identity and observation history, not only title+description hashes.
Conflicting observations MUST be retained and surfaced.

## 14. Entity resolution
Entity resolution MUST support MATCH, POSSIBLE_MATCH and NO_MATCH semantics with confidence and evidence.
Automatic merge MUST be conservative and reversible/auditable.

## 15. Party resolution
Client, employer, agency, buyer, procurement party and intermediary are distinct party roles.
Party relationships MUST preserve evidence and temporal validity.

## 16. Evidence graph
Evidence MUST link source -> observation -> evidence -> claim -> domain object.
Claim-level provenance is mandatory for consequential claims.

## 17. Trust and reputation
Trust is a separate assessment from evidence confidence.
Reputation MUST expose provenance diversity, manipulation signals, confidence and UNKNOWN when evidence is insufficient.

## 18. Eligibility
Eligibility MUST be evaluated independently from payment, KYC, source health and ranking.
Eligibility states include at least ALLOW, REVIEW, BLOCK, UNKNOWN.

## 19. Payment intelligence
Payment method detection is not payment verification.
Payment intelligence MUST distinguish claimed, documented, observed and verified payment paths.

## 20. KYC intelligence
KYC requirements MUST be represented separately from eligibility and payment.
Unknown KYC MUST remain UNKNOWN/REVIEW, not inferred as allowed.

## 21. Policy engine
Policy is deterministic, versioned and auditable.
Policy outcomes MUST include BLOCK, REVIEW, EXECUTE and UNKNOWN.
Policy decisions MUST identify the evidence and policy version used.

## 22. Temporal/change intelligence
Important domain facts MUST be time-aware.
The system MUST support first_seen, last_seen, freshness, expiry/revalidation and contradiction/change detection.

## 23. Intelligence
Intelligence may classify, summarize, cluster, infer and detect demand, competition, TTM, market signals and changes.
AI/heuristics are analytical inputs, not authorities for high-impact authorization decisions.

## 24. Ranking
Ranking MUST remain distinct from policy and decision.
Ranking can prioritize candidates but cannot override BLOCK, UNKNOWN, authorization or hard eligibility constraints.
Ranking should expose major scoring factors and confidence.

## 25. Decision model
A decision is the combination of domain state, evidence, policy, ranking/context and user/profile constraints.
Every consequential decision MUST be reproducible from a decision snapshot.

## 26. Daily Intelligence Center
The product may produce Top 7, Do-Now 3, monitor, blocked and unknown views.
These are views over the decision model, not authority to execute.

## 27. Human approval
Consequential actions require explicit human approval unless an independently defined low-risk policy says otherwise.
Approval MUST be exact-action bound.

## 28. Authorization broker
Authorization binding MUST include target, action, parameters digest, evidence digest, policy version, expiry and one-time nonce/replay protection.
Authorization failure is fail-closed.

## 29. Action model
Actions are stateful transactions with preconditions, execution, result, audit and failure semantics.
An action MUST be idempotent where practical and MUST expose an external reference/result digest where applicable.

## 30. Application lifecycle
Opportunity lifecycle MUST preserve valid state transitions from discovery through application, negotiation, acceptance, delivery and payment.
Invalid transitions MUST fail closed and be auditable.

## 31. Delivery
Delivery MUST record immutable artifact evidence, digest, actor and observation time.
Delivery evidence is not payment evidence.

## 32. Revenue/payment
Revenue recording is a claim/recording step.
Settlement becomes PAID only after explicit payment verification evidence.
Duplicate payment references MUST be rejected.

## 33. Outcome ledger
Submission, response, acceptance, rejection, cancellation, delivery and payment outcomes MUST be recorded.
Outcomes are immutable learning inputs.

## 34. Market learning
The system MUST learn from outcomes, source behavior, party behavior, pricing, TTM, acceptance and revenue.
Learning MUST NOT rewrite historical observations.

## 35. Negative/rejection intelligence
Rejected, blocked, expired and failed opportunities are first-class signals.
The system MUST preserve rejection reasons and use them for future policy/ranking/learning analysis.

## 36. Acquisition fallback
Provider or adapter failure MUST be distinguishable from source absence.
Fallback acquisition MAY improve coverage but MUST preserve provider provenance and confidence differences.

## 37. Scheduler/runtime
Scheduled scans MUST be durable, resumable and observable.
Retry, backoff, timeout, stale detection and recovery state MUST be explicit.

## 38. Security
Security boundaries include host allowlists, SSRF/private-IP controls, secret isolation, signed/bound approvals, replay detection, immutable operational ledgers, parser network isolation and least-privilege action execution.

## 39. Windows product
Windows is the primary product authority.
Portable EXE and installer are product artifacts and require actual Windows build/smoke evidence.
Scripts alone are not a Windows product.

## 40. Android companion
Android is a companion for review, notification, approval and status.
Core authority remains on Windows.
Android MUST NOT become an independent policy/payment authority.

## 41. Observability
Every important stage MUST expose status, timestamps, errors, retries, health and relevant digests.
Operational metrics MUST distinguish attempted, successful, failed, skipped, unknown and not configured.

## 42. Auditability
Consequential state changes and decisions MUST have an audit trail.
Immutable ledgers MUST reject silent mutation/deletion where historical integrity matters.

## 43. Data integrity
Foreign keys/uniqueness/constraints, hashes, idempotency keys and transaction boundaries MUST protect domain invariants.
Historical records MUST remain reconstructable.

## 44. Product UI
UI MUST make the truth model visible: source state, evidence/confidence, eligibility, policy, ranking rationale, approval state, action state and outcome state.
UNKNOWN/REVIEW/BLOCKED MUST NOT visually masquerade as ready.

## 45. Reporting truthfulness
Reports MUST label registered vs discovered vs verified vs execution-ready counts.
Claims about live sources, coverage, production readiness or platform support require corresponding evidence.

## 46. Definition of done
A Manifest requirement is DONE only when:
1. code implements it;
2. regression tests cover it;
3. adversarial/failure behavior is tested where relevant;
4. CI/build evidence exists for environment-specific claims;
5. audit/reporting exposes the state;
6. no contradictory legacy path remains.


## 50. Manifest Amendment A-2026-09-26 — Global Market Universe, Personalized Search and Economic Loop

This amendment makes the intended MarketRadar operating model explicit. It does not reinterpret a source count as verified coverage and does not replace the truth model above.

### 50.1 Global discovery universe

MarketRadar MUST operate as a global discovery system for opportunities in:
- freelance marketplaces and job/project boards;
- bug-bounty, vulnerability-disclosure and security-program platforms;
- direct-employer/project sources where freelance/contract work is offered;
- country-specific and regional marketplaces;
- Iranian/local platforms;
- social and messaging platforms, including Telegram, LinkedIn, X/Twitter, Instagram, Reddit, Rubika, Eitaa, Bale, Soroush Plus and comparable platforms;
- classifieds/service marketplaces such as Divar, Sheypoor and comparable services;
- community forums and discussion sites where users publish experience, recommendations, warnings or opportunity leads;
- intermediary, broker, agency and referral platforms that can expose projects originating from otherwise inaccessible sources;
- any other public or authorized source that can contain relevant paid work, demand signals, project requirements or evidence about platform accessibility.

The discovery universe MUST NOT be restricted to a fixed list of countries, languages, domains or source families. Country and language coverage MUST be extensible and MUST include multilingual discovery.

There is no final fixed number of sources. The 500 figure remains a discovery-pool benchmark only. A registry may grow from hundreds to thousands or more as discovery continues. Source growth MUST be evidence/provenance-backed and MUST NOT be fabricated with placeholders.

### 50.2 Discovery versus source study

For every discovered candidate, MarketRadar SHOULD progress through the capability ladder as evidence permits:
REGISTERED -> DISCOVERED -> REACHABLE -> PARSEABLE -> VALIDATED -> POLICY_VERIFIED -> EXECUTION_READY.

Where technically and legally permitted, source study MUST examine the source's relevant public or authorized surfaces, not only its homepage. Relevant surfaces include:
- registration/login requirements;
- country and jurisdiction restrictions;
- terms, FAQ, help and policy pages;
- project/job/bounty listings;
- payment and payout documentation;
- KYC/identity requirements;
- phone-number and country-code requirements;
- subscription, credits, proposal and application limits;
- source-declared application concurrency limits;
- intermediary/referral structure;
- public community/forum evidence;
- other evidence needed to determine whether a user from Iran can practically use the service.

Silence on a source page MUST NOT be interpreted as Iran compatibility, no-KYC, crypto payout or unrestricted application access. UNKNOWN remains UNKNOWN until evidence changes it.

### 50.3 Iran compatibility, payment and KYC intelligence

For non-Iranian sources, the system MUST independently represent:
- Iran access: ALLOW / BLOCK / REVIEW / UNKNOWN;
- KYC: NOT_REQUIRED / REQUIRED / REVIEW / UNKNOWN, with evidence for the observed requirement;
- payment/payout: fiat, crypto, mixed, other, UNKNOWN, and the specific currencies/networks when documented;
- phone/country-code compatibility;
- registration/access blockers;
- terms/policy evidence and freshness.

Foreign sources that are not usable from Iran MUST NOT be deleted. They MUST be retained in a market-intelligence lane for demand discovery, product/tool ideation, competitive intelligence and indirect-access/intermediary analysis.

For Iranian/domestic sources, the default discovery rule MUST be inclusive: a source MUST NOT be rejected merely because it requires identity verification or uses domestic/fiat payment. KYC/payment information is still recorded for decision support, but it is not by itself a rejection criterion for domestic sources.

### 50.4 Intermediary and indirect-access intelligence

MarketRadar MUST model intermediaries separately from first-party sources.

It MUST be able to identify and monitor cases such as:
- an Iranian intermediary offering access to work originating on an otherwise Iran-incompatible global platform;
- an agency or broker receiving a project and subcontracting or referring work;
- a local platform offering projects denominated or paid in foreign currency;
- a person/company acting as an intermediary between a source and a worker.

Indirect access MUST be reported as a relationship with evidence, not as proof that the original source itself accepts Iranian users.

### 50.5 Market-intelligence lane

Foreign/incompatible sources and other non-executable sources MUST remain useful inputs to demand intelligence.

At least twice per day when online, the system MUST search these sources for:
- recurring requested skills;
- recurring task types and deliverables;
- requested software/tool capabilities;
- budgets/pricing signals where observable;
- required experience/certification/portfolio signals;
- competition and demand changes;
- emerging clusters of unmet demand.

The intelligence layer SHOULD convert recurring demand into an evidence-backed Product Build Specification containing, where supported:
- proposed tool/product name;
- problem statement;
- target user/source family;
- requested capabilities;
- input/output formats;
- required integrations;
- quality/acceptance criteria;
- suggested implementation scope;
- evidence URLs and observations;
- candidate marketplaces/platforms for later promotion or service listing.

AI/LLM output is advisory. It MUST be traceable to the underlying demand evidence and MUST NOT be treated as authoritative policy.

### 50.6 User skill/capability profile

The product MUST expose a user-editable capability profile with per-skill proficiency and optional evidence, including but not limited to Python, Kotlin, Linux and other skills.

The profile MUST support:
- enable/disable skill or capability;
- proficiency level/percentage;
- learning track and current level;
- portfolio/projects;
- resume/CV evidence;
- experience/history;
- certifications where applicable;
- explicit stretch-policy setting.

Recommendation and application generation MUST use the profile. A project MUST NOT be presented as a normal-fit recommendation merely because a skill name matches if its required proficiency, experience, certification or portfolio evidence exceeds the user's configured capability.

Stretch opportunities MUST be visibly marked as stretch/learning candidates rather than silently treated as normal-fit work.

### 50.7 Opportunity matching and recommendation rationale

For each candidate opportunity, the system MUST evaluate, where evidence exists:
- skill fit;
- proficiency fit;
- experience fit;
- portfolio fit;
- KYC/access feasibility;
- payment feasibility;
- budget;
- deadline/TTM;
- application constraints;
- competition/freshness;
- source trust/evidence confidence;
- learning value when the user allows stretch work.

The system MUST produce a reproducible rationale explaining why a candidate was recommended, including the principal positive and negative factors and the evidence used. Ranking MUST NOT override hard policy blocks.

Duplicate opportunities appearing across multiple sites MUST be linked to one canonical opportunity where identity evidence supports the match. Source-specific observations, URLs and application paths MUST remain attached to the canonical opportunity. The system SHOULD recommend one application path rather than submitting duplicates.

### 50.8 Source-aware application limits and adaptive search

MarketRadar MUST learn and persist source-specific operational constraints, including:
- free/paid application models;
- credits/subscriptions;
- one-active-application or pending-request limits;
- cooldowns and rate limits;
- required waiting periods;
- source-specific proposal/application quotas.

Before submission, the system MUST check the current source constraints. If a source permits only one pending request, MarketRadar MUST NOT submit another while the existing request remains pending unless the source evidence indicates that a second request is permitted.

Search strategy MUST adapt to the user's enabled skills, newly completed tools/products, prior application outcomes and current market signals. When a new capability or product is added to the profile, future searches MUST be able to generate queries and matching criteria for that capability without requiring a code change.

### 50.9 Application package generation

For an eligible, authorized opportunity, MarketRadar MUST be able to prepare a source-appropriate application package from the user's profile and opportunity evidence, including as applicable:
- project title and concise understanding;
- proposal/application text;
- tailored resume/CV content;
- relevant portfolio/project selection;
- skill and capability mapping;
- delivery approach and scope;
- clarifying questions;
- requested images or visual assets when the source requires them.

Generated application material MUST be evidence-grounded and MUST NOT fabricate experience, certifications, portfolio items, client history or completed work.

### 50.10 Submission, follow-up and project tracking

The system MUST support a durable application lifecycle covering, where the source exposes the state:
DISCOVERED -> ELIGIBILITY_CHECK -> RECOMMENDED -> APPROVAL_PENDING -> SUBMITTED -> VIEWED/MESSAGE_RECEIVED/NEGOTIATION -> ACCEPTED/REJECTED/EXPIRED.

Authorized automation MAY submit or communicate only through permitted connectors and authorization bindings. Human approval remains the default for consequential actions unless the user has explicitly configured a narrower low-risk preauthorization policy.

After submission, the system MUST be able to:
- monitor status changes;
- detect missing/no-response periods;
- schedule follow-up;
- prepare an email/message follow-up;
- record sent/received evidence and external references;
- track accepted work, milestones, deadline, delivery and payment state.

No follow-up or external message may be silently sent outside an authorized action path.

### 50.11 Scan cadence by source lane

Source scheduling MUST be lane-aware and durable:
- Iran-compatible/evidence-qualified execution sources: target scan interval 60 minutes (or 120 minutes when configured);
- foreign/incompatible market-intelligence sources: target scan interval 12 hours;
- newly discovered/unknown sources: revalidation cadence determined by freshness/health policy;
- blocked/blacklist sources: no normal recommendation scanning, but retained for audit/history and policy re-checks where explicitly configured.

The scheduler MUST persist next-run state, retries, backoff, stale status and recovery state.

### 50.12 Social/community discovery boundaries

Social, messaging and community platforms MUST be treated as discovery/evidence surfaces unless an authorized connector exists.

The product MUST support public/indexed discovery and authorized access. It MUST NOT bypass CAPTCHA, authentication controls, access controls, rate limits or platform restrictions. A social platform appearing in a search result does not imply that its content is fully crawlable.

Forum/community reports are evidence inputs with provenance and confidence. A forum statement such as "this platform does not work in Iran" MUST be retained as a claim with source/time, and MUST be reconciled with direct platform evidence when available.

### 50.13 Search-provider federation and SearXNG

Search acquisition MUST support a provider abstraction so coverage can be expanded without changing domain logic.

Supported providers MAY include:
- Brave;
- Bing;
- Serper;
- SearXNG;
- other explicitly configured providers.

SearXNG may be deployed locally (including Docker on Windows) and used as a metasearch provider. Provider identity MUST be recorded in discovery provenance. A search result is discovery evidence, not source-policy proof.

The system MUST support provider fallback and multi-provider attribution where configured. Provider failure MUST be distinguishable from source absence.

### 50.14 Large-source-pool operation

The runtime MUST be capable of handling a source registry that grows well beyond 500 records, including 1,000+ discovered/registered sources, without changing the meaning of the 500 benchmark.

Scanning MUST be bounded by:
- per-source timeout;
- host/rate limits;
- concurrency controls;
- retry/backoff;
- crawl/page/byte budgets;
- persistent checkpoints;
- resumability;
- per-source failure isolation.

A failure on one source MUST NOT terminate the whole federation scan.

### 50.15 Duplicate and cross-post intelligence

The system MUST detect likely cross-posted projects across sources using multiple signals where available, such as:
- normalized title/description;
- client/employer/party identity;
- budget/currency;
- deadline;
- required skills;
- deliverables;
- URLs or source references;
- temporal proximity.

Deduplication MUST preserve all source observations and confidence rather than deleting the duplicates as if they never existed.

### 50.16 Red-list policy as a configurable operational rule

The user-configured execution blacklist MUST support country/jurisdiction and relationship-based blocking. The current configured policy includes Israel as an explicit execution blacklist target.

When configured, evidence-backed links to the blocked jurisdiction/entity MUST place the source, party or opportunity into a retained blacklist/archive lane and exclude it from recommendations and execution. Records MUST NOT be deleted.

The detector MUST distinguish an operational relationship from incidental textual mention. Evidence can include jurisdiction, ownership, operator, employer/client, payment/registration relationship, explicit business relationship or other auditable linkage. An incidental mention alone MUST NOT be treated as a relationship.

### 50.17 Continuous source expansion

The system MUST support a continuous discovery loop:
DISCOVER -> DEDUP -> REGISTER -> STUDY -> VERIFY/UNKNOWN -> CLASSIFY -> SCHEDULE -> SCAN -> LEARN -> DISCOVER.

Discovery results MUST include provenance so the operator can see which query/provider/community/source caused a candidate to enter the registry.

The system MUST be able to expand beyond the initial catalog automatically when configured and online. Manual source insertion remains supported for operator-discovered platforms.

### 50.18 Evidence and reporting additions

The UI and reports MUST expose, separately:
- discovered/registered count;
- unique canonical hosts;
- reachable count;
- parseable count;
- policy-verified count;
- execution-ready count;
- Iran ALLOW/BLOCK/REVIEW/UNKNOWN;
- KYC states;
- payment capabilities;
- market-intelligence sources;
- blacklist/archive count;
- dynamic-discovery provenance;
- duplicate/cross-post relationships;
- current scan/failure/retry state.

No one of these counts may be presented as another.

### 50.19 Acceptance criteria for this amendment

This amendment is considered implemented only when:
1. code paths exist for global multilingual discovery and source-family expansion;
2. social/community discovery boundaries are represented;
3. SearXNG/provider federation is represented in configuration and provenance;
4. source study persists Iran/KYC/payment/phone/subscription/intermediary evidence;
5. user skill proficiency is persisted and used in matching;
6. demand intelligence can produce evidence-backed Product Build Specifications;
7. cross-source opportunity deduplication preserves source observations;
8. source application limits prevent invalid duplicate submissions;
9. application packages are generated without fabricated claims;
10. follow-up/project tracking is durable and auditable;
11. lane-specific scan cadences are persisted and scheduled;
12. blacklist/archive behavior is non-destructive;
13. 1,000+ source-pool scale is handled with bounded/resumable execution;
14. regression/adversarial tests cover the amendment;
15. CI evidence and audit/reporting distinguish implemented behavior from live external qualification.

## 51. Amendment governance

This amendment is part of the normative contract for the next implementation cycle. Existing Manifest sections remain in force unless this amendment explicitly extends them. Any future change to these requirements MUST be recorded as a further amendment rather than silently reinterpreting the product.

## 47. Manifest governance
This Manifest is normative.
New capabilities must map to an existing contract section or receive an explicit amendment.
Implementation must not silently redefine domain terms.
Audit documents record evidence and gaps; they do not weaken this contract.

## 48. Development rule
Development proceeds:
MANIFEST -> AS-IS AUDIT -> GAP MATRIX -> CONFLICTS -> IMPLEMENTATION -> TEST -> CI EVIDENCE -> AUDIT UPDATE.
No feature is considered complete merely because code exists.

## 49. Final architecture
WORLD -> OBSERVATIONS -> EVIDENCE -> ONTOLOGY/DOMAIN STATE -> DECISION -> ACTION -> OUTCOME -> LEARNING -> NEW DECISION.

The system must preserve the distinction between what happened, what was observed, what is believed, what is allowed, what was approved, what was executed, and what actually happened afterward.

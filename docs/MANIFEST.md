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

# SEPP-MarketRadar Manifest Requirement Matrix v1.0

Status: **NORMATIVE EXECUTION REGISTER**
Baseline: `SEPP-MarketRadar v16.1.2`
Source contract: `docs/MANIFEST.md`
Audit source: `docs/MANIFEST_ASIS_AUDIT.md`
Purpose: تبدیل Manifest به یک ماتریس اجرایی که برای هر الزام، implementation، test، evidence، environment، solution-search و priority را ثبت می‌کند.

## 0. Locked operating rule

This register is subordinate to `docs/MANIFEST.md` and does not weaken or redefine it.

The execution loop is locked:

`MANIFEST → AS-IS AUDIT → GAP MATRIX → CONFLICTS → IMPLEMENTATION → TEST → CI EVIDENCE → AUDIT UPDATE`

Definition of Done for every row:

1. implementation exists;
2. regression coverage exists;
3. adversarial/failure coverage exists where relevant;
4. required environment evidence exists;
5. audit/reporting exposes the state;
6. contradictory legacy paths are removed or retired.

**Important:** source inspection is not runtime PASS. A row is PASS only when the evidence required by its contract exists. Code existence alone is OPEN.

## 1. Status vocabulary

| Status | Meaning |
|---|---|
| PASS | Required implementation and required evidence are present for the row. |
| OPEN | Code/path exists or partial evidence exists, but one or more required proof obligations remain. |
| FAIL | A reproducible current defect blocks the requirement. |
| NOT EXECUTED | The required test/evidence has not yet been run. |
| SKIPPED | Explicitly excluded by a documented environment/contract condition. |

## 2. Priority

| Priority | Meaning |
|---|---|
| P0 | Blocks product qualification, truthfulness, security boundary, or core execution. |
| P1 | Required for Manifest-conformant product behavior and qualification. |
| P2 | Required for complete intelligence/learning/product depth after P0/P1. |
| P3 | Hardening/optimization after the contractual path is proven. |

## 3. Master Manifest Requirement Matrix

| # | Manifest requirement | Implementation / coding that must exist | Test / evidence that must exist | Status | If not PASS: solution already available? | External reference searched? | Required environment | Priority | Expected output |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | Mission | End-to-end domain pipeline from market observations to evidence, decision, authorized action, outcome and learning. | Behavioral qualification proving the chain, not only unit fixtures. | OPEN | YES — existing operationalization and goal-verification paths; full live chain still open. | NO — internal repo/history first. | GitHub CI + Windows live qualification. | P0 | A real opportunity moves through evidence → decision → action → outcome → learning with provenance. |
| 2 | Core truth model | Explicit separation of observation/snapshot/evidence/claim/domain state/decision/action/outcome/learning; UNKNOWN preserved. | Regression tests for each state boundary and negative tests preventing evidence from becoming truth. | OPEN | YES — claim/evidence/decision structures exist; broad contract qualification still required. | NO | GitHub CI + Windows qualification. | P0 | Reports can distinguish what was observed, believed, allowed, approved, executed and actually happened. |
| 3 | Domain contract | Source, endpoint, observation, snapshot, evidence, claim, entity, party, opportunity, decision, approval, action, workflow, outcome, financial observation and learning signal with identity/state/time/provenance/version. | Schema/constraint audit + lifecycle tests + reconstruction tests. | OPEN | YES — substantial schema exists. | NO | GitHub CI; DB regression. | P0 | Canonical domain objects have stable identity and auditable state. |
| 4 | Source registry | Registry states and source metadata; never present registry count as verified integration count. | Registry audit, count-vs-verified distinction, live 500 qualification. | OPEN | YES — registry and audit tools exist. | YES — source/provider documentation research is required for live promotion. | Windows live network. | P0 | Separate registered/discovered/verified/execution-ready counts. |
| 5 | Source adapter contract | Per adapter: acquisition method, endpoint, I/O contract, scope, auth, policy, limits, parser/normalizer, failures, verification evidence, maturity. | Contract completeness test for every executable adapter; live sample acquisition. | OPEN | YES — source contracts exist; full adapter coverage needs qualification. | YES — provider docs/API/terms must be checked per adapter. | GitHub + Windows live network. | P0 | Every executable source is explainable and auditable; homepage scraping is not falsely mature. |
| 6 | Capability maturity | Central monotonic ladder: REGISTERED → DISCOVERED → DOCUMENTED → REACHABLE → PARSEABLE → VALIDATED → POLICY_VERIFIED → EXECUTION_READY. | All-stage promotion tests, anti-downgrade tests and CI evidence. | PASS | — | YES — internal sibling/history pattern; no new external dependency required. | GitHub Windows CI #230. | P0 | Capability cannot advance without evidence or silently downgrade. |
| 7 | Source verification | Record HTTP evidence, parsing, policy, eligibility, KYC, payment, terms, time, confidence, failure reason and stale/revalidation state. | Verification-state regression + stale/revalidation + live source qualification. | OPEN | YES — verifier and stale fields exist. | YES — provider terms/policy references needed for real sources. | Windows live network. | P0 | Time-bounded verification with explicit reason/evidence. |
| 8 | Discovery | Catalog/search/public-page/community/project URL discovery with provenance; discovery never grants authority. | Discovery fixture tests + live discovery gate with configured search provider. | OPEN | YES — discovery engine exists. | YES — search/provider documentation; SEARXNG configuration. | Windows live network. | P0 | New candidates enter as candidates, not execution-ready sources. |
| 9 | Acquisition | Source/host/size/timeout/retry bounds, redirect host policy, secret isolation. | SSRF/private-IP, redirect, size, timeout, retry, secret-leak tests; real acquisition sample. | OPEN | YES — acquisition controls and fallback exist; live acquisition remains qualification gate. | YES — mature HTTP/browser libraries considered; no random dependency added. | GitHub security regression + Windows live. | P0 | Safe source-bound acquisition with auditable failures. |
| 10 | Immutable raw evidence | Hashable/replayable raw payloads; snapshot identity includes source, endpoint, observation time and digest; raw remains distinct from normalized data. | Hash/replay/tamper tests and reconstruction test. | OPEN | YES — raw observations/snapshot hashes exist. | NO | GitHub CI + DB regression. | P0 | Original acquired evidence can be replayed and independently reinterpreted. |
| 11 | Observation layer | Preserve source, URL, timestamp, HTTP metadata, content type, digest and acquisition provenance. | Observation persistence, metadata integrity and replay tests. | OPEN | YES — federation/observation structures exist. | NO | GitHub CI + live acquisition. | P0 | Each observation answers exactly what was received and when. |
| 12 | Canonical opportunity | Normalize observations into domain opportunities while retaining source/evidence links and contradictions. | Normalization regression, provenance linkage and contradiction preservation. | OPEN | YES — canonical pipeline exists; broad proof required. | NO | GitHub CI + live sample. | P0 | One opportunity can be traced back to every originating observation. |
| 13 | Deduplication | Stable opportunity identity + observation history; no title-only replacement; conflicting observations retained. | Duplicate/near-duplicate/conflict tests and historical reconstruction. | OPEN | YES — existing canonical/history model; targeted qualification still needed. | NO | GitHub DB regression. | P1 | Repeated observations update history without erasing contradictory evidence. |
| 14 | Entity resolution | MATCH/POSSIBLE_MATCH/NO_MATCH with confidence/evidence; conservative reversible merge. | Threshold tests, non-merge tests, repeatability/idempotency and audit trail. | OPEN | YES — implemented and regression exists; not independently qualified as a complete Manifest row. | NO | GitHub CI. | P1 | Ambiguous identities remain reversible and auditable. |
| 15 | Party resolution | Distinct client/employer/agency/buyer/procurement/intermediary roles with temporal relationships. | Role separation, relationship evidence and temporal validity tests. | OPEN | YES — party model exists. | NO | GitHub CI + live source samples. | P1 | Party identity and role are not collapsed into a generic entity. |
| 16 | Evidence graph | source → observation → evidence → claim → domain object graph; consequential claims have claim-level provenance. | Orphan/linkage tests, provenance traversal and claim-evidence regression. | OPEN | YES — claim/evidence linkage implemented. | NO | GitHub CI. | P0 | Any consequential claim can be traced to concrete evidence. |
| 17 | Trust/reputation | Separate trust from evidence confidence; provenance diversity, manipulation signals, confidence and UNKNOWN. | Low-evidence/contradiction/manipulation fixture tests; UNKNOWN behavior. | OPEN | YES — trust assessment exists. | YES — external reputation/provider signals only where legitimate and documented. | GitHub + live source qualification. | P1 | Trust is an assessment, never silently promoted to fact. |
| 18 | Eligibility | Independent ALLOW/REVIEW/BLOCK/UNKNOWN state separate from payment/KYC/source health/ranking. | Cross-product tests proving independence and fail-closed UNKNOWN. | OPEN | YES — eligibility/policy structures exist. | YES — country/provider policy sources needed for live evidence. | GitHub + Windows live. | P0 | Eligibility decisions are deterministic and independent of ranking/payment/KYC. |
| 19 | Payment intelligence | Claimed/documented/observed/verified payment-path states; detection ≠ verification. | Positive/negative/ambiguous payment tests; verification evidence required for PAID. | OPEN | YES — payment intelligence and payment lifecycle exist. | YES — payment-provider documentation/reference sources. | GitHub + sandbox/live evidence. | P0 | Payment claims never become PAID without explicit verification. |
| 20 | KYC intelligence | Separate KYC requirement state from eligibility/payment; UNKNOWN remains UNKNOWN/REVIEW. | Unknown-KYC negative tests and documented-vs-observed distinction. | OPEN | YES — KYC layer exists. | YES — provider terms/KYC documentation required per source. | GitHub + live source qualification. | P0 | KYC uncertainty cannot be interpreted as permission. |
| 21 | Policy engine | Deterministic, versioned, auditable BLOCK/REVIEW/EXECUTE/UNKNOWN decisions bound to evidence. | Policy matrix tests, version pinning, evidence binding, fail-closed tests. | OPEN | YES — policy engine and policy version exist. | NO for engine; YES for real provider policy inputs. | GitHub CI + Windows live. | P0 | Same snapshot + policy version yields reproducible policy result. |
| 22 | Temporal/change intelligence | first_seen, last_seen, freshness, expiry/revalidation and contradiction/change detection; immutable conflict ledger. | Temporal contradiction immutability and stale/revalidation regression. | PASS | — | NO new external dependency. | Windows CI #230. | P0 | Changes remain first-class temporal evidence instead of silent overwrite. |
| 23 | Intelligence | Classification, summarization, clustering, demand/competition/TTM/market signals; AI/heuristics not authorization authority. | Determinism/quality tests where deterministic; adversarial tests proving intelligence cannot authorize blocked actions. | OPEN | YES — intelligence components exist. | YES — mature analytical libraries may be reused only after contract review. | GitHub CI + Windows. | P1 | Intelligence enriches decisions without bypassing policy/authorization. |
| 24 | Ranking | Ranking separate from policy/decision; factors/confidence exposed; cannot override hard constraints. | Ranking/policy separation tests and blocked/unknown override tests. | OPEN | YES — ranking exists; qualification needed. | NO | GitHub CI. | P0 | Ranking prioritizes candidates but cannot authorize them. |
| 25 | Decision model | Decision snapshot combines domain state, evidence, policy, ranking/context and user constraints; consequential decision reproducible. | Snapshot replay, immutable decision trace, ACTION_EXECUTION/DAILY_SNAPSHOT tests. | OPEN | YES — decision trace sub-contract is PASS; complete decision-model qualification remains open. | NO | Windows CI #230 + full qualification. | P0 | A consequential decision can be reconstructed exactly from its snapshot. |
| 26 | Daily Intelligence Center | Top 7, Do-Now 3, monitor, blocked, unknown as views over decision model. | Bucket completeness, snapshot trace, ranking context and truthfulness tests. | OPEN | YES — daily center + trace exist. | NO | GitHub CI + Windows UI/live qualification. | P1 | UI/report shows prioritized views without turning them into execution authority. |
| 27 | Human approval | Explicit human approval for consequential actions unless independently defined low-risk policy; exact-action binding. | Approval-required negative tests and exact-action mismatch tests. | OPEN | YES — approval broker exists. | NO | GitHub CI + Windows E2E. | P0 | No consequential action proceeds without valid approval. |
| 28 | Authorization broker | Bind target/action/params digest/evidence digest/policy version/expiry/one-time nonce; fail closed. | Replay, expiry, target/parameter/evidence mismatch, nonce reuse and authorization failure tests. | OPEN | YES — authorization broker exists; execution trace hardened. | NO | GitHub CI + Windows live. | P0 | Only the exact approved action can execute, once, within validity window. |
| 29 | Action model | Stateful transaction with preconditions, execution, result, audit, failure semantics, idempotency and external reference/digest. | Retry/idempotency/failure/recovery tests and external-reference recording. | OPEN | YES — action execution and recovery structures exist. | YES — mature retry/idempotency patterns may be reused after contract review. | GitHub CI + Windows sandbox. | P0 | Repeated execution does not create unintended duplicate side effects. |
| 30 | Application lifecycle | Valid transitions discovery → application → negotiation → acceptance → delivery → payment; invalid transitions fail closed. | Full state-machine transition matrix including invalid transitions. | OPEN | YES — lifecycle code exists; full qualification remains open. | NO | GitHub CI + sandbox. | P0 | Application state is explicit, valid and auditable. |
| 31 | Delivery | Immutable artifact evidence, digest, actor and observation time; delivery ≠ payment. | Artifact tamper/digest/actor/time tests and separation from payment evidence. | OPEN | YES — delivery path exists. | NO | GitHub CI + sandbox. | P1 | Delivery proof is independently verifiable and cannot imply payment. |
| 32 | Revenue/payment | Revenue recording separated from settlement; PAID only after explicit verification; duplicate payment refs rejected. | Duplicate-ref, unverified-payment, verified-payment and transaction rollback tests. | OPEN | YES — revenue/payment lifecycle exists. | YES — provider/payment documentation for sandbox adapters. | GitHub CI + payment sandbox. | P0 | Financial state changes only from explicit evidence. |
| 33 | Outcome ledger | Submission/response/acceptance/rejection/cancellation/delivery/payment outcomes immutable and reusable for learning. | Outcome immutability, reason preservation and lifecycle coverage. | OPEN | YES — outcome ledger exists. | NO | GitHub CI + Windows qualification. | P1 | Every important result becomes a durable learning input. |
| 34 | Market learning | Learn from outcomes, source/party behavior, pricing, TTM, acceptance and revenue without rewriting observations. | Learning replay and historical-integrity tests. | OPEN | YES — learning/revenue intelligence exists. | YES — mature analytics libraries can be evaluated later if needed. | GitHub CI + Windows. | P2 | New learning is additive and historical observations remain unchanged. |
| 35 | Negative/rejection intelligence | Rejected/blocked/expired/failed are first-class; preserve reasons and feed policy/ranking/learning. | Reason taxonomy, propagation and ranking/policy consumption tests. | OPEN | YES — rejection/outcome paths exist. | NO | GitHub CI. | P1 | Negative evidence changes future decisions without rewriting history. |
| 36 | Acquisition fallback | Ordered provider chain, provenance, fallback-used metadata, confidence multiplier, source-unavailable vs all-providers-failed distinction. | Provider ordering/provenance/failure-semantics regression. | PASS | — | NO new dependency required. | Windows CI #230. | P0 | Provider failure is never mislabeled as source absence. |
| 37 | Scheduler/runtime | Durable/resumable scans; explicit retry/backoff/timeout/stale/recovery state. | Restart/resume/retry/backoff/stale/recovery repetition tests. | OPEN | YES — scheduler/runtime/recovery structures exist. | YES — mature scheduler/retry patterns can be compared before expansion. | Windows + GitHub CI. | P0 | A scan can recover from interruption without losing state or duplicating work. |
| 38 | Security | SSRF/private-IP, host allowlists, secret isolation, signed approvals, replay detection, immutable ledgers, parser isolation, least privilege. | Adversarial security suite for every boundary; fail-closed evidence. | OPEN | YES — major controls exist; full red-team qualification remains required. | YES — official security/library docs and mature OSS patterns. | GitHub adversarial + Windows live. | P0 | Untrusted sources/actions cannot cross security boundaries. |
| 39 | Windows product | Real portable EXE + installer + install/uninstall + EXE/UI smoke; scripts alone do not count. | Windows self-hosted build, EXE smoke, UI smoke, installer E2E, uninstall, artifact evidence. | OPEN | YES — packaging and independent verification workflows exist; current runtime bootstrap failed. | YES — official Python/setup-python/PyInstaller docs searched. | Self-hosted Windows runner. | P0 | A clean Windows machine can receive, install, launch, smoke-test and remove the product. |
| 40 | Android companion | Android only reviews/notifies/approves/status; Windows remains authority; no independent policy/payment authority. | Assemble + emulator E2E + authority-boundary tests. | PASS | — | YES — Android/Gradle tooling already used. | GitHub Linux emulator; prior Full Qualification #209. | P1 | Android can operate as a companion without becoming a second decision engine. |
| 41 | Observability | Stage status, timestamps, errors, retries, health/digests; attempted/successful/failed/skipped/unknown/not configured. | Failure injection and status taxonomy tests. | OPEN | YES — observability/audit output exists. | NO | GitHub CI + Windows qualification. | P1 | Operators can distinguish failure, skip, unknown and unconfigured states. |
| 42 | Auditability | Audit trail for consequential state changes; immutable ledgers reject silent mutation/deletion. | UPDATE/DELETE tamper tests and audit reconstruction. | OPEN | YES — audit tables/triggers exist; broad coverage required. | NO | GitHub CI + Windows. | P0 | Historical consequential actions cannot be silently rewritten. |
| 43 | Data integrity | FK/unique/constraints, hashes, idempotency keys, transactions; reconstructable history. | Constraint violation, transaction rollback, duplicate/idempotency and reconstruction tests. | OPEN | YES — SQLite/domain constraints exist. | YES — Python sqlite3/transaction documentation reviewed. | GitHub CI + DB regression. | P0 | Invalid domain states are rejected and valid history is reconstructable. |
| 44 | Product UI | Truth model visible: source/evidence/confidence/eligibility/policy/ranking/approval/action/outcome; UNKNOWN/REVIEW/BLOCKED not disguised as ready. | UI visual smoke + semantic state tests for all truth states. | OPEN | YES — UI and visual smoke exist. | YES — Playwright/UI tooling available for browser-facing surfaces if required. | Self-hosted Windows UI. | P0 | UI faithfully represents system truth and uncertainty. |
| 45 | Reporting truthfulness | Registered/discovered/verified/execution-ready counts separated; live/product/platform claims evidence-gated. | Report-vs-database reconciliation and false-claim regression. | OPEN | YES — product/release audit exists. | NO | GitHub CI + Windows qualification. | P0 | No report can convert registry presence into verification or readiness. |
| 46 | Definition of done | Enforce six-part completion gate in workflow/audit process; code alone cannot close a requirement. | Meta-test/audit check ensuring each requirement has implementation/test/failure/env/audit/legacy evidence. | OPEN | YES — process docs exist; enforcement matrix is this document. | NO | GitHub CI + audit. | P0 | Every closed item has complete evidence, not just code. |
| 47 | Manifest governance | New capability maps to a Manifest section or explicit amendment; no silent terminology changes. | Manifest alignment test + review/audit check for every new capability. | OPEN | YES — normative Manifest exists; matrix now formalizes mapping. | NO | GitHub CI + code review. | P0 | Product evolution cannot bypass the normative contract. |
| 48 | Development rule | Operationalize MANIFEST → AS-IS → GAP → CONFLICTS → IMPLEMENT → TEST → CI → AUDIT. | Workflow/process audit and evidence update after every patch. | OPEN | YES — process is already used; matrix makes it persistent. | NO | GitHub + Windows/Android as required. | P0 | Work proceeds gap-by-gap and every claim is evidence-backed. |
| 49 | Final architecture | Preserve WORLD → OBSERVATIONS → EVIDENCE → DOMAIN STATE → DECISION → ACTION → OUTCOME → LEARNING → NEW DECISION and all distinctions. | Full replay/qualification test plus audit of contradictory legacy paths. | OPEN | YES — architecture is substantially present; final end-to-end proof remains open. | NO | Windows full qualification + GitHub CI + Android companion. | P0 | Complete product loop preserves every semantic boundary from observation to learning. |

## 4. Current explicit qualification gates

These gates are not replacements for the 49 Manifest sections. They are environment-level evidence gates used to prove them.

| Gate | What must be implemented/tested | Current status | Environment | Priority | Known solution/source |
|---|---|---|---|---|---|
| NETWORK_PRECONDITION | External network prerequisite probes. | OPEN until current full qualification produces evidence. | Windows live network. | P0 | Existing gate. |
| WORK_TAXONOMY_OUTPUT_CONTRACT | Required work taxonomy and normalized output contract. | OPEN pending current full qualification evidence. | GitHub/Windows. | P1 | Existing taxonomy gate. |
| BEHAVIORAL_OUTPUT_AND_GOAL_MATCH | Operationalization produces expected opportunity/evidence/Top-7/Do-Now/lifecycle outputs. | OPEN pending current full qualification evidence. | Windows CI/local qualification. | P0 | Existing operationalization lab + goal verifier. |
| RESTART_AND_RECOVERY_REPEATABILITY | Repeat operationalization three times with recoverable state. | OPEN pending current qualification evidence. | Windows. | P0 | Existing recovery/runtime code. |
| LIVE_GLOBAL_DISCOVERY | Live discovery through configured search provider. | OPEN if `SEARXNG_URL` absent; not a PASS without live evidence. | Windows live network. | P0 | Existing discovery path; provider configuration required. |
| LIVE_SOURCE_REACHABILITY_500 | At least 500 live-reachable source endpoints from registry, separately from connector maturity. | OPEN; historical evidence was below target. | Windows live network. | P0 | Existing SourceVerificationEngine; scale/network work required. |
| LIVE_ACQUISITION_SAMPLE | Real acquisition sample produces observations. | OPEN until current run proves it. | Windows live network. | P0 | Existing federation + AcquisitionFallback. |
| SOCIAL_SOURCE_SURFACE | Live reachability of social/community family candidates. | OPEN until current qualification evidence. | Windows live network. | P1 | Existing family gate. |
| PROCUREMENT_SOURCE_SURFACE | Live reachability of procurement family candidates. | OPEN until current qualification evidence. | Windows live network. | P1 | Existing family gate. |
| DYNAMIC_JS_BROWSER | Real dynamic page rendered through Playwright. | OPEN if `QUALIFY_DYNAMIC_URL` absent. | Windows live network/browser. | P1 | Playwright is the external reference/implementation option. |
| ENGINE_CONTRACT_LOCAL | Local engine manifest/job/result contract. | Existing local gate PASS by implementation; current full post-audit evidence still required. | GitHub/Windows. | P1 | Software_Forge contract patterns + existing engine contract. |
| EXTERNAL_ENGINE_E2E | Sandbox endpoint POST, no production side effect. | OPEN when endpoint is not configured. | External sandbox. | P1 | Existing sandbox endpoint gate. |
| APPLICATION_SANDBOX_E2E | Application sandbox execution. | OPEN when endpoint is not configured. | External sandbox. | P0 | Existing action/application path. |
| PAYMENT_SANDBOX_E2E | Payment sandbox verification. | OPEN when endpoint is not configured. | External sandbox. | P0 | Existing payment lifecycle + sandbox gate. |
| PUSH_NOTIFICATION_E2E | Notification sandbox path. | OPEN when endpoint is not configured. | External sandbox + Android. | P1 | Existing Android gateway/notification path. |

## 5. Current Windows qualification incident — evidence, not assumption

Latest observed branch commit before the current remediation:
`b3f140896e2897cd6efa59dcafd144d1728cd122`

Observed runs:

- Full Qualification #298 / run `35870105326`: **queued** at the audit checkpoint.
- Windows CI #281 / run `35870105417`: **FAIL**.
- Fast Regression #29 / run `35870105422`: **FAIL**.
- Windows Verification #30 / run `35870105403`: **FAIL**.

Root causes proven by logs:

1. **Fast Regression:** stale bootstrap still downloaded NuGet `.nupkg` and passed it to PowerShell `Expand-Archive`, which rejects the extension. This is a workflow defect, not a product-code failure.
2. **Windows Verification:** official Python full installer download succeeded, but the installer returned exit code `-2147024891` (Windows access-denied class) when invoked from the self-hosted service context.
3. **Windows CI:** the test suite itself reached 100%, but `tests/test_manifest_alignment.py::test_self_hosted_full_qualification_uses_local_python` failed because the test expected `PYTHON_VERSION_TOO_OLD` in the old workflow contract after the workflow had changed.

The remediation branch now replaces the brittle custom bootstrap with pinned `actions/setup-python@v7.0.0` plus explicit Tkinter validation for Windows product workflows. GitHub's current setup-python documentation explicitly supports self-hosted Windows runners when the runner has appropriate permissions; the documented Windows path uses the runner tool cache, and `setup-python` is the recommended mechanism for GitHub Actions. citeturn2search0turn4search2

For Windows application packaging, PyInstaller documentation confirms that Windows executables must be built on Windows and that the packaged result contains the Python interpreter/dependencies; therefore the Windows runner remains the authoritative build environment. citeturn1search1turn1search2

Python's official Windows documentation distinguishes the full installer from the lightweight NuGet package: the full installer includes Tcl/Tk and pip, while the NuGet package is intended for lightweight CI/build use and lacks UI tooling. This is why a generic NuGet archive is not accepted as the Windows UI qualification runtime. citeturn1search0

Playwright is the selected external browser reference where dynamic-JS qualification is required; its official Python documentation supports Windows/Linux/macOS CI and recommends the Pytest integration for E2E testing. citeturn5search0turn5search12

## 6. External-solution register

| Problem class | Existing solution/reference | Decision |
|---|---|---|
| Windows Python runtime on self-hosted runner | `actions/setup-python@v7`, official GitHub guidance for self-hosted Windows. | USE FIRST; verify on our runner before adding custom installer logic. |
| Windows Python UI/Tkinter | Full CPython distribution with Tcl/Tk; explicit `import tkinter` gate. | KEEP AS CONTRACT. |
| Windows EXE | PyInstaller; must build on Windows. | REUSE existing packaging path; do not invent another bundler unless evidence forces it. |
| Dynamic browser | Playwright + pytest integration. | USE for dynamic-JS gate where a legitimate test target is configured. |
| DB transactions/integrity | Python `sqlite3` transaction model + existing DB constraints/triggers. | REUSE existing DB architecture; add tests before changing transaction semantics. |
| Source acquisition/retry | Existing MarketRadar acquisition/fallback + mature standard HTTP tooling. | Reuse current implementation first; only add dependency if a measured bottleneck/contract requires it. |
| Engineering control plane | Software_Forge contracts, failure graph, goal verifier, recovery and audit patterns. | Reuse/adapt before creating parallel mechanisms. |
| Desktop packaging/Windows regression | CDR_Core Windows verification/regression patterns. | Reuse/adapt test architecture where responsibilities match. |

## 7. Evidence environments

| Environment | Authoritative evidence |
|---|---|
| GitHub-hosted CI | Domain invariants, compile, pytest, manifest regressions, audit checks. |
| Self-hosted Windows `MARKETRADAR-WINDOWS-01` | Windows EXE, installer, UI, filesystem/registry/service/runtime, live network/source qualification. |
| GitHub Linux + Android emulator | Android build and companion E2E. |
| External sandbox | Engine/application/payment/push external contracts without production side effects. |
| Real production/provider | Only where an external contract explicitly requires real-world evidence; otherwise sandbox/fixture is mandatory. |

## 8. Execution order locked by priority

1. **P0 — Windows runtime/bootstrap and product qualification.**
2. **P0 — Full post-audit CI evidence.**
3. **P0 — Live source reachability 500 and live acquisition.**
4. **P0 — Security/authorization/policy/eligibility/payment/KYC evidence closure.**
5. **P0 — End-to-end application → delivery → payment evidence.**
6. **P1 — Discovery/social/procurement/dynamic browser and reporting/UI evidence.**
7. **P1/P2 — learning depth, reputation/intelligence expansion and optimization.**
8. **P3 — performance/optimization only after contractual evidence is stable.**

No lower-priority feature may be used to mask an unresolved P0 contract.

## 9. Reporting rule

The matrix must be updated after every implementation/test cycle.

A row can move only through evidence:

`OPEN/FAIL → PATCH → TARGETED TEST → REQUIRED ENVIRONMENT → CI EVIDENCE → RE-AUDIT → PASS`

A commit, PR, source file, workflow definition or local success alone cannot move a row to PASS.

## 10. Current baseline summary

At this audit checkpoint:

- Manifest sections: **49**
- Explicit environment qualification gates: **15**
- Explicit PASS at section level with current documented evidence: **4** (capability maturity, temporal contradiction, acquisition fallback, Android companion qualification)
- Remaining sections: **OPEN** unless their exact required evidence is explicitly proven.
- Known current CI failures are recorded above and are **not** converted into PASS by source inspection.
- Windows Product Qualification: **OPEN**.
- Full Post-Audit CI Evidence: **OPEN**.
- Live 500-source reachability: **OPEN**.
- External sandbox gates: **OPEN** when endpoints are not configured.
- No PR is to be merged as part of this register creation.

## 11. Mandatory future reference

Before any new feature or fix:

1. open this matrix;
2. identify the Manifest row(s);
3. inspect AS-IS code/tests/history;
4. record the gap and contradiction;
5. search current repo → sibling repos → history → mature OSS → official docs;
6. reuse/adapt a proven solution when responsibility/contracts permit;
7. implement the smallest conformant change;
8. add regression/failure coverage;
9. run the correct environment;
10. update evidence/status here;
11. only then move to the next priority gap.

This document is an execution register, not a replacement for `docs/MANIFEST.md`.

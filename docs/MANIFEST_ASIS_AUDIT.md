# SEPP-MarketRadar Manifest AS-IS Audit

Audit baseline: `main` after Manifest registration and alignment patches.
Product baseline: v16.1.2.
Audit method: repository source inspection against every normative Manifest contract, followed by targeted corrective commits. Environment-specific qualification remains CI-owned.

## 1. Manifest registration

- Normative Manifest: `docs/MANIFEST.md`
- Registration commit: `66a13b3a409a0f2e28190f719946cff1028c9306`
- Manifest is now the source contract for subsequent implementation audits.

## 2. AS-IS architecture observed

The implementation already contains a substantial portion of the intended architecture:

`WORLD -> acquisition/federation -> raw observations -> normalized opportunities -> evidence/policy -> entity/party/trust -> ranking/decision -> approval/authorization -> application -> delivery/payment -> outcomes/learning`

Observed components include:
- source registry, source identity and source contracts;
- source discovery and source-policy verification;
- SSRF/private-IP/host-bound acquisition controls and retry/backoff;
- raw observations, federation runs and snapshot hashes;
- canonical opportunity pipeline and observation history;
- entity/party resolution, reviews and trust assessments;
- eligibility, KYC and payment intelligence;
- versioned policy decisions;
- ranking, TTM, expected value and market signals;
- decision snapshots and daily Top-7 intelligence;
- approval broker, authorization broker and workflow/idempotency state;
- application/delivery/payment lifecycle;
- immutable operational ledgers and audit records;
- outcome learning, revenue intelligence, product/pricing/skill recommendations;
- Windows packaging and Android companion qualification paths.

## 3. Corrective findings fixed during this audit

### 3.1 Claim-level provenance
Finding: claim schema existed, but the canonical opportunity pipeline did not consistently materialize consequential normalized facts as claims linked to evidence.

Fix:
- policy version introduced as `policy.v1`;
- pipeline now persists claims for eligibility, payment, KYC, Iran access and budget;
- claims are linked to the evidence IDs generated for the observation.

Commit: `27898623776c71397f4ba8ac783589082b996536`.

### 3.2 Source capability maturity
Finding: source contracts contained execution capability/verification fields but lacked an explicit maturity state and revalidation deadline.

Fix:
- added capability maturity, capability evidence, capability checked time and stale-at fields to source and source-contract persistence;
- source verification now records REACHABLE / POLICY_VERIFIED maturity according to evidence and execution-lane state;
- revalidation deadline is persisted.

Commit: `51f5324f36545be631d86a4438c0d7c8f3aab98c` (implementation SHA recorded in Git history; current main contains the patch).

### 3.3 Entity resolution state semantics
Finding: the previous resolver effectively recorded MATCH or created a new entity; the Manifest requires explicit MATCH / POSSIBLE_MATCH / NO_MATCH semantics.

Fix:
- >=0.90 similarity remains MATCH;
- 0.65–0.89 is recorded as POSSIBLE_MATCH without merging;
- lower/no candidate is recorded as NO_MATCH;
- repeated non-match decisions are idempotent.

Commits:
- `66b5a1f4cccfaed31078c798575424503465cfad`
- `8f88bbba801367c665233fcdddc6799a2fc165b8`
- regression test `87750858d511d93f370b8b44452105d4e9621479`.

### 3.4 Product version truth
Finding: README still exposed historical 16.1.1/15.0.0 headings while package version was 16.1.2.

Fix:
- README synchronized to v16.1.2.

Commit: `0c549a3da5afc7f7e2c0a71a1a7964c654a4aae8`.

### 3.5 CI supply-chain alignment
Finding: qualification workflow referenced mutable action tags.

Fix:
- checkout, setup-python, setup-java, Gradle setup, Android emulator runner and artifact upload are now pinned to full commit SHAs with release comments.

Commit: `001e27ea0434112162f29085c00c21fad3258232`.

This follows GitHub's current security guidance that third-party Actions should be pinned to full-length commit SHAs. citeturn1search0turn8search3

## 4. Remaining Manifest gaps

### PARTIAL — Temporal contradiction model
The code retains first/last seen, rank history, raw observations and source verification history, and now has source stale-at data. However, there is not yet a first-class contradiction/change ledger for conflicting claims about the same opportunity.

Required next implementation:
- claim supersession/contradiction records;
- freshness policy per claim type;
- revalidation state visible to ranking/decision;
- no silent replacement of conflicting historical claims.

### IMPLEMENTED BY CODE — Source capability ladder
A central monotonic capability transition contract now defines all Manifest stages:
REGISTERED → DISCOVERED → DOCUMENTED → REACHABLE → PARSEABLE → VALIDATED → POLICY_VERIFIED → EXECUTION_READY.
Verification derives the highest stage directly supported by the current evidence and cannot downgrade an existing maturity. Execution-ready promotion additionally requires explicit authorized execution capability, reviewed terms, live verification and evidence URLs. Runtime/CI evidence is still required before PASS.

### IMPLEMENTED BY CODE — Acquisition fallback contract
Federation now exposes an ordered `AcquisitionFallback` contract with:
- explicit provider chain;
- per-provider provenance and fallback-used metadata;
- configurable confidence multiplier on fallback;
- distinct `SOURCE_UNAVAILABLE` vs `ALL_ACQUISITION_PROVIDERS_FAILED` outcomes;
- immutable raw/evidence layers remain responsible for preserving the actual acquired payload and provenance.

Commits:
- `c8c766044b9f69da50b946ffc5b71e99ef804220`
- `07b356fa52d482bfed487b6d506c7347535d9c0b`
- regression coverage: `83020a56acb068a6362cd26093b4c61c6fe6de4c`

Runtime/CI execution evidence is still required before reporting the contract as PASS.

### IMPLEMENTED BY CODE — Consequential decision trace
The codebase now has an immutable `decision_traces` ledger and a shared `record_decision_trace()` contract. Daily recommendations capture policy version, target, action, parameters/digest, evidence IDs/digest, claim snapshot, state snapshot, ranking context, actor, reason and outcome. Authorization issuance also records the approval reference, expiry and nonce. Runtime/CI evidence is still required before PASS.

### OPEN — Windows product qualification
Repository code and packaging paths exist, but the latest full-qualification cycle previously showed Windows EXE/installer failures. The later path/import fixes were committed, but no new complete post-audit Windows qualification result has been observed yet.

### OPEN — Android E2E qualification
Android assembly has succeeded previously, but the latest full qualification showed an emulator/ADB startup failure. No post-audit successful emulator E2E result has been observed yet.

### OPEN — Full post-audit CI evidence
The latest alignment commits have triggered/updated repository workflows, but no completed post-audit full qualification result is available yet. Therefore no final product qualification claim is made here.

## 5. Manifest sections currently aligned by code inspection

Source registry, discovery, acquisition controls, raw observations, canonical opportunity model, evidence storage, party model, trust/reputation, eligibility, KYC/payment separation, policy engine, ranking separation, decision snapshots, human approval, authorization binding, application lifecycle, delivery evidence, payment verification, outcome learning, workflow/idempotency structures, audit logs, Windows packaging structure, Android companion structure, observability and reporting controls are present in the current codebase.

This is source inspection evidence, not a replacement for runtime/CI execution evidence.

## 6. Test additions

Added `tests/test_manifest_alignment.py` covering:
- application state transition and policy binding;
- claim-to-evidence linkage;
- source capability contract columns;
- explicit entity-resolution non-merge states.

Commit: `87750858d511d93f370b8b44452105d4e9621479`.

## 7. Execution rule from this point

The next development cycle is not free-form feature expansion.

It is:

`MANIFEST -> GAP -> PATCH -> TEST -> CI -> RE-AUDIT -> NEXT GAP`

The remaining gaps above are now the implementation queue. No item will be reported as complete until repository code and corresponding evidence agree.


## 2026-09-22 — Capability ladder hardening
- Added centralized monotonic capability maturity transitions in `marketradar/capability.py`.
- Source verification now distinguishes PARSEABLE, VALIDATED, POLICY_VERIFIED and EXECUTION_READY evidence instead of collapsing all live sources to REACHABLE/POLICY_VERIFIED.
- Added regression coverage for all ordered stages and anti-downgrade behavior.
- Commits: `ab47e9c6b503158d63165f4625e2f1705fdc5740`, `4f9320186b7bae0a7f0dcde0c969422e1f95b80c`, `6be136733ad4b9006516cca78ac80f47dcf46798`.

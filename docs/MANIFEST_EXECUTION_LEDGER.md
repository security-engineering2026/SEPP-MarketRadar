# SEPP-MarketRadar — Manifest Operational Execution Ledger v1.1

**Role:** active operational execution controller for `docs/MANIFEST.md`.  
**Normative Manifest:** `docs/MANIFEST.md` v1.0  
**Manifest SHA:** `447b56f8a3a61ee34288730c705d9b0680c00e95`  
**Baseline:** SEPP-MarketRadar v16.1.2  
**Coverage reference:** `docs/MANIFEST_REQUIREMENT_MATRIX_V2.md` v2.0 — coverage/reference only, not the execution queue.  
**Current branch:** `process/manifest-execution-ledger`  
**Initial execution state:** one JIT-derived MICU only. No speculative future rows.

## 1. Authority and operating model

The locked Manifest is the specification. This ledger is the execution controller.

`MANIFEST → COVERAGE CHECK → AS-IS AUDIT → MICU → EXACT GAP → SOLUTION SEARCH → IMPLEMENT/PATCH → FOCUSED TEST → REGRESSION → ADVERSARIAL (when applicable) → EXACT ENVIRONMENT → FRESH EVIDENCE → CONTRADICTION CHECK → IMPACT REVALIDATION → AUDIT UPDATE → PASS → DERIVE NEXT MICU`

This ledger MUST NOT weaken, reorder, reinterpret, or silently amend the Manifest.

### Non-negotiable controls

1. **One execution cursor:** exactly one row may be ACTIVE.
2. **Strict sequential closure:** Row N must reach PASS before Row N+1 is derived/activated, except work explicitly required to remove an external environment blocker.
3. **Just-in-time decomposition:** do not pre-generate 139 execution rows. Derive the next MICU from the next unresolved Manifest requirement, dependency graph, current AS-IS, and impact set.
4. **MICU:** one independently closable behavior/invariant, not a whole Manifest section, feature family, or CI suite.
5. **Code existence is not proof.**
6. **Focused evidence is mandatory:** a large green CI run cannot close a requirement unless the requirement's own assertion is directly exercised.
7. **Environment is part of the acceptance contract.**
8. **Evidence must bind to the audited commit.**
9. **Historical evidence is context only until freshly revalidated.**
10. **Failure loop:** FAIL → proven root cause → solution/reuse search → minimal patch → regression → retest → fresh evidence.
11. **Contradiction gate:** old/bypass/duplicate paths that violate the same invariant block PASS.
12. **Impact gate:** changes may reopen earlier PASS rows; only affected rows are revalidated.
13. **Scope lock:** unrelated work becomes a future MICU.
14. **No merge:** no branch/PR is merged without explicit user instruction.
15. **No global percentage:** do not report a project percentage from an intentionally un-derived execution queue.

## 2. Status and execution state

### Final status — only these values

`PASS / OPEN / FAIL / NOT EXECUTED / SKIPPED`

### Execution state

- `LOCKED` — not the current work unit.
- `ACTIVE` — current MICU.
- `CLOSED` — PASS with all proof gates satisfied.
- A CLOSED row reopens if its contract, code path, dependency, evidence freshness, environment proof, or contradiction state is invalidated.

### Structural audit classification

These are audit metadata, not replacement statuses:

`VALID / NEEDS_SPLIT / NEEDS_REWRITE / MANIFEST_MISMATCH / MISSING_PROOF / OVER_SCOPED / DUPLICATE`

## 3. Coverage vs execution

`docs/MANIFEST_REQUIREMENT_MATRIX_V2.md` remains the broad Manifest coverage/reference artifact.

It answers:

> Where are all Manifest requirements represented?

This ledger answers:

> What is the single next independently closable unit, and what proof is required to close it?

The matrix MUST NOT be copied into the active execution queue merely to obtain row coverage.

Before R001 execution, the coverage gate must establish that every applicable Manifest clause is represented somewhere in the coverage artifact. An unmapped clause is a governance gap, not permission to invent a guessed execution row.

## 4. Required MICU row schema

| Field | Meaning |
|---|---|
| Row | Stable execution ID |
| Manifest Ref | Exact Manifest file + section/clause + Manifest SHA |
| MICU | One independently closable behavior/invariant |
| Acceptance Criteria | Objective, testable closure criteria derived from the Manifest |
| Depends On | Exact prerequisite row IDs, or NONE |
| Unblocks | What becomes derivable/eligible after PASS |
| Code Location | Exact file/module/class/function discovered during AS-IS |
| Code State | MISSING / PARTIAL / PRESENT |
| Current Behavior | Observed behavior, not assumption |
| Exact Gap | Concrete deficiency or “none proven” |
| Solution Search | Repositories/history/docs actually inspected |
| Reuse Decision | REUSE / ADAPT / CONFIRM EXISTING / CREATE-NEW + reason |
| Patch Action | Exact change required, or no patch |
| Focused Test | Smallest direct executable proof |
| Regression | Required regression proof |
| Adversarial | Negative/failure proof when relevant |
| Required Environment | Exact environment, runner/resource, not a generic category |
| Environment Owner/Why | Why this environment is authoritative for this MICU |
| Proof Command | Exact command/workflow/test gate |
| Expected Result | Objective expected result |
| Actual Result | Captured actual result |
| Evidence | Run/job/local execution/artifact reference |
| Evidence Type | UNIT / REGRESSION / INTEGRATION / WINDOWS / CLEAN_WINDOWS / CI / ARTIFACT / SECURITY / ADVERSARIAL / UI / RELEASE / ANDROID / EXTERNAL |
| Evidence Commit | Exact tested commit SHA |
| Artifact Identity | SHA-256/version/path where applicable |
| Evidence Time / Expiry | Fresh timestamp and expiry when time-bound |
| Reproducible | YES / NO / NOT EXECUTED |
| Contradiction | Conflicting implementation/test/UI/API/docs/CI path, or NONE |
| Impact Set | Earlier PASS rows potentially invalidated |
| Audit Update | Exact audit/traceability record updated |
| Audit Classification | Structural quality of the row |
| Final Status | PASS / OPEN / FAIL / NOT EXECUTED / SKIPPED |
| Execution State | LOCKED / ACTIVE / CLOSED |

## 5. PASS gate

A row may be PASS only when all applicable gates are true:

- Manifest clause is exact and traceable to the locked Manifest SHA.
- MICU is independently closable and not over-scoped.
- Current implementation was inspected.
- Exact gap was resolved or its absence was proven.
- Focused executable assertion passed.
- Required regression passed.
- Required adversarial/failure proof passed when applicable.
- Exact authoritative environment was used.
- Evidence is fresh and reproducible.
- Evidence commit matches the audited commit.
- Run/job/artifact identity is captured where applicable.
- No unresolved blocker remains.
- No contradictory reachable path remains.
- Impacted previous PASS rows were revalidated.
- Audit/traceability was updated.

A broad CI PASS, a workflow definition, a test definition, or historical markdown is not sufficient by itself.

## 6. Exact environment rule

Environment is retained as a required column and is strengthened from a generic category to an exact execution target.

Examples:

| Generic class | Active-row value |
|---|---|
| CI | GitHub-hosted Actions, workflow `<name>`, job `<name>`, run `<id>` |
| Windows | Self-hosted runner `MARKETRADAR-WINDOWS-01`, Windows version, run/job ID |
| Clean Windows | Clean Windows VM/image identifier + run |
| Live network | Authorized live-network execution + source/sample + run |
| Android | GitHub Linux runner + emulator API/device + run |
| External sandbox | Named sandbox/provider + environment/run |

A value such as “Windows/live as required” is acceptable only before AS-IS routing. Once the row is ACTIVE, it MUST be resolved to the exact environment and reason.

## 7. Dependency model

Dependencies are not inferred from row numbering.

**Execution dependency:** A → B means B cannot become ACTIVE/derived until A is PASS.

**Change-impact dependency:** component X → PASS row R means a change to X may invalidate R.

Therefore:

`CODE CHANGE → IMPACT ANALYSIS → AFFECTED PASS ROWS → REVALIDATION → RETAIN/REOPEN PASS`

The active row MUST name its exact prerequisite rows. “Depends on an older row” is invalid when the immediate invariant actually requires the current row.

## 8. Reuse/search record

For every non-PASS active row, search and record in this order:

1. Same repository
2. CDR Core
3. Software Forge
4. Git history
5. Mature OSS
6. Official libraries/documentation

For each inspected candidate record:

- source/repository;
- path/module/test;
- commit/version where relevant;
- observed behavior;
- contract compatibility;
- security implications;
- license where external;
- decision: REUSE / ADAPT / CONFIRM EXISTING / CREATE-NEW;
- reason.

**Reuse policy is not evidence.** The active row must contain the concrete inspected implementation/test when solution search matters.

## 9. Failure/recovery record

A failed row remains the active row until closed or explicitly classified as blocked by an external environment condition.

Required chain:

`FAIL → EXACT FAILURE → PROVEN ROOT CAUSE → SOLUTION SEARCH → MINIMAL PATCH → REGRESSION → RETEST → FRESH EVIDENCE`

Do not open an unrelated implementation row merely because the current row failed.

## 10. Contradiction and impact gates

Before PASS search for:

- duplicate implementations;
- old APIs with conflicting semantics;
- stale tests asserting old behavior;
- alternate UI/API paths bypassing the invariant;
- documentation claiming obsolete behavior;
- CI gates that can report PASS without executing the requirement;
- packaging/release paths that bypass the tested implementation.

Record the result in the active row.

If the patch changes a shared component, populate the Impact Set and revalidate only affected PASS rows.

## 11. Current execution cursor

**Current row: R002**  
**R001: PASS / CLOSED**  
**Later rows: NOT DERIVED / LOCKED by design**  
**Overall percentage: NOT VALID**  
**Merge: NOT PERFORMED**

### R001 — first MICU
| Field | Value |
|---|---|
| Row | R001 |
| Manifest Ref | docs/MANIFEST.md §2 — Core truth model; SHA 447b56f8a3a61ee34288730c705d9b0680c00e95 |
| MICU | Prove one concrete invariant: **evidence is never treated as truth/authoritative domain state by the decision path**. |
| Acceptance Criteria | Consequential decision paths preserve evidence/claim separation; evidence has provenance/confidence/hash, claims are separate via claim_evidence, and contradictory claims are explicit rather than overwriting prior observations. |
| Depends On | NONE |
| Unblocks | R002 derivation from the next unresolved §2 Core truth-model assertion |
| Code Location | marketradar/goal_completion.py; tests/test_manifest_alignment.py: temporal claim conflict + decision trace evidence binding tests |
| Code State | PRESENT |
| Current Behavior | AS-IS proves evidence and claims are separate; claim_evidence links them; decision traces retain evidence IDs/digest separately; conflicts are immutable. |
| Exact Gap | NONE PROVEN |
| Solution Search | Same repo implementation/tests inspected; no external patch needed. |
| Reuse Decision | CONFIRM EXISTING |
| Patch Action | NONE |
| Focused Test | python -m pytest -q; directly exercises the R001 assertions in tests/test_manifest_alignment.py. |
| Regression | Full MarketRadar regression suite in the same test-windows job. |
| Adversarial | Contradictory claim + immutable conflict ledger; immutable decision-trace delete/update attempts. |
| Required Environment | GitHub Actions test-windows, run 35881385337, job 107250431908, commit 29ca999366f6213c79b39de5eff795a5f94f5348. |
| Environment Owner/Why | Domain truth-model invariant; not Windows UI/product-packaging dependent. |
| Proof Command | python -m pytest -q |
| Expected Result | Evidence presence alone cannot create authoritative truth; contradictions remain explicit; decision traces remain evidence-bound and immutable. |
| Actual Result | **PASS** — test-windows completed successfully on the audited commit. |
| Evidence | GitHub Actions run 35881385337 / job 107250431908 |
| Evidence Type | CI / REGRESSION |
| Evidence Commit | 29ca999366f6213c79b39de5eff795a5f94f5348 |
| Artifact Identity | NONE |
| Evidence Time / Expiry | 2026-09-23; valid until the tested code path changes. |
| Reproducible | YES |
| Contradiction | NONE FOUND. Separate Windows qualification runner failure is not an R001 dependency. |
| Impact Set | NONE |
| Audit Update | R001 AS-IS, evidence, commit binding, contradiction and environment fields completed. |
| Audit Classification | VALID |
| Final Status | PASS |
| Execution State | CLOSED |

## 12. R002 — next JIT MICU

| Field | Value |
|---|---|
| Row | R002 |
| Manifest Ref | docs/MANIFEST.md §2 — Core truth model; SHA 447b56f8a3a61ee34288730c705d9b0680c00e95 |
| MICU | Prove that **UNKNOWN is a valid first-class state and is not silently converted into ALLOW/EXECUTE** by the decision/policy path. |
| Acceptance Criteria | Insufficient evidence produces explicit UNKNOWN/REVIEW semantics; no authorization/execution is granted solely because the value is unknown or absent; explicit hard BLOCK remains stronger than uncertainty. |
| Depends On | R001 |
| Unblocks | Next unresolved §2 truth-model assertion after R002 PASS |
| Code Location | marketradar/policy.py; marketradar/source_verification.py; tests/test_hardening.py; tests/test_final_architecture_16.py |
| Code State | PRESENT |
| Current Behavior | Existing tests/documentation show UNKNOWN-safe behavior, but fresh focused execution is required. |
| Exact Gap | FRESH EXECUTION EVIDENCE MISSING |
| Solution Search | Same repo first; CDR Core; Software Forge; Git history; mature OSS; official docs if needed. |
| Reuse Decision | CONFIRM EXISTING pending focused execution |
| Patch Action | NONE until focused proof demonstrates a defect. |
| Focused Test | Execute smallest UNKNOWN-safety tests covering eligibility/policy/authorization separation. |
| Regression | Relevant policy/security regression after focused test. |
| Adversarial | UNKNOWN/absent policy evidence must not become EXECUTE; explicit BLOCK must remain BLOCK. |
| Required Environment | GitHub-hosted Actions regression CI. |
| Environment Owner/Why | Domain policy invariant; platform independent unless AS-IS proves otherwise. |
| Proof Command | Focused pytest selection, then relevant regression suite. |
| Expected Result | UNKNOWN remains UNKNOWN/REVIEW and never silently becomes ALLOW/EXECUTE. |
| Actual Result | NOT EXECUTED |
| Evidence | NONE — R002 is ACTIVE. |
| Evidence Type | NOT EXECUTED |
| Evidence Commit | 29ca999366f6213c79b39de5eff795a5f94f5348 baseline; fresh execution required. |
| Artifact Identity | NONE |
| Evidence Time / Expiry | NONE |
| Reproducible | NOT EXECUTED |
| Contradiction | NONE FOUND so far; focused execution required. |
| Impact Set | NONE |
| Audit Update | R002 derived only after R001 PASS; exact active path to be confirmed during AS-IS. |
| Audit Classification | VALID |
| Final Status | NOT EXECUTED |
| Execution State | ACTIVE |

## 13. R001 execution protocol

1. Inspect the exact decision/evidence/domain-state code path.
2. Identify exact files/classes/functions and current tests.
3. Compare behavior directly to Manifest §2.
4. Record Code State and Exact Gap.
5. Search same-repo, CDR, Forge, history for proven solutions.
6. Select the reuse/implementation decision.
7. Run the focused positive assertion.
8. Run regression.
9. Run negative/adversarial proof where applicable.
10. Execute in the exact authoritative environment.
11. Capture evidence bound to the tested commit.
12. Run contradiction and impact checks.
13. Update the audit record.
14. Only when every applicable PASS gate is satisfied, set R001 = PASS.
15. Only then derive R002.

## 13. Coverage and traceability rule

The 139-row Matrix v2 is retained as a **coverage register**, not an execution queue.

When a MICU closes, its Manifest coverage mapping is updated. If one Matrix item contains multiple independently closable invariants, the active ledger may derive them JIT over multiple rows. If multiple Matrix items are one inseparable invariant, they may map to one MICU.

This prevents both failure modes:
- one coarse row hiding several unproven invariants;
- hundreds of pre-generated rows pretending to be executed work.

## 14. Revalidation rule

If evidence was produced for SHA A and implementation changes to SHA B:

**SHA-A evidence does not prove SHA-B behavior.**

Use:

`changed files → impact mapping → affected PASS rows → targeted revalidation → evidence refresh`

No automatic full-suite rerun is required unless the Manifest gate or impact analysis requires it.

## 15. Release truth

Passing the currently derived MICU queue does not make the product FINAL, Production, or Verified.

Release claims require applicable Manifest requirements to have been operationally decomposed and closed with fresh evidence.

## 16. Audit conclusion for v1.1

The previous 139-row operational ledger was structurally too close to a static requirement inventory.

v1.1 deliberately changes it to:

`LOCKED MANIFEST → COVERAGE MATRIX → AS-IS → ONE MICU → EXACT GAP → REUSE SEARCH → PATCH/EXISTING → FOCUSED TEST → REGRESSION → ADVERSARIAL → EXACT ENVIRONMENT → FRESH EVIDENCE → CONTRADICTION → IMPACT → PASS → NEXT MICU`

**Environment is retained.**  
**Dependency is row-specific and immediate.**  
**Generic templates are not closure evidence.**  
**Acceptance is minimum-sufficient and requirement-specific.**  
**Only the current MICU is active.**  
**Future rows are not guessed.**

# Manifest-Driven Execution and Qualification

Status: normative development-control document for SEPP-MarketRadar.

## 1. Purpose

Development progress is measured by Manifest requirement closure and evidence quality, not by commit count, workflow count, or GitHub activity.

The controlling loop is:

MANIFEST -> AS-IS AUDIT -> GAP MATRIX -> CONFLICTS -> IMPLEMENTATION -> TEST -> CI EVIDENCE -> AUDIT UPDATE

GitHub is one evidence environment, not the product authority.

## 2. Requirement closure

A Manifest requirement is closed only when the Definition of Done in Manifest section 46 is satisfied:

1. implementation exists;
2. regression coverage exists;
3. relevant adversarial/failure behavior is tested;
4. required environment evidence exists;
5. audit/reporting exposes the state;
6. contradictory legacy paths are removed or explicitly retired.

Code existence alone is never PASS.

## 3. Status vocabulary

Use only:

- PASS: evidence proves the requirement for its stated scope/environment.
- OPEN: requirement is not broken, but required evidence/capability is still missing or unavailable.
- FAIL: an executed check demonstrated a defect or contract violation.
- NOT EXECUTED: the required check has not yet been run.

Do not convert OPEN or NOT EXECUTED into PASS because another environment passed.

## 4. Environment ownership

| Requirement class | Primary evidence owner | Secondary evidence |
|---|---|---|
| Domain invariants | Regression / GitHub-hosted CI | Windows CI when platform-sensitive |
| Parser / normalization | Regression / GitHub-hosted CI | GitHub Windows |
| Core pytest | GitHub-hosted + fast regression | Windows Runner for Windows-specific regressions |
| EXE | Windows Runner | GitHub Windows only as supporting evidence |
| Installer | Windows Runner | Release audit |
| Windows UI | Windows Runner | UI smoke artifacts |
| Windows services / filesystem / registry | Windows Runner | None unless independently reproducible |
| Live source reachability | Windows Runner / live network | GitHub-hosted live probe where useful |
| 500+ source qualification | Windows Runner | Live network evidence |
| Dynamic JS/browser | Windows Runner | GitHub-hosted browser CI where independent |
| Android E2E | GitHub Linux + emulator | None required unless manifest changes |
| External payment/KYC/application | Real external/sandbox endpoint | Local contract tests |
| Manifest truthfulness | Regression + audit | All environment evidence as applicable |

A test is routed to the environment that can actually prove its claim.

## 5. Test deduplication

Do not execute a broad suite merely because a workflow exists.

For every GAP:

1. identify the exact contract;
2. identify the smallest regression that can prove/fail it;
3. identify the required environment;
4. run independent checks in parallel;
5. run broader qualification only when the targeted check passes or when the broader gate itself is the required evidence.

A PASS from a narrower test does not replace a required broader qualification gate.

## 6. Existing-solution-first rule

Before implementing a new solution, inspect in this order:

1. current MarketRadar implementation and tests;
2. CDR_Core implementation/tests/workflows/history;
3. Software_Forge implementation/tests/workflows/history;
4. prior MarketRadar commits, failures and patches;
5. mature open-source implementations;
6. official library/tool documentation and supported mechanisms.

Reuse/adapt when responsibility, contract, security boundary, and evidence model remain compatible.

Do not copy blindly. Record why the reused mechanism fits the requirement.

## 7. Failure loop

For every FAIL:

FAIL
-> reproduce
-> isolate root cause
-> search existing solutions
-> minimal patch
-> regression test
-> correct environment
-> CI/evidence
-> audit update

Environment noise must be separated from product defects. A transient runner/network failure is not silently classified as a product PASS or FAIL.

## 8. Parallel execution

Independent evidence tracks may run concurrently:

- manifest/code audit;
- regression coverage;
- sibling-repository harvesting;
- OSS/official-solution research;
- GitHub-hosted tests;
- Windows Runner tests;
- live-source qualification;
- Android qualification.

A blocked environment must not block independent work.

## 9. Evidence matrix

Every Manifest gap should be represented as:

Requirement
| Implementation
| Regression
| Adversarial/Failure test
| Required environment
| Latest evidence
| Status
| Contradictory legacy path
| Next action

Evidence must identify scope, environment, commit/ref, and relevant artifact/run where available.

## 10. Re-audit rule

After a patch:

1. update targeted regression;
2. execute targeted environment evidence;
3. execute impacted qualification gates;
4. inspect for contradictory legacy paths;
5. update the AS-IS/GAP evidence;
6. only then advance to the next unresolved Manifest gap.

## 11. Windows product authority

Windows is the primary product authority. EXE, installer, UI, Windows persistence, and OS-specific behavior require Windows evidence.

Mature packaging/tooling must be preferred over custom packaging infrastructure. For example, use the supported PyInstaller invocation and Windows-native build path rather than inventing a custom executable resolver.

## 12. No stale PASS inheritance

A historical PASS is reusable engineering knowledge, not automatic current evidence.

When a Manifest contract changes, the affected evidence must be requalified.

When the implementation is unchanged and the contract/evidence scope remains valid, historical evidence may be referenced rather than unnecessarily rerun, subject to audit freshness.

## 13. Progress metric

Progress is measured by:

- Manifest requirements with current evidence;
- required evidence environments covered;
- unresolved OPEN/FAIL/NOT EXECUTED gaps;
- contradictions removed.

Commit count, PR count, workflow count, and lines changed are not progress metrics.

## 14. Non-goals

This document does not redefine the Manifest domain model.

It does not weaken the Definition of Done.

It does not authorize merging.

It does not declare any requirement PASS without evidence.

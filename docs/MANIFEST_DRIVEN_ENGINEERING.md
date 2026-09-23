# Manifest-Driven Development & Evidence Framework

Status: normative development process for MarketRadar.

## 1. Decision chain

All engineering work MUST follow:

MANIFEST -> OUTPUT -> GOAL -> EVIDENCE -> TEST -> ENVIRONMENT -> REUSE -> EXECUTE -> FAILURE EXTRACTION -> ROOT CAUSE -> MINIMAL PATCH -> REGRESSION -> QUALIFICATION -> MANIFEST RECONCILIATION

GitHub is an evidence environment, not the product definition and not the decision authority.

## 2. Audit order

Before changing code for an OPEN/FAIL item:
1. Read the normative Manifest and identify the exact expected output.
2. Define the goal, acceptance condition, and evidence required to prove it.
3. Inspect AS-IS code, tests, audits, workflows, and prior failure history.
4. Search CDR Core, Software Forge, and MarketRadar for existing implementations, tests, failure fixes, and evidence patterns.
5. Search official tooling/docs, then mature libraries/open-source implementations.
6. Adapt the smallest proven solution; do not rebuild an already-solved capability.
7. Execute the test in the environment that can produce valid evidence.
8. On failure: Failure -> Root Cause -> Existing Solution -> Minimal Patch -> Regression -> Retest.
9. Update evidence and re-audit the Manifest gap.

## 3. Goal/evidence matrix

Every active Manifest goal is tracked as:

| Goal | Expected output | Evidence | Test | Environment | Existing solution | Status | Evidence reference | Gap/next action |
|---|---|---|---|---|---|---|---|---|

A green workflow is not a PASS unless it produced the evidence required by the goal.

## 4. Environment routing

| Evidence class | Primary environment |
|---|---|
| Python/dependency/compile/unit/regression | Appropriate hosted runner; Windows semantics on Windows |
| CI/Manifest/static contract | GitHub Actions |
| EXE packaging | Windows Runner |
| Installer/install/uninstall | Windows Runner |
| Real Windows UI | Windows Runner |
| Windows filesystem/registry/ACL/service | Windows Runner |
| Self-hosted environment behavior | Windows Runner |
| Live Internet/source reachability/acquisition | Windows Runner |
| Dynamic browser | Windows Runner |
| Android companion | GitHub Linux + Android emulator |
| External sandbox/credentialed endpoint | Environment owning the endpoint/credentials |
| Goal-level product behavior | Environment producing the required real evidence |
| Release artifact | Windows Runner + independent verification |

Queued jobs are not product failures; first establish runner-capacity state versus execution failure.

## 5. Reuse hierarchy

For every non-PASS gap:
1. MarketRadar existing implementation/tests/history.
2. CDR Core implementation/tests/history.
3. Software Forge implementation/tests/history.
4. Official tooling/library documentation.
5. Mature open-source implementations.
6. New code only when no suitable proven solution exists.

Reuse means adapting a proven pattern to the current contract and adding project-specific regression coverage.

## 6. Parallel execution

Independent evidence tracks MUST run in parallel where possible. Do not serialize unrelated Linux, Windows, Android, audit, source, or packaging work behind one queue. Do not duplicate tests that prove the same evidence unless redundancy is intentional.

## 7. Status discipline

- PASS = acceptance condition met with valid evidence.
- OPEN = required evidence is missing/incomplete or an external prerequisite is absent.
- FAIL = required test executed and acceptance condition was not met.
- NOT EXECUTED = planned test has not run.
- SKIPPED = intentionally not run under a documented condition.

Never infer PASS from code presence, workflow existence, or stale evidence. OPEN is not FAIL.

## 8. Qualification

Full Qualification aggregates goal evidence; it is not the starting point of engineering.

Release qualification is PASS only when every required gate has valid evidence and no required Manifest gate remains OPEN/FAIL. External realities such as real credentials, submissions, payment, and live accounts remain explicit evidence dependencies and must never be simulated into PASS.

## 9. Continuation contract

Future sessions MUST start from the current Manifest, AS-IS audit, evidence matrix, and git state. The next action is the highest-value unresolved GAP, not merely the next workflow in queue.

The repository is the durable handoff; chat history is not the source of truth.

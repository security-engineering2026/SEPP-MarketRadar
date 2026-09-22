# SEPP-MarketRadar Debug Handoff

## Source of truth
- Repository: security-engineering2026/SEPP-MarketRadar
- Branch: main
- Current debug baseline: 16.1.2
- Previous baseline: 16.1.1

## Protocol
1. Inspect current main before changing code.
2. Reproduce or establish a concrete defect.
3. Patch locally first when the execution environment permits.
4. Commit each logical debug stage to main.
5. Treat current main as the source of truth; Git history remains the audit trail.
6. Run regression and qualification after debugging is complete; never label unexecuted tests PASS.
7. OPEN is not PASS.
8. Synthetic fixtures are not live-market evidence.
9. Reachable source endpoints are not the same thing as verified connectors.
10. Windows and Android release readiness requires real build and E2E evidence.

## Findings fixed in 16.1.2
- QueryPlanner applied priority-region boost twice.
- Full qualification acquisition sampling depended on registry order; it is now deterministic and family-balanced.
- The 500-source gate is explicitly named as endpoint reachability and does not present that gate as proof of connector capability.

## Current repo observations
- sources.json has 679 registered records.
- release_snapshot.json reports 679 sources, 48 active, 20 daily, 0 daily execution-ready, 556 needs-analysis, 15 Iran-blocked.
- Verification is predominantly UNVERIFIED; the catalog is not proof of 679 verified integrations.
- PR #3 qualification/full-cycle-2 is not the source of truth; main remains authoritative until changes are deliberately integrated.

## CI evidence: 16.1.2 baseline run
- Full Qualification run 99 on commit 716fd33f1107257b3bfeaf5450b77e50bd5bd332: FAILURE.
- Windows core regression: 4 failures were exposed:
  - priority-boost regression expected 5.10 while the single-boost exact-mode score is 5.35; test expectation corrected.
  - release snapshot remained at 16.1.1.
  - search-snippet companion URL was not promoted to a candidate.
  - discovery_queries.json lacked the required known-onion-only policy block.
- Windows packaging/UI failures were also exposed:
  - portable build checked the wrong path after PyInstaller successfully produced dist\\MarketRadar.exe.
  - UI visual smoke could not import the package when invoked as a script.
  - installer version was stale at 16.1.1.
- Android build failed because Java target 1.8 and Kotlin target 17 were inconsistent.
- These defects were patched on main in subsequent commits. Version metadata is synchronized to 16.1.2; federation/discovery crawler user agents are synchronized; Android JVM targets are aligned to 17.
- The current main after the fixes must be re-run by GitHub Actions. No final PASS is claimed until fresh CI output exists.

## Latest CI result after 16.1.2 patches
- Full Qualification #111 on commit cdc4119 failed; core pytest was successful.
- Remaining Windows defects identified from real logs: full_qualification.py was executed as a script without the repository root on sys.path, causing six qualification gates to fail with ModuleNotFoundError; installer.iss resolved its Source path relative to packaging/ instead of repository root.
- Windows CI #132 on the same commit succeeded, so the base Windows regression/build path is healthy.
- Android compilation succeeded, but emulator E2E failed because the hosted emulator could not establish the adb daemon (exit code 1); this is an environment/runtime E2E issue, not an Android compile failure.
- Patches committed: 1d82586a6dbcd173a0efb57817c4719e3a08b4db and 5e6d2785875925eaccecf573805ab18a00ade265.
- Fresh Full Qualification #112/#113 and Windows CI #133/#134 are now queued. No final PASS is claimed.

## Next continuation
Use the newest main commit as the source of truth. Inspect the next push-triggered Windows CI and Full Qualification runs, extract every remaining FAIL/OPEN, patch only concrete defects, and commit each logical fix to main. Repeat automatically. After the debug cycle is exhausted, perform and record the final test pass with real output.


## 2026-09-22 — Temporal/Contradiction Patch

- Added immutable `claim_conflicts` ledger to preserve claim changes instead of silently replacing prior values.
- Pipeline now records `CONTRADICTS` relations between successive differing claims, retaining both claim records and linking their evidence.
- Added Manifest alignment regression coverage for conflict-ledger immutability.
- Commits: `cdb3acd5b11b9f896536e548df9f4726be3188b2`, `9e6e6f67cbc19a8996ec2dd33e8db6b41b8347bd`, `53f5103b91373880ef0b056a17cefdb88cdc8a42`.
- CI was triggered by the `main` pushes; combined status currently reports no completed checks yet. No PASS claim is made until GitHub Actions provides execution evidence.


## 2026-09-22 — Acquisition Fallback Patch

- Added ordered `AcquisitionFallback` provider contract with explicit provider provenance.
- Fallback carries a confidence multiplier and distinguishes source unavailability from provider failure.
- Added regression tests and fixed fallback metadata serialization before treating the patch as ready for CI.
- Commits: `c8c766044b9f69da50b946ffc5b71e99ef804220`, `07b356fa52d482bfed487b6d506c7347535d9c0b`, test `83020a56acb068a6362cd26093b4c61c6fe6de4c`.
- CI execution evidence is still pending; no PASS claim made.


## 2026-09-22 — Decision Trace patch
- Implemented universal immutable `decision_traces` ledger in `marketradar/goal_completion.py`.
- Daily recommendation decisions now capture policy version, target/action, parameter and evidence digests, evidence IDs, claims/state/ranking context, actor, reason and outcome.
- Authorization issuance also records approval reference, expiry and nonce in the same trace model.
- Regression coverage added in `tests/test_manifest_alignment.py`; audit updated to IMPLEMENTED BY CODE.
- Latest implementation commits: `475c83a999fd3ebef72509ca22822c8b8b481f40`, `5e3851c62a9223be48cd25d1299366feba4ff295`, `064f71ca368f3c3715db65551ccfe7bbc32f7713`.
- CI evidence is still required; no PASS claim made.

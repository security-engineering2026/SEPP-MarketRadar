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
Use the newest main commit as the source of truth. Inspect the next GitHub Actions Windows/Full Qualification runs, extract every remaining FAIL/OPEN, patch only concrete defects, and commit each logical fix. Live execution evidence comes from GitHub Actions or the existing Windows runner; no autonomous coding loop is used.


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


## 2026-09-22 — Decision Trace hardening
- Decision trace immutability was hardened: both UPDATE and DELETE are blocked by SQLite triggers.
- Regression coverage now verifies UPDATE attempts fail with the immutable-ledger error.
- Latest hardening commits: `5a1c09227665159a5bc80d44834b8a3cc7e21b78`, `af4cfb77c67ad3f77b5862e4ac629ed4b75fe7a8`.
- CI evidence is still required; no PASS claim made.
- Next audit target: Windows Product Qualification and remaining Manifest gaps.


## 2026-09-22 — Windows Product Qualification hardening
- Re-audit of `packaging/build_windows.ps1` found malformed portable artifact paths: executable/config/packaging destinations were concatenated instead of using directory separators.
- Patched the portable layout and runtime-data checks so the expected structure is `release\\portable\\MarketRadar\\...`.
- Commit: `6eba40cca6eb8960216d61286ee61e1ff8e6d1ad`.
- This is a code fix only; Windows CI must execute the build and installer smoke before PASS can be recorded.


## 2026-09-22 — Manifest hardening cycle
- Re-audit found the source capability ladder was still collapsing multiple Manifest stages. Added centralized monotonic maturity transitions and explicit evidence gates through EXECUTION_READY.
- Hardened consequential decision tracing so authorized execution success/failure creates immutable ACTION_EXECUTION traces; temporal contradiction status was also reconciled in the AS-IS audit.
- Capability commits: `ab47e9c6b503158d63165f4625e2f1705fdc5740`, `4f9320186b7bae0a7f0dcde0c969422e1f95b80c`, `6be136733ad4b9006516cca78ac80f47dcf46798`, audit `e290ff83e6aa4f05372231002caa6288a1de11d3`.
- Decision execution commits: `d4759ef61f0e2ce7f2d91a10668385a8bf3ecd57`, test `695387104ca3466153508d134d619dfcc37dc6c2`, audit `d6a07577acbd848356dfd7bbca60fafc2c0dad49`.
- No PASS claim: these are repository changes; fresh GitHub Actions execution evidence is still required.
- Next target remains Windows/Android/full post-audit qualification and any concrete CI failures.


## 2026-09-22 — Latest execution checkpoint
- Hardened Daily Intelligence Center with immutable `DAILY_SNAPSHOT` trace covering Top-7, Do-Now, approval, monitor, BLOCK and UNKNOWN buckets.
- Added regression test for snapshot trace coverage and immutability.
- Commits: `bca0f78c4e4c02c3b4b71d0ae92545d627c566ca`, `b0c6befb1ce478ac5a811078b25a3b701ed65671`, audit `7e6a8031fbefbb50326e7f697c9213c7b01c7c61`.
- Current qualification truth unchanged: no post-audit full Windows/Android qualification PASS has been observed; GitHub workflow evidence remains the gate.
- Next execution target: obtain fresh CI run evidence, then fix concrete Windows/Android/full-qualification failures rather than expanding features without evidence.


## 2026-09-26 — Autonomous engineering removal

- The repository-local autonomous coding/supervisor/overnight execution mechanism has been removed.
- Removed local coding-agent runners, autonomous supervisor/install scripts, overnight agent scripts, the autonomous engineering workflow, and their dedicated regression test.
- MarketRadar product functionality such as source discovery is unchanged; this removal is limited to autonomous software-engineering execution.
- Live engineering validation is now performed through the existing GitHub Actions workflows or the existing dedicated Windows runner.
- No PASS is inferred from repository edits; fresh live execution evidence remains required.

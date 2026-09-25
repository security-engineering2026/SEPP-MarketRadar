# SEPP-MarketRadar — Final Integration Plan

## Purpose
This document is the continuation controller for the final MarketRadar integration work. It does not redesign the product and does not reset historical work.

## Locked truth
- Normative contract: `docs/MANIFEST.md` (Manifest v1.0).
- Product baseline: v16.1.2.
- Historical R001–R049 evidence is preserved.
- R050 is PASS.
- R051–R068 remain closure-queue items in the current ledger.
- No Full Qualification, Windows runner, Android runner, or CI execution is launched by this plan.
- This plan is repository-side reconciliation only until an explicit execution request is made.

## Critical distinction
A passing component, test, or historical row does not prove that the real product entry point uses that component.

Acceptance is based on the integrated chain:

`real entry point -> controller/runtime -> acquisition/discovery -> observation -> evidence -> normalization -> opportunity -> eligibility/policy -> ranking/decision -> approval/authorization -> action -> outcome -> learning -> UI/report`

The clock rule applies: gears that pass individually still do not prove the clock works unless they are installed in the correct positions and turn together.

## Classification
Every existing implementation is classified as:
- **INTEGRATED** — the required capability is connected to the real runtime path.
- **BUILT_NOT_INTEGRATED** — implementation exists, but the required product path does not invoke it.
- **MISSING** — required implementation is absent.
- **EVIDENCE_ONLY** — implementation/integration exists, but current required proof is missing or stale.

Historical PASS is preserved. A later change only reopens an earlier PASS when its contract/evidence is actually affected.

## Operating loop
1. Inspect the locked Manifest requirement.
2. Trace the real product entry point.
3. Trace controller/runtime call-sites.
4. Locate the existing implementation that should perform the behavior.
5. Reuse it if responsibility/cohesion are correct.
6. Apply the smallest integration patch only if needed.
7. Run focused local evidence only; never invent PASS.
8. Record the result in the reconciliation.
9. Re-check impacted historical evidence.
10. Move to the next concrete gap.

## Current first integration candidate
### Desktop global Search
Observed current path:
`User query -> MarketRadarDesktop.search_all() -> refresh_opportunities() -> SQL LIKE over existing opportunities rows -> UI`

Current `refresh_opportunities()` filters only:
- source
- title
- eligibility
- state

It does **not** invoke the existing web-search/discovery capability.

Existing discovery capability is already real:
- `SourceDiscoveryEngine.discover()`
- `WebSearchProvider`
- `QueryPlanner`
- discovery evidence persistence
- source candidate persistence
- runtime `source_discovery_candidates()`
- CLI discovery paths

Therefore the candidate is **not** “build Search”. It is an integration question:
`Desktop Search -> existing runtime/discovery capability -> existing acquisition/pipeline path -> ranked opportunities -> UI`

Before patching, inspect all existing discovery/runtime call-sites and responsibility boundaries. Do not invent a second discovery engine.

## Required final proof
The final integrated proof must answer:

> When a user runs the real MarketRadar product from its real entry point, does the behavior defined by the locked Manifest execute end-to-end through the correct components and produce the expected final state?

R068 remains the final ledger truth condition. This document does not convert R068 to PASS.

## Change discipline
- No restart from zero.
- No replacement of the existing core engine.
- No duplicate implementation when an existing component already owns the responsibility.
- No CI/runner trigger as part of repository reconciliation.
- No merge of PR #63 without explicit authorization.

## Trace result — G-001
The discovery/runtime call-site trace is complete for the current baseline.

Observed orchestration:
- `tools/scheduled_cycle.py` calls `MarketRadar.verify_due_sources()`, then `MarketRadar.scan(mode='project')`, optionally `scan(mode='intelligence')`, and `daily_center()`.
- `MarketRadar.scan()` consumes the registered/dynamic source set and calls `MarketRadarRuntime.federate()`; it does not invoke `SourceDiscoveryEngine`.
- `marketradar/cli.py` owns the explicit `discover-sources` and `autonomous-discovery` orchestration. Those paths persist discovery evidence/candidates, optionally merge candidates through `sync_source_contracts()`, and autonomous discovery verifies newly imported candidates.
- `MarketRadar.__init__()` reloads dynamic source records and syncs them into the runtime source set, so discovery can feed later federation without duplicating acquisition logic.

Conclusion: there is no missing internal edge in the existing discovery -> registry -> federation chain. Discovery is intentionally a separate acquisition-of-sources operation; scheduled scanning consumes the resulting registry. The Manifest says discovery may use catalogs/search/public pages and that discovery creates candidates/provenance; it does not require the Desktop search box to execute live discovery.

Therefore G-001 is **not a Manifest closure blocker** and no Desktop-to-discovery patch is justified by the locked contract. The Desktop behavior remains a local opportunity-set filter, which may be a future UX enhancement but is not evidence of a missing Manifest requirement.

No code patch was made. No CI, runner, Full Qualification, or remote execution was triggered.

## R059 trace — local engine contract
R059 was inspected as the next executable closure item. The previous `engine_contract_gate()` only instantiated an `EngineManifest`, `EngineJob`, and `EngineResult` in memory, so it did not exercise the persisted job/result contract.

Minimal patch applied in `tools/full_qualification.py`:
- validate the real `EngineManifest` contract;
- persist an engine manifest into the real SQLite schema;
- build a real `EngineJob` using `build_job()`;
- persist the job as RUNNING;
- create the real `EngineResult`/`EngineQA` contract;
- persist the result/QA and transition the job to SUCCEEDED;
- reload the persisted JSON and assert job/result/QA identity and status.

Patch commit: `fdfdf707eb7c0131d854a3b251ce58dc9a88102c`.

Status: **PATCHED — focused execution evidence still required**. No CI/runner/Full Qualification was launched.

## R056/R057 trace — qualification taxonomy mismatch
The registry was inspected before changing the gates. Current `config/sources.json` contains concrete social families (`social_platform`, `telegram`, `instagram`, `x`, `linkedin`, `reddit`, `bale`, `eitaa`, `soroush`) and procurement-capable `market_intelligence`; it does not contain literal `social` or `procurement` source families. The qualification gate nevertheless required exact literal equality, causing a false `No registry candidates` OPEN state despite relevant registry surfaces existing.

Minimal patch: `family_surface_gate()` now maps qualification capability groups to the existing registry taxonomy and probes the actual candidates. A focused regression test was added. Patch commits: `6dbd2b220c4b981380671ee15ddd7cf449098250`, `40cc64055b0f8cdc06ed512f003575c28b7a8ec7`.

Status: **PATCHED / EVIDENCE_PENDING**. This corrects the qualification evidence harness; it does not claim that the external surfaces are reachable until the focused gate actually executes.


## R065 focused reconciliation
R065 was inspected after the R059/R056/R057 work. The existing packaging path builds the portable EXE, installer and source archive, but the qualification workflow did not previously record actual artifact size/SHA-256. Minimal evidence-contract patch: the Windows Full Qualification workflow now creates `qualification-artifacts/release_artifact_identity.json` containing schema, version, actual artifact path, size_bytes and SHA-256 for all three required release artifacts, and fails if any is missing. Commit `e4e87e7dca5633aa1a986d5ec2f4d67aa6271454`. Status: **PATCHED / EVIDENCE_PENDING**. No CI/runner execution was performed.

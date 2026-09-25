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

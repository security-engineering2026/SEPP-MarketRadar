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

## Next continuation
Run the regression and qualification workflow on updated main, inspect every FAIL and OPEN result, patch the next concrete defect, and repeat. Only after the debug cycle is exhausted, perform and record the final test pass with real output.

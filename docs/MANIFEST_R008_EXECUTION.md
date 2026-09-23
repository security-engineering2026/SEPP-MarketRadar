# R008 Execution Record — Learning Preserves History

- Invariant: Manifest §34 — Market learning
- Requirement: learning may use outcomes, source behavior, party behavior, pricing, TTM, acceptance and revenue, but MUST NOT rewrite historical observations.
- Status: PASS
- Execution state: CLOSED

## Implementation

No production code change was required. Existing outcome learning reads historical observations/outcomes and writes only derived learning tables.

## Regression

Added `test_manifest_learning_does_not_rewrite_historical_observations` in `tests/test_manifest_alignment.py`. The regression snapshots a raw observation and canonical opportunity, runs outcome learning, and proves both historical records remain byte/value identical and the observation remains singular.

## Evidence

- Tested code commit: `f123e4674970bee7fcce8068a81444e801d3ecd1`
- Windows CI run: `35892275484`
- Windows CI test job: `107287414472`
- Windows CI result: success
- Compile: success
- Full pytest: success
- Product audit: success
- Release audit: success
- Live-search smoke job: success; live discovery steps were skipped because the provider secret was not configured.

PR #17 remains open and unmerged.

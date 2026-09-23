# Manifest R010 Execution — Immutable Raw Evidence

## Status
PASS / CLOSED

## Contract
Manifest §10 — Immutable raw evidence.

Raw payloads MUST be hashable and replayable. Snapshot identity includes source, URL/endpoint, observation time, and content digest. Raw evidence remains distinguishable from normalized interpretation.

## Regression
Added `test_manifest_raw_evidence_identity_is_hashable_replayable_and_distinct`:
- verifies SHA-256 digest matches stored payload;
- verifies source/URL/observation time are retained;
- verifies duplicate snapshot identity is rejected;
- verifies raw payload cannot be updated or deleted;
- verifies the original payload remains replayable by identity.

Existing hardening coverage also enforces raw-observation immutability.

## Evidence
Tested commit: `8fe2c3487d8d703c08202b98fe9d4902deac3bb2`.

### Failure → Root Cause → Patch → Retest
- Windows CI run `35893075885` exposed a regression-test defect: the duplicate-identity check rolled back the transaction that contained the seed snapshot, so the later UPDATE/DELETE affected zero rows and falsely reported mutability.
- The production immutability triggers were already present and were not changed.
- The regression was patched to commit the seed raw snapshot before the negative UPDATE/DELETE checks.
- Final Windows CI run `35894088662` passed: Compile, full pytest, Product audit, and Release audit all PASS.
- Live-search smoke job completed successfully, with live discovery skipped because the provider secret is not configured; this does not affect the R010 database regression.

No production behavior change was required for this contract.

## Merge
No merge performed.

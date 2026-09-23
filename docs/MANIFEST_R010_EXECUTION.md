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
Tested commit: `f11a4381e7f81a158d491e3e28f1a748aa672555`.

No production behavior change was required for this contract.

## Merge
No merge performed.

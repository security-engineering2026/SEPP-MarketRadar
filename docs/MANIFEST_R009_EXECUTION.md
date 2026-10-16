# Manifest R009 Execution — Acquisition Fallback

## Status
PASS / CLOSED

## Manifest contract
Section 36 — Acquisition fallback.

Provider or adapter failure MUST be distinguishable from source absence. Fallback acquisition may improve coverage, but provider provenance and confidence differences MUST be preserved.

## Existing implementation verified
- `AcquisitionFallback` executes an ordered provider chain.
- Successful fallback records `acquisition_provider`, `fallback_used`, `confidence_multiplier`, provider-chain index, and prior attempt metadata.
- Provider exceptions are recorded as `PROVIDER_FAILURE`.
- HTTP 404/410 is classified as `SOURCE_UNAVAILABLE`.
- All-provider failure is surfaced as `ALL_ACQUISITION_PROVIDERS_FAILED`.
- Fallback never upgrades source capability or policy truth by itself.

## Regression coverage
`tests/test_acquisition_fallback.py` covers:
1. primary provider failure followed by secondary success;
2. explicit provider provenance;
3. fallback-used marker;
4. confidence multiplier preservation;
5. distinction between source unavailable and provider failure.

## CI evidence
Windows CI #230 / run `35840121528` completed successfully.
The corresponding Manifest alignment regression coverage executed successfully, including acquisition fallback outcomes/provenance.

This evidence is also recorded in `docs/DEBUG_HANDOFF.md` under the 2026-09-23 Manifest contract evidence closure checkpoint.

## Scope note
This PASS covers the acquisition-fallback contract and its regression/CI evidence. It does not claim that all live providers are configured or that dynamic discovery is universally available.

## Merge
No merge performed. PR remains unmerged unless explicitly authorized.

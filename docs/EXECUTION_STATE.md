# Market Radar — Execution State

**Contract:** docs/EXECUTION_CONTRACT_31_ROWS.md  
**Current row:** 3  
**Current status:** IN_PROGRESS  
**Execution direction:** 3 → 31, strictly sequential  
**Do not advance:** until current row has real PASS evidence.

## Current row 3 — SearXNG / Search Federation

### Known repository state
- SearXNG support already exists in the repository.
- Runtime/provider configuration and doctor/test infrastructure exist.
- The product contract requires proving that SearXNG is actually used by the Runtime discovery path, not merely configured.
- Language-aware and JSON-result handling must be verified.
- Fallback, timeout/error behavior and provenance must be verified.
- Windows CI and Full Qualification must be green for the applicable changes.

### Latest implementation work
- Discovery planner was adjusted so country/community discovery receives reserved cycle capacity instead of being starved by a small global query cap.
- Qualification/source selection was aligned with the current blocking-gate contract.
- These changes are not themselves a PASS for Row 3.

### Latest commits
- d3ee2203bc45b02cbce575d8b65121764a7710ac — TEST: align source scale gate assertion with current contract
- fd2a5adda309d9ce5fbf7bf30e07202e1f25aa68 — add this execution contract

### Required next actions
1. Inspect the actual SearXNG provider implementation and all Runtime call sites.
2. Verify query → SearXNG HTTP request → JSON parsing → normalized result → provenance → downstream discovery.
3. Verify language propagation from planner/config into provider requests.
4. Verify timeout, non-JSON/HTTP failure, empty result and malformed-result handling.
5. Verify fallback behavior and provenance when fallback is used.
6. Add/fix deterministic integration tests.
7. Run Windows CI and Full Qualification.
8. Use runtime evidence where possible.
9. Mark Row 3 PASS only after all applicable gates pass.
10. Immediately continue to Row 4 without waiting for user instruction.

## Rule

Do not tell the user a row is complete based only on a commit, a passing unit test, or a queued/in-progress workflow. Completion requires evidence.


### Current Row 3 execution checkpoint
- Provider path now accepts planner language and passes it to SearXNG; normalized results retain the actual provider as provenance.
- `auto` mode now attempts configured providers sequentially and falls back on provider errors/empty results; explicit provider mode remains strict.
- Added tests for SearXNG language propagation, malformed JSON, federation fallback/provenance, and discovery language propagation.
- GitHub Actions for commit `e3d4bf8020937f7bc8578c20742566fe700d5750` are currently queued; Row 3 is **not PASS** until CI/runtime evidence completes.
- Local container could not clone GitHub because outbound DNS/network is unavailable; no local test result is being represented as evidence.


## Chat continuation

The repository is now the cross-chat source of truth for continuation.

- User follow-up protocol: `docs/CHAT_CONTINUATION_PROTOCOL.md`
- Completion boundary: `docs/COMPLETION_BOUNDARY.md`
- Superset coverage: `docs/COMPLETION_MAP_100.md`
- Live cursor: this file
- Ordered execution contract: `docs/EXECUTION_CONTRACT_31_ROWS.md`

User should ask for the **current row/status**, not a fixed final row number. The chat must finish the current row to real PASS, record evidence, then continue automatically to the next row.

# v4.14.0 Patch Audit — Corrected Source Tree

This archive is the corrected working source tree after an exhaustive follow-up red-team/professor pass over the v4.10.4 tree.

## Defects corrected in this pass

1. **Lifecycle race result was unstable** — a concurrent transition could become `INVALID_TRANSITION` instead of the domain-level `STATE_RACE`. The transition path now captures the expected state, serializes the write boundary, re-checks the state, and reports stale competitors deterministically.
2. **Hard policy precedence was incomplete** — KYC/terms blocks could be hidden by an earlier UNKNOWN result. All explicit hard blocks now dominate evidence uncertainty.
3. **Dry-run was not fully dry in the older tree** — raw observation persistence and health/error persistence were guarded so dry-run has no database side effects.
4. **Runtime source blocks could be lost across registry synchronization** — federation now consults the persisted runtime verification state in `source_contracts`, which is preserved by sync.
5. **SQLite trigger migration was unsafe** — `CREATE TRIGGER IF NOT EXISTS` allowed old definitions to survive upgrades. Managed triggers are now replaced transactionally, after required legacy columns are migrated.
6. **Compatibility engine ignored configured timeout** — `MarketRadar(root=...)` now loads the configured HTTP timeout.
7. **Release version audit was incomplete** — User-Agent and Android version metadata are now checked against the core version.

## Validation

- 166 test functions: full pytest PASS under Xvfb and headless pytest PASS with the expected GUI-only skip
- Python AST parse: PASS
- compileall: PASS
- Desktop UI smoke under Xvfb: PASS
- Clean release audit: PASS
- Legacy-schema migration regression: PASS
- Concurrency regression: PASS
- Dry-run mutation regression: PASS
- Windows EXE/installer execution: NOT CLAIMED in this Linux environment

## 4.14.0 additional audit fixes

8. **Dashboard crashed with populated SQLite data** — `sqlite3.Row` was incorrectly accessed with `.get()`; dashboard rendering now uses row indexing and has a populated-data GUI regression test.
9. **Lifecycle state could be changed directly without an application event** — a DB trigger now requires a matching immutable event for every state mutation.
10. **Opportunity/source records could be deleted directly** — deletion is now blocked so evidence, provenance and historical source identity cannot be orphaned.
11. **Acquisition attestation trusted a stored hash without recomputing the payload hash** — attestation now hashes the persisted raw payload before accepting it.
12. **Registry sync could erase historical source identity and was not exception-atomic** — missing sources are disabled and sync rolls back on failure.
13. **Health persistence could erase policy metadata** — existing Iran/KYC/payment/execution metadata is preserved unless explicitly supplied.
14. **Dry-run / registry verification could bypass persisted source blocks** — preflight now enforces blocked-source boundaries before any network request.
15. **Android companion source/resources were missing from the release tree** — restored and added to release audit checks.


## 4.14.0 product-completeness pass
The product-level audit found that the previous release had architecture placeholders rather than the requested user-facing capabilities. v4.14.0 adds cross-region source contracts, authorized Telegram/Reddit/X/LinkedIn boundaries, country-aware Iran/Israel execution policy, structured crypto revenue metadata, need-to-tool analysis, resume/proposal generation, submission planning, authorized submission connectors, Action Center and Career Kit. The 500-source target remains a real expansion target and is not fabricated as operational coverage.
## 4.14.0 deep source/policy pass

16. **Iran origin was incorrectly mixed with employer/client blacklist policy** — Iran was removed from the execution blacklist; Israel remains the explicit blacklist.
17. **Global sources were incorrectly mixed with Iran-compatible daily sources** — added `GLOBAL_DISCOVERY` and made active daily sources require `iran_status=ALLOW`.
18. **Source-policy evidence was not persisted** — added policy basis, URL, checked date, source origin and upstream-source attribution to the DB contract.
19. **Iran source selection was incomplete** — added Kaya as an Iran-facing intermediary and ManMitonam as a domestic candidate; kept ParsCoders and other existing Iranian sources in the daily lane.
20. **Exact duplicate source contracts inflated registry breadth** — removed five exact duplicate URLs.
21. **Source Strategy double-click crashed** — removed the nonexistent `sources.notes` SQL column reference and added an interaction regression test.
22. **Global scan results were not separated from Iran daily acquisition** — scan telemetry now reports daily and global discovery counts independently.
23. **Blocked sources were incorrectly considered promotable by the registry audit** — blocked-lane records are now excluded from the promotable set.

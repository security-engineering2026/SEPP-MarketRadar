## v16.1.1 — Windows Locking Hotfix + Release Integrity (2026-09-19)

- Fixed Windows file-lock cleanup for `marketradar.log` when runtime data roots are temporary or changed between application instances.
- Added explicit logging shutdown on application/desktop close plus safe reconfiguration when the data root changes.
- Added a regression test for log-handle release.
- Synchronized installer, discovery/federation user-agent, Android version metadata, CLI final-verification filename, and release snapshots to v16.1.1.
- Local gate: 264 collected / 263 PASS / 1 SKIPPED; release/product/architecture audits report errors=0.

## v16.1.0 — Final Jury Release (2026-09-18)

Final jury cycle integrated and re-audited: source constraints/surface discovery, finance/account routing, reporting, email lifecycle tracking, Android companion gateway, and release-integrity hardening.


## v16.1.0 — Integrated Architecture Finalization (2026-09-18)

- Added evidence-based Work Taxonomy / Task Understanding while preserving legacy opportunity-intelligence fields.
- Added source lanes for hourly execution scanning, twice-daily market intelligence, review, and archived blacklist.
- Reframed the former 500-source target as a discovery-pool benchmark; execution sources are evidence-qualified and Iran-compatible.
- Added source deduplication by canonical host and persistent source scan state.
- Added user profile/domain/level-aware daily recommendations with Top 7 and 3 visible by default.
- Added provider-aware Capability Registry; no connected Engine no longer rejects a project. Manual execution remains possible.
- Added Provider/Engine manifests for Python, Web Bug Bounty, Android Bug Bounty, and Student/Office services.
- Added Product Opportunity generation from market-intelligence-only sources with evidence-backed task/output counts and build specs.
- Added Persian Daily Center actions for manual request and automatic-engine readiness.
- Added blacklist archives for source/opportunity records instead of deletion.
- Hardened fresh-database schema creation and final lifecycle verification.

# SEPP-MarketRadar 15.0.0 — Final Release
## 15.0.0 — Final Operationalization Pass

- Added executable operationalization acceptance for the canonical market pipeline.
- Added replayable 1000-opportunity → top-7 → top-3 validation.
- Added local economic-loop acceptance proving payment claim remains DELIVERED until explicit verification transitions to PAID.
- Exercised market signals, demand clustering, product/service recommendations, skill gaps and portfolio recommendations in one integrated run.
- Added `operationalization` CLI command and `reports/OPERATIONALIZATION_15.0.0.json`.
- Fixed skill-profile compatibility so both list-style and mapping-style skill profiles are accepted by the portfolio intelligence engine.
- Preserved strict external evidence gates: live sources, real market data, authorized external submission, settlement verification and Windows certification are never simulated as PASS.


## Final baseline
- Unified the complete Market → Evidence → Intelligence → Decision → Action → Revenue → Learning loop.
- Hardened source federation, autonomous discovery, evidence/provenance, policy, identity, reputation and opportunity intelligence.
- Hardened application lifecycle and approval/authorization boundaries.
- Added durable project contracts, milestones, communications, deadlines and follow-ups.
- Added application-status evidence and authorized polling.
- Separated payment claim from payment verification; only verified settlement reaches PAID.
- Added payment verification attempts and authorized payment polling.
- Added final project reporting with lifecycle timing, milestones, communications, follow-ups and payment evidence.
- Added Windows portable/installer build path, UI smoke tests, worker modes and scheduled tasks.
- Added final release self-verification including schema, backup/restore and economic lifecycle proof.
- Added Windows CI release gates for EXE, installer, install/uninstall and smoke testing.

## Release integrity
15.0.0 is the final product baseline. External facts remain evidence-gated and UNKNOWN when the required provider/runtime evidence is unavailable.


## Final hardening pass
- Added deterministic release-hardening gates for config, SQLite integrity, orphan detection, lifecycle invariants, shipped-file presence, and secret-field review.
- Added Windows DPAPI protection helpers with fail-closed non-Windows behavior.
- Added Windows ACL and Authenticode verification hooks.
- Added dependency vulnerability audit to the Windows release pipeline.
- Added `release-hardening` CLI gate and bound it to final verification.

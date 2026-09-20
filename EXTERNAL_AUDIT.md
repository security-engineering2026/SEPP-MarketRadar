# External-Reviewer Audit — v4.14.0

This review was performed as if an independent instructor/reviewer were checking the student's product rather than trusting the project's own claims.

## Findings and resolutions

### 1. Fake scale in Source Registry — HIGH
**Finding:** The previous registry contained 495 placeholder records using `example.com` while presenting a 500+ registry shape.

**Resolution:** Placeholder records were removed from the operational registry. `source_targets.json` now expresses the 500+ strategic target separately. Only onboarded source contracts remain in `sources.json`.

### 2. Source verification was too close to HTTP success — HIGH
**Finding:** HTTP 200 was insufficient evidence that an adapter understood the feed.

**Resolution:** Verification now requires adapter parsing plus content-type compatibility. Empty/invalid feeds become degraded rather than verified.

### 3. Retry policy retried policy/programming errors — HIGH
**Finding:** Non-transient validation failures could fall through the retry loop.

**Resolution:** Retries are limited to transient network failures and selected HTTP statuses. HTTP errors are checked before the `URLError` superclass so 4xx policy errors such as 401/403/404 stop immediately. Validation/policy errors stop immediately.

### 4. Registry shrink left stale database contracts — HIGH
**Finding:** Removing a source from the registry did not remove its stale current contract/source row.

**Resolution:** Registry synchronization now reconciles current state and removes stale current rows while retaining health history and onboarding events.

### 5. Opportunity URLs were not canonicalized — MEDIUM
**Finding:** Tracking parameters and fragments could create duplicate opportunities.

**Resolution:** URLs are canonicalized before persistence and evidence is normalized against the canonical URL.

### 6. Budget parser crashed on valid currency formats — HIGH
**Finding:** `USD 1,200` could raise an index error.

**Resolution:** Currency-before-amount and amount-before-currency formats are parsed independently and tested.

### 7. Revenue + Android notification could split transactionally — HIGH
**Finding:** Revenue could be committed before an Android notification failed.

**Resolution:** Revenue transition, message creation and audit are now one transaction; notification failure rolls the payment state back.

### 8. Source health contract drift — HIGH
**Finding:** `sources` could show a new verification state while `source_contracts` still showed the old state.

**Resolution:** Health persistence updates both current source state and its contract; registry synchronization now refreshes contract metadata without overwriting runtime technical verification state.

### 9. Windows release gate was incomplete — HIGH
**Finding:** The workflow built the installer but did not prove that the installed executable could start and write to its installed-user data location.

**Resolution:** CI now runs both portable and installed EXE smoke tests. Installer staging excludes `.portable`.

### 10. Release hygiene — MEDIUM
**Finding:** Development cache artifacts could enter a source ZIP.

**Resolution:** Release audit rejects `__pycache__`, `.pytest_cache`, `.pyc`, `.db`, and `.log` artifacts. Packaging is performed only after cleanup.

## Remaining external dependency

A real Windows runner is still required to prove the final EXE/installer behavior. Linux verification cannot substitute for that evidence.

### 11. Disabled source was eligible for default verification — HIGH
**Finding:** The default verification selector included any source marked `documented`, `verified` or `degraded`, so a disabled source with a stale verification state could still be network-targeted.

**Resolution:** Default verification now selects only `active` sources. Explicitly named sources remain available for deliberate operator checks.

### 12. Atom feeds were accepted by the content-type contract but not parsed — HIGH
**Finding:** The adapter advertised RSS/Atom compatibility but `parse_rss()` only iterated RSS `<item>` nodes, causing valid Atom feeds to become empty/degraded.

**Resolution:** The parser now handles Atom `<entry>` elements and Atom link/summary/content fields, with regression coverage.

### 13. Android companion version metadata drift — MEDIUM
**Finding:** The Android companion still declared the older 4.1.1 version while the desktop/core release had advanced.

**Resolution:** Android companion `versionName` and `versionCode` are aligned to v4.9.2. This is metadata alignment only; no Android build is claimed here.

## 14. v4.9.5 Red-Team/Professor Audit — CRITICAL SSRF boundary
**Finding:** Hostname validation resolved a public hostname and then delegated the actual connection to urllib, which could resolve the hostname again. A DNS rebinding attacker could therefore pass the public-IP check and cause the HTTP client to connect to a private address.

**Validation evidence:** An adversarial local test changed the DNS answer from a public address during validation to `127.0.0.1` for the connection; the pre-v4.9.5 implementation reached the local HTTP endpoint.

**Resolution:** The acquisition path now resolves the hostname, validates the complete answer set, and connects to the selected resolved IP directly. HTTPS preserves the original hostname for TLS SNI/certificate validation. Redirects repeat the same validation/pinning boundary.

## 15. v4.9.5 Red-Team/Professor Audit — audit/financial record tampering
**Finding:** Raw observations were append-only, but audit records, application events, revenue records, federation runs, health history, onboarding events, and approval records were still directly mutable/deletable through SQLite.

**Resolution:** These historical records are now protected by SQLite triggers. Approval binding fields are immutable after issuance, and replay state cannot be cleared once used.

## 16. v4.9.5 Red-Team/Professor Audit — transaction ownership
**Finding:** `record_revenue(commit=False)` could roll back a caller-owned transaction when its own insert/transition failed, violating the meaning of the non-committing API.

**Resolution:** The function no longer rolls back the connection. The caller owns the transaction when `commit=False`; `MarketRadarRuntime.record_payment()` retains the explicit rollback boundary around the complete payment + Android-message transaction.

## 17. v4.9.5 Red-Team/Professor Audit — XML parser hardening
**Finding:** DTD/entity declarations were rejected, but the parser still used the standard library XML parser directly.

**Resolution:** RSS/Atom parsing now uses `defusedxml.ElementTree` as defense in depth against XML entity/resource abuse.

## 18. v4.9.5 Red-Team/Professor Audit — Windows CI evidence
**Finding:** Previous CI built and smoke-tested Windows artifacts but did not run the full Python test suite on the Windows runner before packaging.

**Resolution:** Windows CI now runs pytest, cleans generated test artifacts, runs the release audit, and only then builds the portable EXE and installer.

## 19. v4.9.5 Adversarial Architecture Audit — cross-source poisoning

**Finding:** A lower-quality source could overwrite the canonical opportunity row when two sources exposed the same canonical URL. Provenance was preserved, but the intelligence payload itself could be poisoned.

**Resolution:** Opportunity updates now require a strictly higher `quality_score` than the current canonical record. Lower/equal-quality observations still record source provenance and observation time without replacing the established intelligence record.

## 20. v4.9.5 Adversarial Architecture Audit — Android message replay

**Finding:** HMAC authenticity did not itself provide persistent replay protection; a valid message could be presented repeatedly to a stateless verifier.

**Resolution:** Android envelopes now receive a persistent `message_id`; SQLite stores issuance/expiry metadata and a single-use `consumed_at` state. Verification can consume atomically, and message binding fields are immutable.

## 21. v4.9.5 Adversarial Architecture Audit — orphan domain records

**Finding:** `PRAGMA foreign_keys=ON` was enabled, but several existing tables lacked declarative foreign keys, allowing orphan evidence/application/revenue/opportunity-source rows to be inserted.

**Resolution:** Insert-time SQLite integrity triggers now reject orphan references for domain records that must belong to an opportunity. This preserves compatibility with the existing schema while enforcing the invariant for new writes.

## 22. v4.9.5 Professor Review status

The v4.9.5 review was performed against the extracted release tree with adversarial tests, including DNS rebinding, approval forgery/rebinding, persistent approval replay, Android replay, cross-source poisoning, orphan-record insertion, transaction ownership, unsafe XML, retry classification, blocked-source bypass, and content-type contract violations.

Remaining release-level limitations are explicitly documented: real 500+ source onboarding is not complete, terms review remains pending for the five public sources, and Windows EXE/installer execution still requires a Windows environment/runner rather than Linux-local evidence.


## v4.9.5 — State / Race / Evidence Audit

### 23. State transition TOCTOU — FIXED
The application state update now uses a compare-and-set `WHERE id=? AND state=?` guard after validation. Concurrent stale writers cannot both commit the same transition.

### 24. Approval and Android replay races — VERIFIED
Persistent approval consumption and Android message consumption are atomic single-use updates and were exercised from separate SQLite connections.

### 25. Evidence/provenance spoofing — FIXED
Source-declared `provenance_root` is no longer trusted. Unattested ingestion is capped at 0.75 confidence; acquisition-attested ingestion may retain adapter confidence, while the provenance root is always the authoritative source name.

### 26. Post-action intelligence mutation — FIXED
After an opportunity leaves `DISCOVERED`, later observations cannot rewrite the actionable snapshot (title, score, eligibility, etc.). They remain available as evidence/provenance.

### 27. Direct financial lifecycle bypass — FIXED
SQLite now rejects direct `revenue` inserts unless the referenced opportunity is in `DELIVERED`.

### Professor Review Status
The v4.9.5 audit found and fixed the material state/race/evidence defects above. Remaining architecture limitations are documented separately; passing tests are not treated as proof of zero defects.


## 23. Historical v4.9.6 Final Professor / Red-Team Audit

The final audit targeted the remaining material integrity surfaces: DB-level state invariants, application-event consistency, revenue cardinality/lifecycle, acquisition-attestation boundaries, source trust/quality poisoning, federation retry/error semantics, responsibility cohesion, and packaging readiness.

### State / DB integrity
- Database now rejects unknown opportunity states and illegal state transitions even when SQL bypasses the Python state-machine helper.
- Application events must reference an existing opportunity and their `to_state` must match the opportunity's current state.
- PAID requires an existing revenue record.

### Revenue / financial integrity
- Revenue requires DELIVERED state, positive/non-empty core fields, and one payment record per opportunity. Existing immutable-record and payment-reference protections remain active.

### Source trust / provenance
- Pipeline ingestion no longer accepts a caller-controlled boolean as proof of acquisition. Runtime passes a structured acquisition attestation tied to the source, HTTP success status, URL and snapshot hash.
- Source-declared provenance roots remain ignored; acquisition source owns the provenance root. Unattested evidence remains conservatively capped.

### Federation / reliability
- HTTP error retry classification remains transient-only; retry attempts, size limits, redirects, host boundaries and pinned DNS connections remain enforced.
- Adapter/content-type validation remains mandatory before parsing.

### Architecture / responsibility
- Acquisition, parsing, normalization, quality, policy, application, revenue and runtime orchestration remain separated. The new integrity checks were added at the DB boundary rather than duplicating business logic across unrelated modules.

### Verification result
- 95 automated tests: PASS.
- compileall: PASS.
- release audit on clean tree: PASS.
- source audit: 6 valid, 0 invalid; 5 active public sources + 1 disabled local test.
- Windows EXE/installer execution remains explicitly unclaimed because this audit environment is Linux.

**Historical assessment:** v4.9.6 met its then-defined engineering release gate; it is not the current release. This does not mean the future 500+ source expansion or actual Windows artifact execution has magically occurred; those remain external expansion/validation gates.

## 24. v4.9.7 Final Windows-release audit

The v4.9.6 release was re-extracted and independently re-reviewed after a desktop UI quality complaint and an application-event integrity review. The desktop interface was redesigned without adding runtime dependencies. Application transition events are now DB-authoritative: the insert trigger validates the current state and legal edge, then an AFTER trigger applies the state change in the same transaction. A race test was re-run after the change.

Validation performed on a clean extraction included the 97-test pytest suite, Python compilation, Tkinter desktop construction under Xvfb, GUI screenshot inspection, release audit, archive cleanliness checks, and three repeated clean extractions. No Windows EXE execution is claimed from Linux; the Windows GitHub Actions workflow remains the authoritative Windows build/install smoke gate.


## 25. v4.10.1 Presentation-layer redesign

The desktop presentation layer was independently reviewed against established market-intelligence and BI interaction patterns. The UI was refactored without moving acquisition, pipeline, security, lifecycle, or revenue responsibilities into the presentation layer. The release adds persistent workspace navigation, contextual filtering, KPI overview, activity visualization, source-health views, federation monitoring, and opportunity/source drill-down panels. UI smoke validation is executed under a real Tk display in CI/local Xvfb; this does not claim a native Windows executable was run in this Linux environment.


## 26. v4.10.1 Release / Distribution Audit

The v4.10.0 release was re-opened for an independent release-engineering review before Windows distribution. The review found several release-boundary defects: the installer version audit accepted any `#define MyAppVersion`, the Windows workflow did not validate that a tag matched the application version, the portable build did not execute the UI smoke gate, the installer gate did not verify the UI smoke path or uninstall removal, and the workflow uploaded CI artifacts but did not publish a GitHub Release. These were corrected in v4.10.1.

Additional version drift was found and corrected in the README, Android companion metadata/versionCode, and federation User-Agent. The changelog was also checked for accidental duplicate current-version sections.

Validation on the Linux audit environment: 109/109 tests pass; release audit reports 6 registered sources, 5 active, 0 invalid, 6 documented warnings, and 0 errors; no current-version drift remains outside the historical changelog. The actual Windows EXE, installer, UI smoke, uninstall, and GitHub Release publication remain intentionally unclaimed until the v4.10.2 GitHub Actions Windows job executes successfully.


## 27. v4.10.2 Professor / Red-Team audit

A line-by-line review of the v4.10.1 source tree found material defects that ordinary tests did not expose: the desktop activity chart queried a non-existent `created_at` column and silently rendered zero activity; lifecycle filter options included states that do not exist in the application state machine; global opportunity search filtered only the first 300 ranked rows; `raw_observations` stored normalized opportunity items rather than the actual acquired response; acquisition attestations were not bound to a persisted response hash; evidence and opportunity-source provenance records were mutable through direct database writes; post-execution opportunity action fields were not DB-frozen; and source contract declared verification state was overwritten by runtime verification state. These were corrected in v4.10.2 and covered with new regression tests. The audit also found and corrected an RSS 1.0 namespace parsing gap, IPv6 URL canonicalization, and test/runtime state isolation that could otherwise dirty a developer environment. Finally, source onboarding and the federation boundary now reject invalid access scopes and unsupported active acquisition families, and payment timestamps must carry an explicit timezone.

Validation boundary remains explicit: Windows EXE/installer execution is not claimed until the Windows workflow actually runs.


## 28. v4.10.4 second independent pass

A second source-tree audit of the v4.10.3 artifact found additional defects outside the previous 113-test boundary: an unstable concurrent lifecycle transition result, incomplete hard-policy block precedence, a dry-run persistence leak, runtime source-block loss after registry synchronization, and a migration flaw where `CREATE TRIGGER IF NOT EXISTS` could preserve older security triggers. The compatibility engine also ignored configured HTTP timeout, and release auditing did not fully verify version alignment. These were corrected and covered by new regression tests. Current local validation is 122/122 tests, compileall PASS, AST PASS, UI smoke PASS, and clean release audit PASS. Windows execution remains explicitly unclaimed until the Windows workflow runs.

## 29. v4.14.0 exhaustive pass

An additional broad source-tree audit was performed beyond the existing regression suite. It exercised populated GUI state, direct database mutation paths, persisted source-block paths, registry-removal behavior, raw-response hash integrity, policy metadata preservation, and release-tree Android completeness. The pass found seven material defects and corrected them. Local validation is now 131/131 tests, including Xvfb GUI execution; Windows EXE/installer execution and Android Gradle compilation remain unclaimed because this audit environment does not provide those target runtimes/toolchains.


## 30. v4.14.0 product-capability audit
A separate product-level pass compared the executable source tree against the requested product behavior rather than only prior regression tests. It found that the earlier tree did not actually implement resume generation, need-to-tool analysis, country-aware Iran/Israel execution policy, structured crypto payment metadata, or user-facing application planning/authorized submission boundaries, and its source registry covered only six operational records. v4.14.0 adds those capabilities and expands the registry to 619 registered source contracts across multiple regions. Telegram, Reddit, X and LinkedIn remain explicitly authorization-gated and are not claimed live without credentials/approval. Local validation is 139/139 under Xvfb; Windows EXE/installer execution and Android Gradle compilation remain unclaimed in this Linux environment.

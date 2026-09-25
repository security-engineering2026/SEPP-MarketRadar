# SEPP-MarketRadar — Manifest Execution Reconciliation

## Source of truth
- Normative Manifest: `docs/MANIFEST.md`
- Operational ledger: `docs/MANIFEST_EXECUTION_LEDGER.md`
- AS-IS audit: `docs/MANIFEST_ASIS_AUDIT.md`
- Debug handoff: `docs/DEBUG_HANDOFF.md`
- Branch reviewed: `process/final-qualification-hardening`
- Product baseline: v16.1.2

## Important ledger correction
The current operational ledger does **not** contain 68 independent physical table rows. It contains one grouped baseline row `R001–R049`, followed by individual rows `R050` through `R068`.

Therefore this reconciliation preserves the ledger exactly rather than inventing 49 fake one-to-one rows.

## Historical baseline

| Ledger row | Status | Meaning | Reconciliation treatment |
|---|---|---|---|
| R001–R049 | PASS | Previously executed Manifest requirement set, including R046–R049 qualification/audit/architecture evidence | Preserve. Do not blindly rerun. Reopen only if a later change affects its contract/evidence. |
| R050 | PASS | Final-qualification regression contract | Preserve. Evidence recorded in ledger: Windows CI 35974142391 / job 107550508738 / commit b48628eafee324d8826181d1557a4fe0c8cb1a26. |

## Final closure queue

| Row | Current status | Depends on | What must be true | Integration classification |
|---|---|---|---|---|
| R051 | NOT EXECUTED | R050 | Windows compile, pytest, qualification gates, audits, EXE/installer/smoke/install/UI/uninstall and final decision | EVIDENCE_ONLY until fresh execution |
| R052 | NOT EXECUTED | R050 | Android assemble + emulator E2E + artifact capture | EVIDENCE_ONLY until fresh execution |
| R053 | NOT EXECUTED | R051 | Configured SearXNG endpoint executes live global discovery successfully | EVIDENCE_ONLY / environment-owned |
| R054 | NOT EXECUTED | R051 | 500 current registry candidates are actually live-reachable | EVIDENCE_ONLY / environment-owned |
| R055 | NOT EXECUTED | R054 | Real acquisition yields an observed opportunity/event with provenance | EVIDENCE_ONLY |
| R056 | NOT EXECUTED | R054 | Social-family registry candidates are reachable | EVIDENCE_ONLY / environment-owned |
| R057 | NOT EXECUTED | R054 | Procurement-family registry candidates are reachable | EVIDENCE_ONLY / environment-owned |
| R058 | NOT EXECUTED | R051 | Authorized dynamic target rendered by Playwright with title/body/screenshot evidence | EVIDENCE_ONLY / environment-owned |
| R059 | NOT EXECUTED | R051 | Local engine manifest/job/result contract executes and validates | EVIDENCE_ONLY |
| R060 | NOT EXECUTED | R051 | Configured external engine sandbox accepts qualification payload without production side effects | EVIDENCE_ONLY / environment-owned |
| R061 | NOT EXECUTED | R051 | Configured application sandbox accepts qualification payload without production side effects | EVIDENCE_ONLY / environment-owned |
| R062 | NOT EXECUTED | R051 | Configured payment sandbox accepts qualification payload without production side effects | EVIDENCE_ONLY / environment-owned |
| R063 | NOT EXECUTED | R051 | Configured push sandbox accepts qualification payload without production side effects | EVIDENCE_ONLY / environment-owned |
| R064 | NOT EXECUTED | R051–R063 | AS-IS audit reflects actual final-qualification evidence and has no stale contradiction | EVIDENCE_ONLY |
| R065 | PATCHED / EVIDENCE_PENDING | R051 | Portable EXE, installer, source archive with actual identity/path/size/SHA-256 | EVIDENCE_ONLY until execution |
| R066 | NOT EXECUTED | R065 | Clean Windows install -> smoke -> UI -> uninstall with no leftover executable | EVIDENCE_ONLY |
| R067 | NOT EXECUTED | R064–R066 | Product audit + release audit + qualification report agree | EVIDENCE_ONLY |
| R068 | NOT EXECUTED | R067 | One fresh end-to-end candidate from source/build through product workflow, Android, artifacts, uninstall and final decision | EVIDENCE_ONLY; final truth row |

## Manifest contract reconciliation

| Manifest section | Existing implementation observed | Current interpretation |
|---|---|---|
| 2 Core truth model | Raw observations, evidence, claims, policy/decision records, outcomes exist across DB/runtime | Built; integration must be traced at final product level |
| 4–7 Source registry/adapter/capability/verification | Registry, source contracts, maturity ladder, verification records and stale/revalidation fields exist | Built and historically evidenced; no reset |
| 8 Discovery | SourceDiscoveryEngine, QueryPlanner, WebSearchProvider, candidate/provenance persistence | Built and integrated through CLI/discovery paths; Desktop global Search does not currently call it |
| 9 Acquisition | Federation fetch path with host/timeout/retry controls and provenance | Integrated in federation path |
| 10–13 Evidence/observation/opportunity/dedup | raw observations + Pipeline.ingest + opportunity history | Integrated in federation/pipeline path; final product proof remains separate |
| 14–17 Entity/party/trust | Entity/party/trust components and audit evidence exist | Built; preserve historical PASS; trace affected final paths only |
| 18–21 Eligibility/payment/KYC/policy | Pipeline and runtime expose these stages | Integrated in opportunity processing; policy remains distinct from ranking |
| 22–26 Temporal/intelligence/ranking/decision/daily center | temporal fields, intelligence, ranking, decision snapshots and daily center exist | Built/integrated in core paths; final end-to-end evidence still belongs to closure |
| 27–29 Approval/authorization/action | approval broker, authorization broker and action execution paths exist | Integrated core capability; final release evidence is separate |
| 30–35 Lifecycle/delivery/revenue/outcome/learning | lifecycle, delivery, payment verification, outcome ledger and learning components exist | Integrated core capability; final release evidence is separate |
| 36–38 Fallback/scheduler/security | fallback provenance, scheduler state/retry, host/SSRF/security controls exist | Built/integrated; preserve existing evidence |
| 39 Windows product | packaging/build/installer/smoke implementation exists | EVIDENCE_ONLY for current final qualification until fresh authoritative run |
| 40 Android companion | Android companion and successful prior E2E evidence exist | Historical PASS preserved; current closure still ledger-controlled |
| 41–45 Observability/audit/integrity/UI/reporting | runtime status, immutable traces, constraints, UI states and audits exist | Built/integrated; final audit must reconcile actual candidate |
| 46–49 Definition/governance/development/final architecture | Manifest governance and architecture are documented and tested in prior evidence | Preserve; no invented new requirement |

## Current integration gap register

### G-001 — Desktop global Search path
**Classification:** BUILT_NOT_INTEGRATED (for the specific behavior of turning a user search into discovery/acquisition).

**Observed path:**
`MarketRadarDesktop.search_all() -> refresh_opportunities() -> SQL LIKE over existing opportunities`

**Existing capability available elsewhere:**
`SourceDiscoveryEngine.discover() -> WebSearchProvider/QueryPlanner -> discovery candidates/evidence`

**Why this matters:**
The product contains a real discovery subsystem, but the desktop global Search currently searches the already-stored opportunity set. The distinction is between “search the local result set” and “run market discovery”.

**Do not do:**
- Do not rebuild WebSearchProvider.
- Do not build a second discovery engine in Desktop.
- Do not bypass source policy/acquisition controls.
- Do not assume Manifest explicitly mandates that the search box itself must discover live sources.

**Next inspection:**
Trace the existing CLI/runtime discovery orchestration and determine the smallest cohesive runtime method that can accept a user query without moving discovery responsibility into the UI.

**Patch status:** NOT STARTED.

## Evidence policy
- Code presence is not integration proof.
- Unit/regression PASS is not final product PASS.
- Historical CI PASS is preserved but is not silently reinterpreted as current runtime proof.
- Environment-owned gates remain environment-owned.
- No synthetic live-market evidence is accepted.

## Current cursor
**First concrete reconciliation target: G-001 Desktop global Search integration boundary.**

No code patch is authorized by this document until the remaining discovery/runtime call-sites are traced and the smallest existing responsibility boundary is identified.

## G-001 trace closure
**Result:** No code patch required.

The trace confirmed that discovery is already integrated at the correct system boundary:
- explicit CLI discovery executes `SourceDiscoveryEngine` and `WebSearchProvider`;
- discovery persists candidate/provenance state;
- applied/autonomous discovery synchronizes new source contracts;
- `MarketRadar` reloads dynamic source records;
- scheduled `scan()` consumes the source registry and calls `MarketRadarRuntime.federate()`;
- `federate()` feeds the existing `Pipeline.ingest()` path.

The Desktop Search box only filters existing opportunities. The locked Manifest does not state that a UI search query must launch live discovery. Consequently G-001 is reclassified from `BUILT_NOT_INTEGRATED` to **NON-BLOCKING UX ENHANCEMENT / NOT A MANIFEST GAP**. It is not added to R051–R068 closure work.

No runner/CI/qualification execution was performed during this trace.

## R059 focused reconciliation
R059 exposed a qualification-evidence weakness: the prior gate constructed contract objects but did not exercise their persistence path. The gate was minimally hardened to use the existing `engine_contract` and real SQLite `engine_manifests` / `engine_job_runs` schema, then reload and validate the persisted job/result/QA.

Patch: `fdfdf707eb7c0131d854a3b251ce58dc9a88102c`.

Current status: **PATCHED / EVIDENCE_PENDING**. This is not marked PASS until the focused gate executes successfully. No runner or CI execution was performed.

## R056/R057 focused reconciliation
Trace found a qualification-harness defect rather than a missing product component: `family_surface_gate("social")` and `family_surface_gate("procurement")` compared literal family names that are absent from the registry taxonomy. Existing registry families include social-platform variants and `market_intelligence` for procurement/tender surfaces.

The gate was patched to use an explicit taxonomy mapping, and a regression test was added. Commits: `6dbd2b220c4b981380671ee15ddd7cf449098250`, `40cc64055b0f8cdc06ed512f003575c28b7a8ec7`.

Current status: **R056/R057 PATCHED / EVIDENCE_PENDING**. No reachability PASS is asserted without execution.


## R065 focused reconciliation
**EVIDENCE_ONLY** for current final qualification. The packaging path exists, but the qualification workflow previously did not record artifact size/SHA-256. The workflow is now patched to emit `qualification-artifacts/release_artifact_identity.json` with version/path/size/SHA-256 for the portable EXE, installer and source archive. Commit `e4e87e7dca5633aa1a986d5ec2f4d67aa6271454`. Focused/CI execution is still required; do not mark PASS from code inspection.

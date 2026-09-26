# Market Radar — Audited Remaining Work Master Table

Status: NORMATIVE EXECUTION QUEUE
Audit date: 2026-09-26
Manifest: docs/MANIFEST.md
Superset audit: docs/COMPLETION_MAP_100.md
Previous sequence: docs/EXECUTION_CONTRACT_31_ROWS.md

## Purpose

This table replaces the old 31-row table as the **remaining-work execution cursor** after an AS-IS audit of the current repository tree, Manifest, existing tests, release/qualification records, and completion map.

Already implemented/verified work is not repeated. A row appears here only because it is still OPEN, IN_PROGRESS, RUNTIME-GATE, or requires fresh current-candidate evidence.

The order below is the only execution order for the remaining Market Radar work. Row 1 is the next job. A row must reach PASS before the next row starts.

## Mandatory research gate for EVERY row

Before PASS, the active row must have a research packet containing:
- at least **10 independent non-GitHub sources** relevant to that row;
- at least **5 and at most 10 comparable software/products/platforms** relevant to that row;
- official documentation/vendor material where available;
- at least one independent/industry source where useful;
- concrete patterns adopted, rejected, or adapted;
- source URLs, access date, and the exact requirement/code decision influenced;
- no copying of proprietary code/content;
- contradictions recorded instead of silently selecting convenient claims.

Research is input to engineering, not a substitute for tests.

## Runtime rule

Authoritative execution resources:
1. GitHub Actions / repository CI;
2. user's Windows self-hosted runner;
3. user's main Windows environment via explicit PowerShell commands when required.

A queued GitHub job is **not** a blocker. If a runner is unavailable or queued, classify the environment failure and use the next authorized environment capable of proving the same contract. Code/test failure must never be hidden by changing environments.

## Remaining queue

| Row | Source gates | Remaining work | Required proof |
|---:|---|---|---|
| 1 | 11–14 | Close SearXNG provider, federation, language propagation, normalized result/provenance path | real SearXNG request + focused/regression + Windows/CI evidence |
| 2 | 22 | Prove 1000+ bounded/resumable source operation | real scale run, memory/time/error evidence |
| 3 | 25 | Real source-health verification at scale | live Internet verification with persisted evidence |
| 4 | 38 | Close active-source warnings/ambiguities | live source-policy review and persisted resolution |
| 5 | 39 | Authorized social/API runtime evidence | authorized runtime connectors, no bypass |
| 6 | 53 | Real-market 1000→7→3 decision evidence | live discovery, dedup, ranking, rationale evidence |
| 7 | 64 | Newly added capability automatically changes search end-to-end | add capability → search plan/query/result proof |
| 8 | 74 | Site-specific authorized application adapters | real permitted adapter execution and constraints |
| 9 | 75 | Browser session recovery | real browser interruption/recovery proof |
| 10 | 77 | Real user-approved application submission | one authorized submission with evidence |
| 11 | 78 | Acceptance/rejection/status ingestion from a real source | real lifecycle/status evidence |
| 12 | 80 | Authorized external follow-up sending | real permitted follow-up path |
| 13 | 87 | Fiat settlement verification where configured | real settlement evidence or explicit N/A |
| 14 | 88 | Chain-specific crypto settlement verification | configured chain runtime proof or explicit N/A |
| 15 | 89 | Acceptance → delivery → payment end-to-end | real economic lifecycle evidence |
| 16 | 90 | Revenue/outcome learning from completed real work | persisted outcome → learning signal proof |
| 17 | 95 | Refresh dependency/supply-chain/security evidence | current scan/SBOM/exception evidence |
| 18 | 97 | Operational health metrics, alerts and SLO evidence | running system telemetry + alert exercise |
| 19 | 99 | Incident response/runbook/recovery rehearsal | controlled incident drill + evidence |
| 20 | 100 | Target deployment restart/disaster/failure recovery | Windows target recovery drill |
| 21 | Distribution | Windows native EXE build | actual artifact + hash + startup |
| 22 | Distribution | Windows installer execution | install/upgrade/uninstall evidence |
| 23 | Distribution | Windows clean-machine startup | clean-host evidence |
| 24 | Distribution | Windows scheduler installation and execution | actual scheduled scan |
| 25 | Distribution | Process restart/recovery after failure | kill/restart/reconcile proof |
| 26 | Distribution | Real configured SearXNG instance | live configured instance exercise |
| 27 | Distribution | Live Internet source verification | real source observations |
| 28 | Distribution | Android APK build/deployment | actual APK artifact |
| 29 | Distribution | Android device/emulator E2E | install/use/recovery evidence |
| 30 | Distribution | External engine/connector execution | actual authorized connector execution |
| 31 | Distribution | Real authorized application submission | target-side evidence |
| 32 | Distribution | Real payment/settlement verification | target-side payment evidence |
| 33 | Cross-cutting | Reconcile all 100-map statuses against current candidate and reopen only impacted earlier gates | impact analysis + current evidence |
| 34 | Final | Full qualification, release audit, installability and final acceptance against Manifest + this table | complete release evidence; no OPEN mandatory row |

## Completion rule

The product is not called complete until Row 34 passes and the final acceptance check confirms that no applicable OPEN/RUNTIME-GATE item remains in the Manifest or Completion Map.

Historical PASS is retained as evidence and is not re-executed unless change-impact analysis invalidates it.


## Locked execution mode — Baseline-first / Evidence-first / Gap-only

The existing executed baseline is the starting implementation. For every row: **PRESERVE** proven working behavior; **FIX** verified defects; **COMPLETE** partial implementations; **BUILD** only genuinely missing capability. The queue is not a rebuild plan. Valid historical evidence must be recovered before re-execution, and no working component is replaced merely to satisfy a row.

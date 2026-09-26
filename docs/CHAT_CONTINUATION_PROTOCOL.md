# Market Radar — Chat Continuation Protocol

Status: NORMATIVE
Repository: security-engineering2026/SEPP-MarketRadar
Normative Manifest: docs/MANIFEST.md
Remaining-work queue: docs/REMAINING_WORK_MASTER_TABLE.md
Research gate: docs/RESEARCH_GATE_STANDARD.md
Superset audit: docs/COMPLETION_MAP_100.md

## Single execution rule

The **Remaining Work Master Table** is now the active queue. The older 31-row table remains historical/traceability material and must not be used to restart completed work.

Every chat must:
1. read the Manifest, Remaining Work Master Table and current evidence;
2. identify the first remaining row not PASS;
3. inspect/reuse existing code, tests, history and evidence before coding;
4. perform the required research packet (10+ non-GitHub sources and 5–10 comparable products);
5. implement only the proven gap;
6. test focused + regression + failure/adversarial + required runtime environment;
7. record exact commit/evidence;
8. mark PASS only when the row's acceptance contract is proven;
9. immediately continue to the next row without waiting for a new user message;
10. update the queue/state before chat handoff.

## Runner policy

GitHub queueing is never itself a reason to stop.
If GitHub-hosted execution is unavailable, classify the environment failure and use the user's Windows self-hosted runner or main Windows PowerShell when that environment can prove the same contract. A genuine code/test failure remains a product failure and must be fixed.

## No duplicate work

A completed row is not reopened unless current code/evidence changed, evidence is invalid/expired, or impact analysis finds a contradiction. Historical PASS must be recovered from repository/history before any re-execution decision.

## User commands

The user can simply say:
- "وضعیت؟"
- "ادامه بده"
- "ردیف فعلی رو تا PASS واقعی کامل کن و بعد برو بعدی."

Do not ask the user to name the row.

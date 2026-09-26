# Market Radar — Chat Continuation Protocol

Status: NORMATIVE
Repository: security-engineering2026/SEPP-MarketRadar
Canonical execution contract: docs/EXECUTION_CONTRACT_31_ROWS.md
Coverage boundary: docs/COMPLETION_MAP_100.md
Execution state: docs/EXECUTION_STATE.md

## How the user should follow progress

Do NOT ask for "row 31" unless the project is already near the end.

Use one of these short commands in the Market Radar chat:
- "وضعیت Market Radar؟"
- "ردیف فعلی کجاست؟"
- "ادامه بده"
- "ردیف فعلی را تا PASS کامل کن و بعد خودکار برو ردیف بعد."
- "بر اساس EXECUTION_STATE و COMPLETION_MAP_100 ادامه بده."

The chat must read the repository state before doing work. The current row in EXECUTION_STATE is authoritative.

## Execution rule

The chat must:
1. inspect existing implementation before adding code;
2. reuse working paths and tests;
3. execute the current row completely;
4. test implementation, integration, failure behavior and required runtime environment;
5. record exact commit/test/CI/runtime evidence;
6. mark PASS only when the row's PASS contract is actually satisfied;
7. immediately continue to the next row without waiting for another user message;
8. use COMPLETION_MAP_100 as the superset boundary so finishing Row 31 cannot silently create a new category of work;
9. leave an exact checkpoint in EXECUTION_STATE before context/chat handoff;
10. stop only for a genuine external blocker and state the single concrete user action required.

## No false completion

Code/config/docs alone are not completion evidence.
Mock-only tests do not prove live integrations.
Queued, cancelled or runner-provisioning-failed jobs do not count as successful product evidence.
Runtime-gated items remain runtime-gated until the required environment is actually exercised.

## Completion boundary

Rows 3–31 are the execution sequence.
COMPLETION_MAP_100 is the coverage universe.
A row or final release may not remove, hide, rename or postpone a requirement merely to obtain PASS.

Final product wording is allowed only after the final acceptance gates in both documents are satisfied.

## Handoff requirement

At every checkpoint record:
- current row;
- status;
- latest commit;
- tests/CI/runtime evidence;
- exact blocker, if any;
- next row;
- affected completion-map gates.

This file exists so a new chat can continue from the repository without relying on conversation memory.

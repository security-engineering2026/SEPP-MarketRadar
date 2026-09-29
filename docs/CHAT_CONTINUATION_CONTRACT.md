# SEPP-MarketRadar Chat Continuation Contract

Status: normative execution-process contract for engineering chats
Repository: security-engineering2026/SEPP-MarketRadar
Authoritative branch: main
Current baseline: 16.1.2

## Purpose

Every new engineering chat MUST continue from the repository's current evidenced state. A chat is not allowed to restart the project from memory, recreate already-closed work, invent missing evidence, or silently change the execution methodology.

This document controls the assistant's engineering workflow. It does not add product requirements to the System Manifest.

## 1. Source of truth

1. Current `main` is the source of truth.
2. Git history is the audit trail.
3. Open or stale branches/PRs are not authoritative unless deliberately integrated into `main`.
4. Historical PASS evidence remains historical; a later change can reopen an affected requirement.
5. Closed rows must not be re-executed unless impact analysis shows they were reopened.
6. UNKNOWN and OPEN remain explicit states. OPEN is never PASS.

## 2. Required continuation sequence

Every chat MUST use this sequence:

```
INSPECT CURRENT MAIN
  -> IDENTIFY CURRENT OPEN ROW / DEFECT
  -> DEFINE ONE BOUNDED CHANGE
  -> IMPLEMENT SMALLEST COHERENT INCREMENT
  -> ADD/UPDATE REGRESSION COVERAGE
  -> RUN RELEVANT TEST
  -> REVIEW ACTUAL RESULT
  -> IF FAILURE: DIAGNOSE -> PATCH -> RETEST
  -> RUN REQUIRED REGRESSION / QUALIFICATION
  -> RECORD EXACT EVIDENCE
  -> UPDATE HANDOFF
  -> SELECT NEXT CONCRETE ACTION
```

The assistant MUST NOT jump directly from an idea to implementation without inspecting current main and the relevant evidence.

## 3. One-cycle rule

One chat turn/cycle must have one concrete engineering objective.

Do not bundle unrelated feature work.

The default unit is:

```
one defect/gap
+ smallest coherent code change
+ direct regression
+ exact execution evidence
```

After the result is known, decide the next action.

## 4. Evidence discipline

The assistant MUST distinguish:

- repository code exists;
- regression test passes;
- CI/build passes;
- runtime qualification passes;
- release gate passes.

These are different claims.

The assistant MUST NOT write PASS, COMPLETE, VERIFIED, production-ready, release-ready, or equivalent language unless the corresponding required execution evidence exists.

A passing unit test is not proof of live source qualification.

Synthetic fixtures are not live-market evidence.

Reachability is not capability.

Registration is not verification.

## 5. Failure-first engineering

When a test or qualification fails:

1. stop broad expansion;
2. preserve the exact failure;
3. inspect the failing path;
4. identify the smallest concrete defect;
5. patch only that defect;
6. add or repair regression coverage;
7. rerun the narrow test;
8. only then continue to broader regression/qualification.

Do not hide, downgrade, reinterpret, or delete a failure to obtain a green result.

## 6. Branch and PR discipline

For normal engineering work:

- work against current `main`;
- create a reviewable logical branch/PR when a change is required;
- do not create multiple competing branches for the same defect;
- do not continue from a stale branch when a mainline-integrated continuation already exists;
- before creating another patch, compare the candidate branch with current `main`;
- merge only after the required review/evidence gate.

For the current Row 4 work, PR #73 is the current mainline-integrated qualification candidate. PR #72 is historical/stale and must not be treated as the active source of truth.

## 7. Chat-to-repository handoff

At every meaningful checkpoint, `docs/DEBUG_HANDOFF.md` MUST record:

- current main commit;
- baseline/version;
- rows closed/PASS and their evidence;
- current OPEN/FAILED/UNKNOWN row;
- exact observed evidence;
- exact code/test changes already made;
- active PR, if any;
- what must NOT be repeated;
- one next concrete action.

A new chat must read this handoff before making changes.

## 8. User execution boundary

The assistant may inspect and modify repository content through the connected GitHub workflow.

When local execution is required:

1. assistant gives the exact command;
2. user runs it in the real environment;
3. user returns the exact output;
4. assistant interprets the result;
5. only then is the next execution command selected.

Do not assume a command ran successfully.

Do not ask the user to rerun a long qualification when a narrower diagnostic can establish the cause.

## 9. No autonomous repository engineering loop

The repository-local autonomous coding/supervisor/overnight execution mechanism was removed on 2026-09-26.

This chat contract therefore does NOT authorize or recreate an autonomous coding loop inside MarketRadar.

Live engineering validation remains through the existing repository CI and the user's permitted local Windows execution environment.

## 10. No runner escalation

Do not introduce new requests to the user's self-hosted Windows runner as a default recovery mechanism.

If an environment-specific gate is required, first inspect existing CI evidence and determine whether the required evidence can be obtained without changing the user's runner setup.

## 11. Model/strategy lock

All future engineering chats for this repository MUST preserve the current methodology:

```
current main
-> current evidence
-> one concrete gap
-> smallest coherent change
-> direct regression
-> real execution evidence
-> diagnose/repair on failure
-> update handoff
-> continue
```

A new chat must not replace this with:

- broad speculative feature development;
- repeated full-suite reruns without diagnosis;
- reopening closed rows without impact evidence;
- branch/PR proliferation;
- claims based only on code inspection;
- silent changes to Manifest semantics;
- fabricated external-source evidence;
- autonomous overnight coding.

## 12. Current checkpoint

As of this contract's creation:

- Rows 1-3 are PASS/CLOSED and must not be repeated without impact analysis.
- Row 4 is OPEN.
- Row 4 concerns closure of active-source Terms/Legal evidence warnings.
- Current active-source population is 48.
- The latest mainline-integrated Row 4 candidate is PR #73.
- Row 4 remains OPEN until its dedicated runtime qualification produces the required evidence.
- The next chat must inspect current `main` and PR #73 evidence before changing code.

## 13. Definition of a good next chat

A correct new chat should be able to begin with:

```
Read:
  docs/CHAT_CONTINUATION_CONTRACT.md
  docs/DEBUG_HANDOFF.md
  docs/MANIFEST.md

Then:
  inspect current main
  inspect current active PR/evidence
  identify the single current blocker
  execute only the next required action
```

No project history reconstruction from memory is required.

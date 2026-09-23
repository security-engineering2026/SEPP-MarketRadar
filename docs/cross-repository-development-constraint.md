# Cross-Repository Development Constraint

**Status:** MANDATORY  
**Scope:** This repository and the other two repositories in the Engineering Learning Network.

## Engineering Learning Network

These three repositories are developed and tested together:

- `security-engineering2026/SEPP-MarketRadar`
- `security-engineering2026/Software_Forge`
- `security-engineering2026/CDR_Core`

They must be treated as an **Engineering Learning Network**, not as three isolated projects.

## Mandatory cross-repository inspection

Before designing or implementing a new solution, inspect the other two repositories for relevant:

- implementation and source code
- architecture and responsibility boundaries
- contracts and schemas
- regression tests
- CI workflows and qualification gates
- Windows Runner results
- failure history and root causes
- patches and recovery mechanisms
- audit and evidence mechanisms
- EXE / Installer / portable-build patterns
- data relationship and search patterns
- qualification and goal-verification mechanisms

If another repository has already solved a similar problem or has a proven test result, evaluate reuse or adaptation **before building a new solution from scratch**.

If another repository has failed on a similar problem, inspect the failure, root cause, and patch so the same failure is not repeated elsewhere.

## Reuse rule

Reuse must never be blind copying.

Before adapting a solution, evaluate:

1. responsibility and cohesion
2. coupling and dependencies
3. contract compatibility
4. domain-specific assumptions
5. test/evidence portability
6. security and operational implications

A PASS in one repository is evidence for that repository only. It becomes a candidate for reuse elsewhere after the evidence and domain differences are checked.

## Shared engineering loop

```
Implementation
  -> CI / Windows Runner
  -> PASS / FAIL
  -> Root Cause
  -> Minimal Patch
  -> Evidence
  -> Reusable Engineering Knowledge
  -> Other Repositories
```

A proven solution from one project is a candidate for accelerating the other two.

A failure from one project is reusable negative knowledge: its root cause and corrective action should be considered before implementing an equivalent capability elsewhere.

## Project roles

### CDR Core
Windows / EXE / Installer / Desktop Hardening / Data Relationships / Search / Regression

### Software Forge
Engineering Control Plane / Contracts / Goal Verification / Failure Graph / Recovery / Audit / Evidence

### SEPP-MarketRadar
Source Federation / Acquisition / Policy / Claims / Decision Trace / Opportunity Intelligence / Qualification

## Evidence discipline

Cross-repository learning does not change the evidence standard:

- Code existence is not proof of completion.
- A test must have real evidence before it is marked PASS.
- Product/domain evidence must not be confused with engineering-control evidence.
- Environment-specific failures must be classified before being treated as product defects.
- No project may inherit a PASS merely because another project passed an analogous test.

## Operational requirement for future work

When working on any one of these repositories, relevant work in the other two must be considered as part of the implementation path. The objective is continuous engineering knowledge transfer while preserving each repository's domain boundaries.

This document is a repository-level handoff/constraint and should remain synchronized with the corresponding documents in the other two repositories.

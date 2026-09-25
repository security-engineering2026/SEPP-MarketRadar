# SEPP-MarketRadar — Final Runtime Flow Map

## Scope
This map describes the architecture that must be traced as an integrated system. It is not a claim that every edge has fresh end-to-end evidence.

## Flow A — Market intelligence

```
Real user/scheduled trigger
        |
        v
Entry point
  |-- Desktop UI
  |-- CLI / scheduled cycle
  |
  v
Controller / MarketRadarRuntime
  |
  +--> Discovery/query planning
  |      |
  |      +--> SourceDiscoveryEngine
  |      +--> QueryPlanner
  |      +--> WebSearchProvider
  |      |
  |      +--> candidate + provenance
  |
  +--> Source registry / contract / capability gate
  |
  +--> Acquisition / Federation
  |      |
  |      +--> source-bound fetch
  |      +--> timeout/retry/host policy
  |      +--> raw observation + digest
  |
  v
Pipeline.ingest()
  |
  +--> validation / normalization
  +--> payment + KYC detection
  +--> evidence cleaning / quality
  +--> eligibility
  +--> policy / blacklist
  +--> opportunity type
  +--> ranking factors
  +--> application readiness
  |
  v
Canonical Opportunity + observation history
  |
  v
Eligibility / KYC / payment intelligence
  |
  v
Versioned Policy Decision
  |
  v
Ranking
  |
  v
Decision Snapshot / Daily Intelligence Center
  |
  v
Desktop UI / reports
```

## Flow B — Authorized action

```
Opportunity
  -> decision context
  -> human approval or defined low-risk policy
  -> authorization broker
  -> exact action binding
  -> preconditions
  -> action execution
  -> immutable audit / decision trace
  -> external reference/result
```

## Flow C — Outcome and learning

```
Action
  -> submission response
  -> acceptance/rejection/cancellation
  -> delivery evidence
  -> payment claim
  -> payment verification
  -> outcome ledger
  -> FinancialObservation / LearningSignal
  -> outcome learning
  -> new intelligence
  -> new decision
```

## Truth boundaries
The following distinctions are mandatory:
- Observation != Evidence
- Evidence != Claim
- Claim != Decision
- Recommendation != Authorization
- Authorization != Execution
- Execution != Outcome
- Payment claim != Payment verification
- Registration != Verification
- Reachability != Capability

## Current integration finding
Desktop global Search is presently a presentation-layer database filter:

`search_all() -> refresh_opportunities() -> SELECT ... FROM opportunities WHERE ... LIKE ...`

The existing discovery/search subsystem is elsewhere and already contains:
`SourceDiscoveryEngine -> WebSearchProvider -> discovery evidence/candidates`.

This means the current question is an **integration boundary** question, not a missing-search-feature question.

## Responsibility boundary
- Desktop owns presentation and user interaction.
- Runtime owns executable orchestration.
- Discovery owns discovery and provenance.
- Federation/acquisition owns source-bound acquisition.
- Pipeline owns normalization/domain processing.
- Policy owns deterministic policy decisions.
- Ranking owns prioritization.
- Approval/authorization own permission to act.
- Outcome/learning own post-action truth.

A patch should connect these boundaries without moving responsibilities into Desktop or duplicating discovery logic.

## Evidence rule
A flow edge is not marked PASS merely because both endpoint functions exist. Evidence must show that the real runtime path invokes the edge and produces the expected downstream state.

## Trace result — discovery and scheduled scanning
The real call-sites confirm two separate but connected flows:

```text
Explicit discovery command
    -> SourceDiscoveryEngine
    -> candidates + provenance
    -> persist candidates/evidence
    -> sync_source_contracts (when applied/imported)
    -> dynamic source records
    -> MarketRadar reload
    -> scan
    -> MarketRadarRuntime.federate
    -> Pipeline.ingest
```

and:

```text
Scheduled cycle
    -> verify_due_sources
    -> scan(project)
    -> optional scan(intelligence)
    -> daily_center
```

`scan()` does not rediscover sources on every scan. This is consistent with the Manifest boundary that discovery creates candidates/provenance while acquisition operates against source-bound integrations. The Desktop global Search remains a local opportunity-set filter and is not required by the Manifest to become a live discovery trigger.

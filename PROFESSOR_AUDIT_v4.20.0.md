# Professor / Adversarial Audit — v4.20.0

## Verdict

**Architecture direction: PASS with material improvement required.**
The previous releases over-weighted source federation. v4.20 moves the product back toward the original outcome: opportunity selection, learning-level adaptation, application readiness, and lifecycle tracking.

## Baseline inspection

- Core Python modules: 42
- Core LOC: ~4.2K
- Desktop presentation module: ~1.0K LOC
- Largest functions after patch: CLI orchestration, pipeline ingest, source validation, runtime federation.
- Broad bare `except` handlers: 0 in core modules.
- Full tests: **PASS — 196 tests, 1 skip** at the v4.20 verification run.
- Compileall: **PASS**.
- Desktop UI smoke test under Xvfb: **PASS**.
- Product audit: **PASS, 0 errors**.
- Release audit: **PASS, 0 errors**.

## Judge findings

### P0 — Outcome imbalance

**Finding:** v4.18/v4.19 invested heavily in source discovery while the product's actual economic outcome was represented mainly by a simple score and manual submission plan.

**Correction:** introduced `opportunity_ranker.py`, learning profile, rank history, application queue and guided fast application path.

### P0 — Learning level was not an input to project selection

**Finding:** the product generated a tool recommendation, but did not materially constrain or prioritize projects according to the user's current learning level.

**Correction:** profile now supports:
- level 1–5
- tracks
- stretch mode
- maximum project complexity

Ranking now includes skill fit, difficulty fit and learning value.

### P0 — "Best project" ranking was too source-centric

**Finding:** `score()` was mostly quality/evidence/eligibility/payment/budget/time-to-money.

**Correction:** ranking now combines:
- evidence quality
- eligibility
- skill fit
- difficulty fit
- learning value
- freshness
- competition signal
- application speed
- budget
- Red/Blue Team track relevance

### P1 — Application path was not optimized for speed

**Finding:** the default connector was effectively manual and application queue did not exist.

**Correction:** `application_queue` ranks ready opportunities and `GuidedBrowserConnector` opens the fastest legitimate path with prepared material. It does not silently submit, bypass CAPTCHA/2FA, or evade site controls.

### P1 — Desktop overview was source-heavy

**Finding:** primary dashboard KPIs were Sources / Active / Execution Ready / Blocked.

**Correction:** primary dashboard is now opportunity-first:
- Best opportunities
- Application ready
- Opened today
- Submitted

Source posture remains visible as secondary intelligence.

### P1 — Windows validation was release-only

**Finding:** Windows workflow was primarily tied to tagged releases.

**Correction:** added Windows CI for PR/main plus optional SearXNG live-search smoke using a GitHub secret.

### P1 — Jurisdiction filter could become an identity/nationality filter

**Finding:** a request to block anything related to a country can easily become an unsupported inference about a person's nationality or identity.

**Correction:** MarketRadar only blocks explicit operational jurisdiction evidence: domain, registration, legal entity, hosting/IP, or location metadata. It does **not** infer or block by a person's nationality, ethnicity, religion, or a mere textual mention.

## Architecture review

```text
Presentation
    ↓
Runtime / Application orchestration
    ↓
Opportunity Intelligence ── Learning Profile ── Ranking
    ↓
Policy / Evidence Gate
    ↓
Application Queue / Approval
    ↓
Authorized Connector or Guided Browser
    ↓
Outcome / Revenue

Parallel intelligence plane:
Search Federation → Community Intelligence → Evidence Graph → Source Discovery → Source Verification
```

This is healthier than treating Source Discovery as the product itself.

## Red Team / Blue Team review

The product now classifies security opportunities into project tracks. It may recommend:
- Red Team / bug bounty / authorized testing work
- Blue Team / detection / monitoring / incident-response work

The system does **not** autonomously perform unauthorized exploitation, CAPTCHA bypass, KYC bypass, account creation, or unrestricted external offensive actions.

## Remaining material work

1. Browser form automation should become site-specific adapters rather than generic DOM guessing.
2. Opportunity parsers need richer deadline, proposal-count, client-reputation and acceptance-rate extraction where a source exposes those fields.
3. Search federation should eventually include provider health/cost/latency scoring.
4. Evidence Graph should evolve from simple signal edges into source → discussion → platform → policy → opportunity → outcome relationships.
5. CLI orchestration is still somewhat monolithic and should be split into command services in a later cleanup pass.
6. `product_audit.py` still reports static coverage-target warnings; the long-term metric should become discovery yield and verified opportunity yield rather than registry quotas.

## Live Internet verdict

**NOT PROVEN in this runtime.** The local runtime has no configured search provider. The software correctly records this as provider unavailability rather than fabricating discovery.

A Windows runtime with SearXNG or another permitted provider is required for the first real Internet-wide discovery measurement.

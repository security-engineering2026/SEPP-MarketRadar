# SEPP-MarketRadar v4.18.0 — Source Coverage

## Current registry

| Metric | Value |
|---|---:|
| Registered contracts | 679 |
| Active | 48 |
| Daily project scan | 15 |
| Global discovery | 83 |
| Needs analysis | 558 |
| Blocked for Iran | 11 |
| Bug bounty | 89 |
| Exact duplicate URLs | 0 |
| Execution ready | 0 |

## Verification truth

`DISCOVERED` means the source is a discovery candidate. It is not a live verification result.

The runtime verifier is now responsible for turning candidates into `LIVE_CONFIRMED`, `DEAD`, `LOW_QUALITY` or `STALE`, while extracting Iran, KYC, payout and payment evidence.

Explicit documented Iran restrictions are retained in `BLOCKED_IRAN` and cannot be used by the acquisition engine.

## Discovery is deliberately broader than execution

The platform maintains separate lanes:

- `DAILY_PROJECT_SCAN`
- `GLOBAL_DISCOVERY`
- `MARKET_INTELLIGENCE_ONLY`
- `NEEDS_ANALYSIS`
- `BLOCKED_IRAN`
- `REVIEW`

Unknown foreign sources remain discovery/research-only until the verifier finds evidence.

## Regional gap audit

The product audit checks country/region targets automatically. Current gaps include Russia, Türkiye, Qatar, Oman, Bahrain, China, Taiwan, Malaysia, Australia, New Zealand, Caucasus, Central Asia and the broader Africa/bug-bounty targets. These are tracked as discovery gaps rather than being hidden by the global source count.

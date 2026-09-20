# SEPP-MarketRadar — Goal vs Reality / v4.21.0

## Original product goal

MarketRadar was intended to behave less like a source catalog and more like an adaptive market-intelligence and execution system:

`Discover → Verify → Evidence → Eligibility → Opportunity Intelligence → Learning Fit → Rank → Prepare → Legitimate Application → Outcome → Learning → Revenue → Re-rank`

The success criterion is not the number of registered sources. It is whether the system can turn broad evidence-backed discovery into better, faster, safer and increasingly accurate actions.

## v4.21 comparison

| Capability | v4.21 state | Judge decision |
|---|---|---|
| Global discovery | Strong architecture; live yield provider-dependent | Keep improving provider federation, not registry inflation |
| Source verification | Strong | Maintain |
| Evidence/provenance | Strong | Maintain and extend cross-entity graph |
| Deadline extraction | Implemented locally with confidence | Improve site-specific parsers |
| Proposal-count extraction | Implemented locally with confidence | Improve structured/provider adapters |
| Client reputation | Implemented as evidence-weighted signals | Add source-specific reputation fields |
| Competition intelligence | Implemented | Add time-series proposal velocity |
| Acceptance probability | Implemented with smoothed source/category/global priors | Learn from larger real outcome history |
| Expected-value/revenue ranking | Implemented | Add verified currency normalization and realized margin |
| Learning adaptation | Strong baseline | Learn from completed outcomes and skill-gap history |
| Application adapters | Registry + safe generic fallback | Major next gap: authorized site-specific adapters |
| Browser recovery | Retry/backoff + immutable attempt audit | Add browser-session state when real browser runtime is available |
| Approval/audit | Strong | Maintain immutable evidence/approval binding |
| Outcome capture | Implemented | Add richer rejection/acceptance/negotiation reason taxonomy |
| Outcome learning | Implemented | Requires real production outcome volume to become predictive |
| Revenue feedback | Implemented | Add net revenue, fees, time-to-money and realized ROI |
| Windows product | Packaging pipeline present | Windows runner remains required for runtime proof |
| Android | Companion exists | Remains non-Core and environment-gated |

## Judge → Maker decision

### Upgraded in v4.21

1. Deadline extraction.
2. Proposal-count extraction.
3. Client reputation scoring.
4. Competition pressure.
5. Acceptance-probability learning.
6. Expected-value ranking.
7. Source-specific application adapter boundary.
8. Browser recovery and attempt audit.
9. Immutable outcome history.
10. Accepted/rejected reason learning.
11. Revenue-informed ranking.
12. 100-pass deterministic Judge→Maker audit.

### Remaining gaps that are real, not cosmetic

1. **Live site-specific application automation**: local adapter architecture exists, but each real site still needs an authorized, tested adapter and credentials/session handling.
2. **Outcome data volume**: prediction quality cannot be honestly claimed until real accepted/rejected/completed/paid outcomes accumulate.
3. **Proposal velocity**: a single proposal count is weaker than change-over-time competition.
4. **Client reputation depth**: source-specific fields such as verified spend, hire rate, repeat-client rate and dispute signals should be normalized where legally/publicly available.
5. **Revenue realism**: gross budget is not net revenue. Fees, refunds, taxes, payment friction and time-to-money need separate evidence-backed fields.
6. **Live provider routing**: search-provider health, latency, cost and yield should influence discovery routing.
7. **Windows runtime proof**: EXE/installer/signing/clean-machine execution requires the actual Windows environment.

These are now explicitly bounded engineering gaps rather than hidden deficiencies.

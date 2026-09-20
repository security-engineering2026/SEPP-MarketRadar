# SEPP-MarketRadar v6.2.0 — Goal → Code → Runtime Audit

## Classification
**Engineering release candidate. Not Windows-certified. Not economic-loop proven with live external providers.**

## Closed / hardened in this release
- Project contract/acceptance record: acceptance, start, deadline, agreed amount, payment due.
- Durable project milestones.
- Durable project communications ledger.
- Application tracking model: external reference, status URL, polling mode, last poll, next poll.
- Application status evidence: raw status, normalized state, confidence, evidence URL/text, digest, accepted transition.
- Payment verification attempts: separate from payment claim; PAID requires verified evidence.
- Final project report: lifecycle, stage durations, payment state, verification attempts, milestones, communications, follow-ups, deadline variance.
- Source concurrency constraints can be declared in source contracts instead of only hardcoded logic.
- Packaged worker mode: `MarketRadar.exe --operation-tick`.
- Packaged scheduled-cycle mode: `MarketRadar.exe --scheduled-cycle`.
- Windows installer registration: two daily market scans + 15-minute operations worker.

## Still runtime-dependent
- Live source verification and live Internet discovery.
- Live application status APIs for individual providers.
- External follow-up sending through authorized connectors.
- Real payment settlement verification through configured banking/crypto/provider adapters.
- Windows EXE build, installer execution, Scheduled Task execution and restart/recovery proof.
- Android APK build/deployment.

## Explicitly not claimed
- 679 sources are not 679 live sources.
- `execution_ready=0` is not presented as operational readiness.
- A recorded payment is not treated as deposited/settled until verification evidence exists.
- A scheduled follow-up is not claimed as a sent message.
- A source contract is not claimed as a live connector.
- Passing Linux tests is not claimed as Windows certification.

## Current automated proof
- pytest: **227 tests — 226 passed, 1 skipped**.
- 100-pass Judge→Maker audit: **PASS**.
- Product audit: **0 logical errors** (49 coverage warnings are retained as warnings).
- Release audit: **0 errors**.
- CLI worker smoke: `MarketRadar.pyw --operation-tick` returned successfully.

## Coverage warnings intentionally retained
Coverage gaps remain in several geographic targets plus the bug-bounty discovery target. These are coverage expansion items, not fabricated source-health claims.


## v6.2.0 critical integrity fixes
- Recording a payment claim no longer transitions an opportunity to `PAID`; settlement remains `DELIVERED` until verification.
- Application status polling can no longer transition directly to `PAID`; payment status is handled by the payment-verification path.
- Source-declared application concurrency limits are enforced in the approval/submission path.
- Authorized payment-status polling is available as a durable worker path; it still requires a configured provider endpoint and credential.
- Windows packaging now includes the scheduled-task installer script in the portable tree used by CI.

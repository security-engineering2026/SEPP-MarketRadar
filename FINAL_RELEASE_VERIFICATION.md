# SEPP-MarketRadar — Final Release 15.0.0

## Release meaning
This is the **final product baseline**: the feature set, data model, workflow controls, economic loop, desktop UI, source federation, discovery, evidence, policy, reliability controls, packaging path, CI gates, and recovery controls are frozen as one coherent release.

A final release does not manufacture facts that require an external environment. Live source health, third-party account authorization, external application acceptance, settlement, and Windows execution must be proven by the corresponding runtime evidence. The product therefore fails closed and records UNKNOWN where proof is absent.

## Final local proof
- Full pytest suite passes in the development environment.
- Final economic lifecycle test: DISCOVERED → ELIGIBILITY → APPROVAL → SUBMITTED → MESSAGE_RECEIVED → NEGOTIATION → ACCEPTED → IN_PROGRESS → DELIVERED → verified payment → PAID.
- Payment claim alone cannot produce PAID.
- Application tracking evidence cannot produce PAID.
- Payment verification is a separate authority path.
- SQLite backup/restore round-trip is tested.
- Source application concurrency limits are enforced before submission.
- Deadline, follow-up, application-status and payment-operation workers are durable and callable without the GUI.
- Windows CI contains EXE build, portable smoke, installer install/uninstall, UI smoke and scheduled-task checks.

## Windows release gate
The source release is final, but the **Windows artifact is not certified until Windows CI has executed the actual EXE and installer**. This distinction is intentional: production-readiness requires evidence from the actual production artifact/environment, not merely source-level or Linux test evidence. citeturn0search0turn0search2

## No false claims
- Source registry count ≠ live verified source count.
- Candidate/discovered ≠ execution-ready.
- Scheduled follow-up ≠ sent follow-up.
- Payment claim ≠ deposited/settled payment.
- Passing Linux tests ≠ Windows certification.
- Android source/build presence ≠ deployed Android companion.

## Go/No-Go rule
A Windows distribution may be promoted only when the Windows release workflow has green evidence for: EXE build, EXE smoke, GUI smoke, installer install, installed-app smoke, uninstall, scheduled-task registration/execution, restart/data persistence, and the final economic lifecycle. This follows the principle that a release gate must be evidence-backed and include recovery/operational readiness, not merely unit-test success. citeturn0search1turn0search12

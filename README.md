# SEPP-MarketRadar v16.1.1

# SEPP-MarketRadar 15.0.0

**Final Product Baseline — Windows-first Market Intelligence & Economic Operations Platform**

MarketRadar is built around:

`Market → Evidence → Intelligence → Decision → Action → Revenue → Learning`

It is not a single job scraper. It federates market sources, discovers additional sources, normalizes observations into canonical opportunities, preserves evidence, separates eligibility/policy/payment/KYC decisions, resolves identities and parties, ranks opportunities, controls application actions, tracks project execution, records payment evidence, and feeds outcomes back into market/product/pricing intelligence.

## Final release controls
- fail-closed evidence and policy gates
- immutable/auditable operational records
- human approval for consequential actions
- source-health states that never pretend UNKNOWN is healthy
- application concurrency constraints
- durable operations worker
- payment verification authority separate from payment claims
- backup/restore verification
- Windows EXE + installer CI gates

## Run local final verification

```text
py -m marketradar.cli final-verify
```

On the packaged Windows application:

```text
MarketRadar.exe --final-verify
```

## Windows distribution
The repository contains the PyInstaller spec, portable build script, Inno Setup installer definition, scheduled-task registration and Windows CI release workflow. The actual Windows artifact must be generated and tested on Windows; a Linux build cannot truthfully certify Windows execution.

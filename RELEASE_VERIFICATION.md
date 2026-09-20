# Release Verification — v4.14.0

## Source/archive
- Fresh source tree audit: PASS
- Operational registry contains only onboarded records: PASS
- Strategic source target remains >=500: PASS
- Current onboarded records: 23 (18 active + 4 authorized candidates + 1 disabled local test): PASS
- No placeholder `example.com` operational records: PASS
- Source contract audit: PASS

## Automated verification
- Python compileall: PASS
- pytest: PASS
- Release security/static audit: PASS (run on a clean release tree before test-generated caches are created)
- CLI status: PASS
- Source audit: PASS
- Desktop smoke test: PASS

## Final audit
- State-machine DB invariants: PASS
- Revenue lifecycle/cardinality: PASS
- Acquisition provenance boundary: PASS
- Architecture responsibility review: PASS
- 139-test suite: PASS under Xvfb

## Reliability/security
- Host allow-list: PASS
- Public/private IP boundary: PASS
- Redirect boundary: PASS
- URL length bound: PASS
- Response size bound: PASS
- Transient-only retry policy: PASS
- Adapter/content-type contract: PASS (including RSS and Atom parser paths)
- Raw observation immutability: PASS
- Persistent approval replay protection: PASS
- Transactional submission/revenue operations: PASS
- Non-active sources excluded from default verification: PASS
- Health history and failure tracking: PASS

## Windows
- PyInstaller source configuration: READY
- Portable EXE smoke-test gate: READY
- Installer smoke-test gate: READY
- Actual Windows execution: NOT CLAIMED in this environment

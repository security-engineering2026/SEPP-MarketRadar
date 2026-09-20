# SEPP-MarketRadar 16.1.1 — Consolidated Candidate

This archive consolidates the source state that produced the GitHub Windows CI PASS on run `35453669137` and includes the subsequent Windows Release workflow hardening prepared for manual validation.

## Included CI fixes
- Windows SQLite resource cleanup in jury tests.
- Desktop logging shutdown import fix.
- Required PyInstaller spec included in `packaging/marketradar.spec`.
- Windows CI cleanup removes generated test artifacts before release audit.

## Included release hardening
- Python 3.12 pinned in Windows Release workflow.
- `checkout@v7` and `setup-python@v7`.
- Manual dispatch is validation-only and does not publish a GitHub Release.
- Tag/version validation runs only for `v*` tag pushes.
- Authenticode enforcement is controlled explicitly through `REQUIRE_AUTHENTICODE_SIGNING`.
- Windows builder uses `python -m PyInstaller` rather than the Windows `py` launcher.

This archive is a consolidated candidate, not a claim that the Windows Release workflow itself has already passed end-to-end.


## Windows Release Validation follow-up

- Corrected the repository-integrity test to validate the actual PyInstaller spec root resolution: `SPECPATH/parent` (the spec is under `packaging/` and the desktop entry point is under `desktop/`).
- This follows GitHub Windows Release validation run `35455069574`, where the full Windows test suite reached one remaining stale integrity assertion before the EXE build stage.


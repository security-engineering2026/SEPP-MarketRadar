# Windows Locking Hotfix — 16.1.1

## Defect
Windows returned `WinError 32` while cleaning temporary test/runtime directories because `marketradar.log` remained open in a `RotatingFileHandler`.

## Fix
- `marketradar.logging_setup.configure_logging()` now detects data-root changes and closes stale file handlers.
- `close_logging()` releases all MarketRadar log handlers.
- Desktop/application close paths call `close_logging()`.
- A regression test verifies that a temporary data root can be removed after logging use.

## Verification
- 264 tests collected
- 263 PASS
- 1 SKIPPED (Tk display unavailable in the local non-GUI environment)
- compileall PASS
- Release audit PASS (errors=0)
- Product audit PASS (errors=0)
- Architecture audit PASS

Windows native EXE/Installer E2E remains a separate host-level gate and is not claimed by these local results.

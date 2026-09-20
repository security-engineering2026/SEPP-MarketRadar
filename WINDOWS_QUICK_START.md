# Windows Quick Start — SEPP-MarketRadar 16.0.0

1. Run `PowerShell -ExecutionPolicy Bypass -File .\packaging\windows_preflight.ps1`.
2. Run `PowerShell -ExecutionPolicy Bypass -File .\packaging\prepare_windows.ps1 -ArchivePath <ZIP>`.
3. Only after local tests pass, run the Windows build/release script.
4. The scheduler contract is: execution radar hourly; market intelligence 08:00 and 20:00; operations every 15 minutes.

The preparation script uses the `py -3` launcher, not a bare `python` command, based on Windows execution findings from the previous release cycle.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$portable = Join-Path $root "release\portable\MarketRadar"
if (-not (Test-Path $portable)) { throw "Portable release not found: $portable" }
# Restrict shipped configuration to administrators and the current user.
& icacls $portable /inheritance:r | Out-Null
& icacls $portable /grant:r "$env:USERNAME:(OI)(CI)F" "Administrators:(OI)(CI)F" "SYSTEM:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "ACL hardening failed" }
Write-Host "Windows ACL hardening applied to $portable"

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$version = (python -c "from marketradar import __version__; print(__version__)").Trim()
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

$distRoot = Join-Path $repoRoot "dist"
$buildRoot = Join-Path $repoRoot "build"
$releaseRoot = Join-Path $repoRoot "release"
$distExe = Join-Path $distRoot "MarketRadar.exe"
$portableRoot = Join-Path $releaseRoot "portable\MarketRadar"

if (Test-Path $distRoot) { Remove-Item $distRoot -Recurse -Force }
if (Test-Path $buildRoot) { Remove-Item $buildRoot -Recurse -Force }
if (Test-Path $releaseRoot) { Remove-Item $releaseRoot -Recurse -Force }

python -m PyInstaller (Join-Path $PSScriptRoot "marketradar.spec") --clean --noconfirm
if (-not (Test-Path $distExe)) { throw "PyInstaller did not create MarketRadar.exe at $distExe" }

New-Item -ItemType Directory -Force -Path $portableRoot | Out-Null
Copy-Item $distExe (Join-Path $portableRoot "MarketRadar.exe") -Force
Copy-Item (Join-Path $repoRoot "config") (Join-Path $portableRoot "config") -Recurse -Force

$portablePackaging = Join-Path $portableRoot "packaging"
New-Item -ItemType Directory -Force -Path $portablePackaging | Out-Null
Copy-Item (Join-Path $PSScriptRoot "install_scheduled_scan.ps1") (Join-Path $portablePackaging "install_scheduled_scan.ps1") -Force

$smokeRoot = Join-Path $env:RUNNER_TEMP "SEPP-MarketRadar-Smoke-$version"
if (Test-Path $smokeRoot) { Remove-Item $smokeRoot -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Force -Path $smokeRoot | Out-Null
Copy-Item $portableRoot $smokeRoot -Recurse -Force
New-Item -ItemType File -Force -Path (Join-Path $smokeRoot ".portable") | Out-Null

function Remove-SmokeRootWithRetry([string]$Path) {
  for ($i = 1; $i -le 10; $i++) {
    try {
      if (-not (Test-Path $Path)) { return $true }
      Remove-Item $Path -Recurse -Force -ErrorAction Stop
      return $true
    } catch {
      Start-Sleep -Milliseconds 500
    }
  }
  return $false
}

try {
  $smokeExe = Join-Path $smokeRoot "MarketRadar.exe"
  & $smokeExe --smoke-test
  if ($LASTEXITCODE -ne 0) { throw "Portable EXE smoke test failed: $LASTEXITCODE" }
  & $smokeExe --ui-smoke-test
  if ($LASTEXITCODE -ne 0) { throw "Portable EXE UI smoke test failed: $LASTEXITCODE" }
  Get-Process -Name "MarketRadar" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 500
} finally {
  if (-not (Remove-SmokeRootWithRetry $smokeRoot)) {
    Write-Warning "Smoke root could not be removed immediately; runner temp is ephemeral."
  }
}

if (Test-Path (Join-Path $portableRoot "data")) { throw "Portable artifact contains runtime data" }
if (Test-Path (Join-Path $portableRoot "logs")) { throw "Portable artifact contains runtime logs" }
New-Item -ItemType File -Force -Path (Join-Path $portableRoot ".portable") | Out-Null

Write-Host "Portable build v$version created at $portableRoot"

$ErrorActionPreference = "Stop"
$version = (python -c "from marketradar import __version__; print(__version__)").Trim()
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path release) { Remove-Item release -Recurse -Force }
python -m PyInstaller packaging/marketradar.spec --clean --noconfirm
if (-not (Test-Path (Join-Path "dist" "MarketRadar.exe"))) { throw "PyInstaller did not create MarketRadar.exe" }

$portableRoot = Join-Path "release" "portable"
$portableApp = Join-Path $portableRoot "MarketRadar"
New-Item -ItemType Directory -Force -Path $portableApp | Out-Null
Copy-Item (Join-Path "dist" "MarketRadar.exe") (Join-Path $portableApp "MarketRadar.exe") -Force
Copy-Item "config" (Join-Path $portableApp "config") -Recurse -Force
$portablePackaging = Join-Path $portableApp "packaging"
New-Item -ItemType Directory -Force -Path $portablePackaging | Out-Null
Copy-Item (Join-Path "packaging" "install_scheduled_scan.ps1") (Join-Path $portablePackaging "install_scheduled_scan.ps1") -Force

$smokeRoot = Join-Path $env:RUNNER_TEMP "SEPP-MarketRadar-Smoke-$version"
if (Test-Path $smokeRoot) { Remove-Item $smokeRoot -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Force -Path $smokeRoot | Out-Null
Copy-Item $portableApp (Join-Path $smokeRoot "MarketRadar") -Recurse -Force
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
  $smokeExe = Join-Path $smokeRoot "MarketRadar\MarketRadar.exe"
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

if (Test-Path (Join-Path $portableApp "data")) { throw "Portable artifact contains runtime data" }
if (Test-Path (Join-Path $portableApp "logs")) { throw "Portable artifact contains runtime logs" }
New-Item -ItemType File -Force -Path (Join-Path $portableRoot "MarketRadar.portable") | Out-Null
Write-Host "Portable build v$version created at $portableApp"

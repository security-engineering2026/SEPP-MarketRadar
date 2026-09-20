$ErrorActionPreference = "Stop"
$version = (python -c "from marketradar import __version__; print(__version__)").Trim()
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path release) { Remove-Item release -Recurse -Force }
python -m PyInstaller packaging/marketradar.spec --clean --noconfirm
if (-not (Test-Path dist\MarketRadar.exe)) { throw "PyInstaller did not create MarketRadar.exe" }
New-Item -ItemType Directory -Force -Path release\portable\MarketRadar | Out-Null
Copy-Item dist\MarketRadar.exe release\portable\MarketRadar\MarketRadar.exe -Force
Copy-Item config release\portable\MarketRadar\config -Recurse -Force
New-Item -ItemType Directory -Force -Path release\portable\MarketRadar\packaging | Out-Null
Copy-Item packaging\install_scheduled_scan.ps1 release\portable\MarketRadar\packaging\install_scheduled_scan.ps1 -Force

# Smoke-test a disposable portable copy so the release artifact stays free of runtime DB/log files.
$smokeRoot = Join-Path $env:RUNNER_TEMP "SEPP-MarketRadar-Smoke-$version"
if (Test-Path $smokeRoot) { Remove-Item $smokeRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $smokeRoot | Out-Null
Copy-Item release\portable\MarketRadar\* $smokeRoot -Recurse -Force
New-Item -ItemType File -Force -Path (Join-Path $smokeRoot '.portable') | Out-Null
try {
  & (Join-Path $smokeRoot 'MarketRadar.exe') --smoke-test
  if ($LASTEXITCODE -ne 0) { throw "Portable EXE smoke test failed: $LASTEXITCODE" }
  & (Join-Path $smokeRoot 'MarketRadar.exe') --ui-smoke-test
  if ($LASTEXITCODE -ne 0) { throw "Portable EXE UI smoke test failed: $LASTEXITCODE" }
} finally {
  if (Test-Path $smokeRoot) { Remove-Item $smokeRoot -Recurse -Force }
}

# The shipped portable tree must contain no runtime-generated state.
if (Test-Path release\portable\MarketRadar\data) { throw "Portable artifact contains runtime data" }
if (Test-Path release\portable\MarketRadar\logs) { throw "Portable artifact contains runtime logs" }
New-Item -ItemType File -Force -Path release\portable\MarketRadar\.portable | Out-Null
Write-Host "Portable build v$version created at release\portable\MarketRadar"

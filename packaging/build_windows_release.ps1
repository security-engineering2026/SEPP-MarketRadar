$ErrorActionPreference = "Stop"
$version = (py -c "from marketradar import __version__; print(__version__)").Trim()
if (-not $version) { throw "Could not read application version" }
Write-Host "Building SEPP-MarketRadar v$version"


py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt pyinstaller
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path release) { Remove-Item release -Recurse -Force }
py -3 -m PyInstaller packaging/marketradar.spec --clean --noconfirm
if (-not (Test-Path dist\MarketRadar.exe)) { throw "PyInstaller did not create MarketRadar.exe" }

New-Item -ItemType Directory -Force -Path release\portable\MarketRadar | Out-Null
Copy-Item dist\MarketRadar.exe release\portable\MarketRadar\MarketRadar.exe -Force
Copy-Item config release\portable\MarketRadar\config -Recurse -Force
New-Item -ItemType Directory -Force -Path release\portable\MarketRadar\packaging | Out-Null
Copy-Item packaging\install_scheduled_scan.ps1 release\portable\MarketRadar\packaging\install_scheduled_scan.ps1 -Force
New-Item -ItemType File -Force -Path release\portable\MarketRadar\.portable | Out-Null

$smokeRoot = Join-Path $env:RUNNER_TEMP "SEPP-MarketRadar-Smoke-$version"
if (Test-Path $smokeRoot) { Remove-Item $smokeRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $smokeRoot | Out-Null
Copy-Item release\portable\MarketRadar\* $smokeRoot -Recurse -Force
try {
  & (Join-Path $smokeRoot 'MarketRadar.exe') --smoke-test
  if ($LASTEXITCODE -ne 0) { throw "Portable EXE smoke test failed: $LASTEXITCODE" }
  & (Join-Path $smokeRoot 'MarketRadar.exe') --ui-smoke-test
  if ($LASTEXITCODE -ne 0) { throw "Portable EXE UI smoke test failed: $LASTEXITCODE" }
} finally {
  if (Test-Path $smokeRoot) { Remove-Item $smokeRoot -Recurse -Force }
}

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) { throw "Inno Setup compiler (iscc.exe) is required for a complete Windows release" }
& $iscc.Source "/DMyAppVersion=$version" "packaging/installer.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed: $LASTEXITCODE" }
$installer = "release\installer\SEPP-MarketRadar-Setup-$version.exe"
if (-not (Test-Path $installer)) { throw "Installer artifact missing: $installer" }
Write-Host "Windows portable EXE: release\portable\MarketRadar\MarketRadar.exe"
Write-Host "Windows installer: $installer"

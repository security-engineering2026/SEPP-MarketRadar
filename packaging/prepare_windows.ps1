param([Parameter(Mandatory=$true)][string]$ArchivePath,[string]$Destination="$env:TEMP\SEPP-MarketRadar")
$ErrorActionPreference="Stop"
if (!(Test-Path $ArchivePath)) { throw "Archive not found: $ArchivePath" }
if (Test-Path $Destination) { Remove-Item $Destination -Recurse -Force }
New-Item -ItemType Directory -Path $Destination | Out-Null
$extract = Join-Path $Destination 'extract'
Expand-Archive -LiteralPath $ArchivePath -DestinationPath $extract -Force
$project = Get-ChildItem $extract -Directory | Select-Object -First 1
if (-not $project) { $project = Get-Item $extract }
while ((Test-Path (Join-Path $project.FullName 'marketradar')) -eq $false) {
  $child = Get-ChildItem $project.FullName -Directory | Select-Object -First 1
  if (-not $child) { break }
  $project=$child
}
if (!(Test-Path (Join-Path $project.FullName 'marketradar'))) { throw 'MARKETRADAR_PACKAGE_ROOT_NOT_FOUND' }
& (Join-Path $PSScriptRoot 'windows_preflight.ps1')
Push-Location $project.FullName
try {
  & py -3 -m venv .venv
  & .\.venv\Scripts\python.exe -m pip install --upgrade pip
  & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  & .\.venv\Scripts\python.exe -m compileall -q marketradar tests
  & .\.venv\Scripts\python.exe -m pytest -q
} finally { Pop-Location }
Write-Host "Prepared and locally tested: $($project.FullName)"

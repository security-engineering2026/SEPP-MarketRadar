$ErrorActionPreference = 'Stop'
$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = 'C:\Users\Lotus Store\Downloads\SEPP-MarketRadar-16.1.1-CI\SEPP-MarketRadar-16.1.1-FINAL'

if (-not (Test-Path (Join-Path $target '.git'))) { throw "Target repository not found: $target" }
Set-Location $target

$remote = (git remote get-url origin).Trim()
if ($remote -notmatch 'github\.com/security-engineering2026/SEPP-MarketRadar(?:\.git)?$') {
    throw "Unexpected origin remote: $remote"
}
$head = (git rev-parse --short HEAD).Trim()
if ($head -ne '92e8881') {
    throw "Expected existing repository HEAD 92e8881 before consolidation, found $head. Abort without changes."
}

Write-Host "Syncing complete consolidated candidate into existing Git repository..."
$excludeDirs = @('.git')
$helperFiles = @(
    'APPLY_WINDOWS_HOTFIX.ps1',
    'README_WINDOWS_HOTFIX.txt',
    'APPLY_WINDOWS_CI_CLEANUP_HOTFIX.ps1',
    'README_WINDOWS_CI_CLEANUP_HOTFIX.txt',
    'APPLY_WINDOWS_RELEASE_HOTFIX.ps1',
    'README_WINDOWS_RELEASE_HOTFIX.txt'
)

# Copy the complete candidate tree without touching repository metadata.
robocopy $source $target /E /XD .git /XF $($helperFiles -join ' ') /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -gt 7) { throw "robocopy failed with exit code $LASTEXITCODE" }

foreach ($file in $helperFiles) {
    $p = Join-Path $target $file
    if (Test-Path $p) { Remove-Item $p -Force }
}

Write-Host 'Validating working tree...'
git diff --check

git add -A
git diff --cached --check

$status = git status --short
if (-not $status) { throw 'No changes detected after consolidation.' }
git status --short

git diff --cached --stat

git commit -m 'Align Windows release integrity test with spec root resolution'
git push origin main

Write-Host 'Consolidated source pushed. Dispatching Windows Release validation...'
$dispatchOutput = gh workflow run windows-release.yml --repo security-engineering2026/SEPP-MarketRadar --ref main 2>&1
if ($LASTEXITCODE -ne 0) { throw "GitHub workflow_dispatch failed: $dispatchOutput" }
Start-Sleep -Seconds 5

$head = (git rev-parse HEAD).Trim()
$runs = (gh run list --repo security-engineering2026/SEPP-MarketRadar --workflow windows-release.yml --branch main --event workflow_dispatch --limit 10 --json databaseId,headSha,status,conclusion,url | ConvertFrom-Json)
$run = $runs | Where-Object { $_.headSha -eq $head } | Select-Object -First 1
if (-not $run) { throw "Could not locate Windows Release validation run for $head" }

Write-Host "Release validation run $($run.databaseId): $($run.url)"
gh run watch $run.databaseId --repo security-engineering2026/SEPP-MarketRadar --exit-status
if ($LASTEXITCODE -ne 0) {
    gh run view $run.databaseId --repo security-engineering2026/SEPP-MarketRadar --log-failed
    throw 'Windows Release validation failed.'
}

Write-Host 'WINDOWS RELEASE VALIDATION PASS'
Write-Host 'Manual validation completed; no GitHub Release was published.'



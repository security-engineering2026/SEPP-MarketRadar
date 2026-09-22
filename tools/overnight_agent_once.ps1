# SEPP-MarketRadar autonomous execution: one bounded cycle.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,
    [Parameter(Mandatory = $true)]
    [string]$AgentRunner,
    [int]$MaxMinutes = 8
)
$ErrorActionPreference = "Stop"
$TaskRoot = Join-Path $RepoPath ".agent"
$LogDir = Join-Path $TaskRoot "logs"
$LockDir = Join-Path $TaskRoot "run.lock"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log = Join-Path $LogDir "$stamp.log"
function Log([string]$Message) {
    "$(Get-Date -Format o) $Message" | Tee-Object -FilePath $log -Append
}
if (-not (Test-Path (Join-Path $RepoPath ".git"))) { Log "ABORT: invalid git worktree"; exit 2 }
try { New-Item -ItemType Directory -Path $LockDir -ErrorAction Stop | Out-Null }
catch { Log "SKIP: another autonomous cycle is already running."; exit 0 }
try {
    Set-Location $RepoPath
    Log "AUDIT: syncing main."
    git fetch origin main 2>&1 | Tee-Object -FilePath $log -Append
    if ((git status --porcelain).Trim()) { Log "ABORT: dirty worktree"; exit 3 }
    git merge --ff-only origin/main 2>&1 | Tee-Object -FilePath $log -Append
    $headBefore = (git rev-parse HEAD).Trim()
    $prompt = @"
You are the autonomous SEPP-MarketRadar execution engineer.
Repository: security-engineering2026/SEPP-MarketRadar
Branch: main
Cycle budget: $MaxMinutes minutes.

Read first: docs/MANIFEST.md, docs/MANIFEST_ASIS_AUDIT.md, docs/DEBUG_HANDOFF.md, and latest GitHub Actions evidence.

MISSION: Audit -> Implement -> Test -> Fix -> Commit -> Continue.

RULES:
- Do not redesign or weaken the Manifest.
- No PASS/100%/production/readiness claims without real evidence.
- OPEN is not PASS.
- Prefer the first concrete reproducible CI/runtime failure over adding features.
- Patch the smallest coherent fix and add/update regression coverage.
- Run relevant tests before committing.
- Keep Windows qualification and Android E2E evidence real.
- Never modify secrets, credentials, tokens, or security controls to make a test pass.
- Never force-push or rewrite history.
- Do not touch unrelated files.
- Update DEBUG_HANDOFF.md only for a meaningful checkpoint.
- Commit all logical changes to main. DO NOT push; the controller pushes.
- If there is no safe concrete change, leave the tree unchanged.

Execute one highest-value engineering cycle within the time budget.
"@
    $promptPath = Join-Path $TaskRoot "current_prompt.txt"
    Set-Content -Path $promptPath -Value $prompt -Encoding UTF8
    Log "IMPLEMENT: invoking configured agent runner."
    $job = Start-Job -ScriptBlock {
        param($Runner, $PromptFile)
        & $Runner $PromptFile 2>&1
        exit $LASTEXITCODE
    } -ArgumentList $AgentRunner, $promptPath
    $completed = Wait-Job -Job $job -Timeout ($MaxMinutes * 60)
    if (-not $completed) {
        Stop-Job -Job $job -ErrorAction SilentlyContinue
        Log "ABORT: agent exceeded cycle budget."
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
        exit 4
    }
    Receive-Job -Job $job 2>&1 | Tee-Object -FilePath $log -Append
    Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
    $headAfter = (git rev-parse HEAD).Trim()
    if ((git status --porcelain).Trim()) { Log "ABORT: agent left uncommitted changes"; exit 5 }
    if ($headAfter -ne $headBefore) {
        Log "COMMIT: $headBefore -> $headAfter"
        git push origin main 2>&1 | Tee-Object -FilePath $log -Append
        if ($LASTEXITCODE -ne 0) { Log "FAIL: push failed"; exit 6 }
        Log "PUSH: main updated successfully."
    } else {
        Log "NO-CHANGE: no committed repository change."
    }
}
catch { Log "ERROR: $($_.Exception.Message)"; exit 10 }
finally { Remove-Item -LiteralPath $LockDir -Recurse -Force -ErrorAction SilentlyContinue }

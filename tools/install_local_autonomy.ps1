[CmdletBinding()]
param([string]$RepoPath = (Get-Location).Path,
      [string]$TaskName = "SEPP-MarketRadar-Local-Autonomous-Agent",
      [int]$IntervalMinutes = 10)
$ErrorActionPreference = "Stop"
if (-not (Test-Path (Join-Path $RepoPath ".git"))) { throw "RepoPath is not a Git repository: $RepoPath" }
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { throw "Ollama was not found on PATH." }
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python launcher 'py' was not found on PATH." }
$script = Join-Path $RepoPath "tools\run_local_autonomous_cycle.ps1"
if (-not (Test-Path $script)) { throw "Missing runner: $script" }
$argument = '-NoProfile -ExecutionPolicy Bypass -File "' + $script + '" -RepoPath "' + $RepoPath + '"'
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
$trigger.RepetitionInterval = New-TimeSpan -Minutes $IntervalMinutes
$trigger.RepetitionDuration = New-TimeSpan -Days 3650
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 9)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "Installed $TaskName every $IntervalMinutes minutes."

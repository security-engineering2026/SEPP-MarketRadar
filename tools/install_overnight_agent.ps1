# Install the SEPP-MarketRadar autonomous Windows task.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,
    [Parameter(Mandatory = $true)]
    [string]$AgentRunner,
    [string]$TaskName = "SEPP-MarketRadar-Autonomous-Agent"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path (Join-Path $RepoPath ".git"))) { throw "RepoPath is not a git worktree: $RepoPath" }
if (-not (Test-Path $AgentRunner)) { throw "AgentRunner does not exist: $AgentRunner" }
$once = Join-Path $RepoPath "tools\overnight_agent_once.ps1"
if (-not (Test-Path $once)) { throw "Missing controller: $once" }
$ps = (Get-Command powershell.exe -ErrorAction Stop).Source
$q = [char]34
$arguments = "-NoProfile -ExecutionPolicy Bypass -File " + $q + $once + $q + " -RepoPath " + $q + $RepoPath + $q + " -AgentRunner " + $q + $AgentRunner + $q
$action = New-ScheduledTaskAction -Execute $ps -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1))
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 9)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
$task = Get-ScheduledTask -TaskName $TaskName
$task.Triggers[0].Repetition.Interval = "PT10M"
$task.Triggers[0].Repetition.StopAtDurationEnd = $false
$task.Triggers[0].Repetition.Duration = "P1D"
Set-ScheduledTask -TaskName $TaskName -Trigger $task.Triggers[0] | Out-Null
Write-Host "Installed: $TaskName"
Write-Host "Repo: $RepoPath"
Write-Host "Agent runner: $AgentRunner"
Write-Host "Cadence: every 10 minutes while Windows is running."

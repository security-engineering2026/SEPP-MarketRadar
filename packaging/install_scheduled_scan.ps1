$ErrorActionPreference = "Stop"
$AppDir = Split-Path -Parent $PSScriptRoot
$Exe = Join-Path $AppDir "MarketRadar.exe"
if (-not (Test-Path $Exe)) { throw "MarketRadar.exe not found: $Exe" }

$ExecutionTask = "SEPP-MarketRadar-ExecutionRadar"
$ExecutionAction = New-ScheduledTaskAction -Execute $Exe -Argument "--scan project" -WorkingDirectory $AppDir
$ExecutionTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName $ExecutionTask -Action $ExecutionAction -Trigger $ExecutionTrigger -Description "Hourly evidence-gated execution opportunity scan" -Force | Out-Null

$IntelligenceTaskBase = "SEPP-MarketRadar-MarketIntelligence"
$IntelligenceTriggers = @(
    New-ScheduledTaskTrigger -Daily -At 08:00,
    New-ScheduledTaskTrigger -Daily -At 20:00
)
$IntelligenceAction = New-ScheduledTaskAction -Execute $Exe -Argument "--scan intelligence" -WorkingDirectory $AppDir
foreach ($i in 0..($IntelligenceTriggers.Count-1)) {
    Register-ScheduledTask -TaskName "$IntelligenceTaskBase-$($i+1)" -Action $IntelligenceAction -Trigger $IntelligenceTriggers[$i] -Description "Twice-daily market intelligence and product-demand scan" -Force | Out-Null
}

$OpsTask = "SEPP-MarketRadar-Operations"
$OpsAction = New-ScheduledTaskAction -Execute $Exe -Argument "--operation-tick" -WorkingDirectory $AppDir
$OpsTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName $OpsTask -Action $OpsAction -Trigger $OpsTrigger -Description "Deadline, follow-up, application-status and payment-operation checks" -Force | Out-Null

Write-Host "Installed: hourly execution radar, two daily market-intelligence scans, and a 15-minute operations worker."

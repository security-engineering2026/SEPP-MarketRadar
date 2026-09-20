$ErrorActionPreference = "Stop"
$checks = New-Object System.Collections.Generic.List[object]
function Check($Name,$Ok,$Detail) { $checks.Add([pscustomobject]@{check=$Name;status=($(if($Ok){'PASS'}else{'OPEN'}));detail=$Detail}) }
$py = Get-Command py -ErrorAction SilentlyContinue
Check "PythonLauncher" ($null -ne $py) ($(if($py){$py.Source}else{'py launcher not found'}))
if ($py) {
  try { $v = (& py -3 --version 2>&1 | Out-String).Trim(); Check "Python3" ($LASTEXITCODE -eq 0) $v } catch { Check "Python3" $false $_.Exception.Message }
  try { & py -3 -c "import tkinter" 2>$null; Check "Tkinter" ($LASTEXITCODE -eq 0) "Tkinter import" } catch { Check "Tkinter" $false $_.Exception.Message }
  try { & py -3 -m venv --help 2>$null; Check "Venv" ($LASTEXITCODE -eq 0) "venv module" } catch { Check "Venv" $false $_.Exception.Message }
}
Check "PowerShell" ($PSVersionTable.PSVersion.Major -ge 5) ($PSVersionTable.PSVersion.ToString())
Check "WritableTemp" (Test-Path $env:TEMP) $env:TEMP
$checks | Format-Table -AutoSize
if (($checks | Where-Object status -eq 'OPEN').Count -gt 0) { exit 2 }

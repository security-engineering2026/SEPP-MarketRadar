[CmdletBinding()]
param([string]$RepoPath = (Get-Location).Path)
$ErrorActionPreference = "Stop"
Set-Location $RepoPath
$ollama = Get-Command ollama -ErrorAction Stop
$null = & $ollama.Source list
if ($LASTEXITCODE -ne 0) { throw "Ollama is not responding. Start Ollama first." }
$model = if ($env:AUTONOMOUS_MODEL) { $env:AUTONOMOUS_MODEL } else { "qwen2.5-coder:7b" }
$list = & $ollama.Source list 2>&1
if (-not ($list -match [regex]::Escape($model))) { throw "Required local model '$model' is not installed. Run: ollama pull $model" }
$env:AUTONOMOUS_MODEL = $model
$env:AUTONOMOUS_TEST_COMMAND = "py -m pytest -q"
$env:AUTONOMOUS_TEST_TIMEOUT = "600"
& py (Join-Path $RepoPath "tools\autonomous_coding_agent.py")
$agentExit = $LASTEXITCODE
if ($agentExit -eq 0) { git push origin main; exit $LASTEXITCODE }
if ($agentExit -eq 20) {
  $env:AUTONOMOUS_CYCLE = "local-$([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))"
  & py (Join-Path $RepoPath "tools\autonomous_supervisor.py")
  $supervisorExit = $LASTEXITCODE
  if ((git rev-list --count origin/main..HEAD) -gt 0) { git push origin main }
  exit $supervisorExit
}
exit $agentExit

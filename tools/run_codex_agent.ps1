# Default Codex runner for the overnight controller.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PromptFile
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PromptFile)) {
    throw "Prompt file not found: $PromptFile"
}

if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw "codex CLI was not found on PATH."
}

$prompt = Get-Content -Path $PromptFile -Raw
$prompt | codex exec --ephemeral --sandbox workspace-write -
exit $LASTEXITCODE

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

$codexCommand = Get-Command codex -ErrorAction SilentlyContinue

if ($codexCommand) {
    $codexExe = $codexCommand.Source
}
else {
    $wingetRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    $codexExe = Get-ChildItem $wingetRoot -Recurse -File -Filter "codex-x86_64-pc-windows-msvc.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName

    if (-not $codexExe) {
        throw "Codex CLI was not found on PATH or in the WinGet package directory."
    }
}

$prompt = Get-Content -Path $PromptFile -Raw
$prompt | & $codexExe exec --ephemeral --sandbox workspace-write -
exit $LASTEXITCODE

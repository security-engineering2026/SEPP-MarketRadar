# Overnight Autonomous Execution

This repository contains a Windows-side controller for bounded autonomous engineering cycles:

AUDIT -> IMPLEMENT -> TEST -> FIX -> COMMIT -> PUSH -> next cycle

The controller is not the coding model. It invokes a locally configured agent runner, so the model/provider can be changed without changing the repository protocol.

## Safety boundaries

- main remains the source of truth.
- Dirty worktrees are refused.
- The agent must inspect MANIFEST.md, MANIFEST_ASIS_AUDIT.md, and DEBUG_HANDOFF.md.
- The agent must test before committing.
- The controller never auto-commits uncommitted work.
- The controller never force-pushes.
- Only committed changes are pushed.
- Concurrent scheduled runs are ignored.
- Each cycle is time-bounded.
- No secrets are stored in the repository.

## Windows installation

Prerequisites:

1. A clone of security-engineering2026/SEPP-MarketRadar.
2. Git authentication that can push to main.
3. Codex CLI installed and authenticated, or another local coding-agent runner.
4. PowerShell with the ScheduledTasks module.

For the included Codex runner:

    Set-Location C:\path\to\SEPP-MarketRadar
    .\tools\install_overnight_agent.ps1 -RepoPath "C:\path\to\SEPP-MarketRadar" -AgentRunner "C:\path\to\SEPP-MarketRadar\tools\run_codex_agent.ps1"

The included runner uses non-interactive codex exec with a workspace-write sandbox and does not push. The controller owns the push step. OpenAI documents codex exec as the non-interactive mode for scripts and CI, including prompt input through stdin.

Windows Task Scheduler supports minute schedules/repetition intervals, and IgnoreNew prevents overlapping task instances.

## Agent-runner contract

Input: one prompt-file path.
Working directory: repository root.
Expected behavior: inspect -> code -> test -> commit.
Exit code 0: completed or intentionally made no change.
Non-zero: failed/aborted.

The runner should not push. The controller owns the push step.

## Morning audit

    Get-ScheduledTask -TaskName "SEPP-MarketRadar-Autonomous-Agent"

    Get-ChildItem .agent\logs | Sort-Object LastWriteTime -Descending | Select-Object -First 10

Then inspect GitHub main history, GitHub Actions, and docs/DEBUG_HANDOFF.md.

## Important limitation

The repository can provide the controller and protocol, but this ChatGPT session cannot itself remain a background process on the user's PC after the conversation stops. The one-time Windows installation is the boundary between chat and the real overnight executor.

Target state:

Chat = engineer/orchestrator when present.
Windows agent = continuous executor.
GitHub = shared source of truth and audit trail.

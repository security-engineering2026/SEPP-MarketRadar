# Autonomous Progress

Repository: https://github.com/security-engineering2026/SEPP-MarketRadar
Branch: main
Control loop: AUDIT -> IMPLEMENT -> TEST -> FIX -> COMMIT -> CONTINUE
Cadence target: every 10 minutes
Current mode: LOCAL_MODEL_NO_PAID_API

## Current status
- Paid cloud coding engines are intentionally disabled.
- Copilot CLI was blocked by repository/organization policy.
- OpenAI/Anthropic/Gemini API keys are not required by the local engine.
- GitHub Actions is now a checkpoint/test observer, not the coding engine.
- Local coding engine: Ollama on Windows.
- Default model: qwen2.5-coder:7b.
- Local runner: tools/run_local_autonomous_cycle.ps1.
- Scheduled-task installer: tools/install_local_autonomy.ps1.

## Control loop
1. Read the latest checkpoint and handoff.
2. Run pytest.
3. Build targeted context from failure evidence and documented OPEN defects.
4. Ask the local model for exactly one unified diff.
5. Validate and apply the patch.
6. Run tests.
7. If tests fail, discard the patch.
8. If tests pass, commit and push to main.
9. The next scheduled cycle starts from the new main commit.

## Evidence rules
- No PASS/100%/production claims without fresh execution evidence.
- UNKNOWN and OPEN remain explicit.
- No secrets are sent to the model.
- No paid provider endpoint is called by the local engine.
- Local model failure records a supervisor checkpoint.

## Previous blocked cloud attempts
- Copilot execution: blocked by GitHub policy.
- OpenAI API attempt: reached the API but returned HTTP 429.
Those paths are removed from the active workflow.

## Next action
On Windows:
1. Install/start Ollama.
2. Install the default local coding model.
3. Run tools/run_local_autonomous_cycle.ps1 once manually.
4. If that succeeds, install the 10-minute task with tools/install_local_autonomy.ps1.

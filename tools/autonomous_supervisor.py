"""Minimal autonomous supervisor for SEPP-MarketRadar.

This process deliberately separates supervision from code-generation. It can run
without Copilot: it audits the repository, executes the configured test command,
records exact evidence, and preserves a continuation checkpoint. A coding engine
can later be attached through AUTONOMOUS_AGENT_COMMAND without changing the loop.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "docs" / "AUTONOMOUS_PROGRESS.md"
HANDOFF = ROOT / "docs" / "DEBUG_HANDOFF.md"
CHECKPOINT = ROOT / "docs" / "AUTONOMOUS_CHECKPOINT.json"
MAX_OUTPUT = 12000


def run(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    p = subprocess.run(
        cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout
    )
    out = (p.stdout + "\n" + p.stderr).strip()
    return p.returncode, out[-MAX_OUTPUT:]


def main() -> int:
    stamp = datetime.now(timezone.utc).isoformat()
    cycle = os.getenv("AUTONOMOUS_CYCLE", "supervisor")
    print(f"[AUTONOMOUS] {stamp} cycle={cycle}")

    dirty_code, status = run(["git", "status", "--short"])
    if dirty_code != 0:
        print(status)
        return 2
    if status:
        print("[BLOCKED] Worktree is dirty before supervisor start:")
        print(status)
        return 3

    head_rc, head = run(["git", "rev-parse", "HEAD"])
    if head_rc != 0:
        print(head)
        return 4

    test_cmd = os.getenv("AUTONOMOUS_TEST_COMMAND", "python -m pytest -q").split()
    print(f"[TEST] {' '.join(test_cmd)}")
    test_rc, test_out = run(test_cmd, timeout=int(os.getenv("AUTONOMOUS_TEST_TIMEOUT", "600")))
    result = "PASS" if test_rc == 0 else "OPEN"
    evidence_digest = hashlib.sha256(test_out.encode("utf-8")).hexdigest()
    checkpoint = {
        "schema": 1,
        "cycle": cycle,
        "timestamp_utc": stamp,
        "starting_commit": head,
        "test_command": " ".join(test_cmd),
        "test_exit_code": test_rc,
        "status": result,
        "evidence_digest": evidence_digest,
    }
    tmp = CHECKPOINT.with_suffix(".tmp")
    tmp.write_text(json.dumps(checkpoint, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(CHECKPOINT)

    checkpoint = f"""
## {stamp} — Autonomous Supervisor Cycle {cycle}

- Starting commit: `{head}`
- Supervisor execution: EXECUTED
- Code-generation engine: NOT CONFIGURED unless `AUTONOMOUS_AGENT_COMMAND` is supplied.
- Test command: `{' '.join(test_cmd)}`
- Test result: **{result}** (exit code {test_rc})
- Exact test tail:

```text
{test_out}
```

- Implementation status: NOT EXECUTED by this supervisor-only cycle.
- Next action: inspect this evidence and, when an approved coding engine is configured, execute one bounded implementation/fix cycle.
"""
    PROGRESS.write_text(PROGRESS.read_text(encoding="utf-8") + checkpoint, encoding="utf-8")

    rc, _ = run(["git", "add", "docs/AUTONOMOUS_PROGRESS.md", "docs/AUTONOMOUS_CHECKPOINT.json"])
    if rc != 0:
        return 5
    msg = f"chore(autonomy): record supervisor cycle {cycle}"
    rc, out = run(["git", "commit", "-m", msg])
    print(out)
    if rc != 0:
        return 6
    return 0 if test_rc == 0 else 10


if __name__ == "__main__":
    raise SystemExit(main())

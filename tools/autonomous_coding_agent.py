"""Local provider-free bounded coding engine for Windows/Ollama."""
from __future__ import annotations
import json, os, re, subprocess, urllib.error, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MAX_MODEL_CONTEXT = int(os.getenv("AUTONOMOUS_MODEL_CONTEXT", "90000"))
TEST_TIMEOUT = int(os.getenv("AUTONOMOUS_TEST_TIMEOUT", "600"))
MODEL = os.getenv("AUTONOMOUS_MODEL", "qwen2.5-coder:7b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")

def sh(*args: str, timeout: int = 120) -> tuple[int, str]:
    p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    return p.returncode, (p.stdout + "\n" + p.stderr).strip()

def read(path: Path, limit: int = 30000) -> str:
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except (OSError, UnicodeDecodeError):
        return ""

def test_snapshot() -> str:
    rc, out = sh("python", "-m", "pytest", "-q", timeout=TEST_TIMEOUT)
    return f"exit_code={rc}\n{out[-16000:]}"

def candidate_context(test_output: str) -> str:
    paths = [ROOT/"docs/MANIFEST.md", ROOT/"docs/MANIFEST_ASIS_AUDIT.md",
             ROOT/"docs/DEBUG_HANDOFF.md", ROOT/"docs/AUTONOMOUS_PROGRESS.md",
             ROOT/"tools/full_qualification.py", ROOT/"installer.iss",
             ROOT/"tools/windows_ci.py"]
    for match in re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.py", test_output):
        paths.append(ROOT / match)
    seen, chunks, total = set(), [], 0
    for path in paths:
        path = path.resolve()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        body = read(path)
        chunk = f"\n===== {path.relative_to(ROOT)} =====\n{body}\n"
        if total + len(chunk) > MAX_MODEL_CONTEXT:
            break
        chunks.append(chunk)
        total += len(chunk)
    return "".join(chunks)

def call_ollama(prompt: str) -> str:
    payload = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                          "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as response:
        return json.load(response).get("response", "")

def main() -> int:
    rc, status = sh("git", "status", "--porcelain")
    if rc != 0 or status:
        print("DIRTY_WORKTREE"); print(status); return 3
    rc, head = sh("git", "rev-parse", "HEAD")
    if rc: print(head); return 4
    evidence = test_snapshot()
    context = candidate_context(evidence)
    prompt = f"""You are a local bounded coding engineer for SEPP-MarketRadar.
Starting commit: {head}
Select ONE concrete reproducible defect from the evidence/context.
Make the smallest coherent fix and focused regression coverage when appropriate.
Never weaken security, evidence, policy, eligibility, payment, validation, or tests.
Never touch secrets or rewrite history.
Return ONLY a unified git diff beginning with 'diff --git'.
If no safe justified fix exists, return exactly NO_SAFE_FIX.

LATEST TEST EVIDENCE:
{evidence}

TARGETED REPOSITORY CONTEXT:
{context}
"""
    try:
        result = call_ollama(prompt)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"OLLAMA_ERROR: {exc}"); return 20
    if result.strip() == "NO_SAFE_FIX":
        print("NO_SAFE_FIX"); return 0
    marker = result.find("diff --git ")
    if marker < 0:
        print("INVALID_AGENT_OUTPUT"); return 21
    diff = result[marker:].strip()
    patch = ROOT / ".agent" / "proposed.patch"
    patch.parent.mkdir(exist_ok=True)
    patch.write_text(diff + "\n", encoding="utf-8")
    rc, out = sh("git", "apply", "--check", str(patch))
    if rc: print("PATCH_REJECTED"); print(out); return 23
    rc, out = sh("git", "apply", "--index", str(patch))
    if rc: print("PATCH_APPLY_FAILED"); print(out); return 24
    test_cmd = os.getenv("AUTONOMOUS_TEST_COMMAND", "python -m pytest -q").split()
    rc, out = sh(*test_cmd, timeout=TEST_TIMEOUT); print(out[-16000:])
    if rc:
        sh("git", "reset", "--hard", "HEAD")
        print("TEST_FAILED_PATCH_DISCARDED"); return 25
    sh("git", "config", "user.name", "autonomous-local-engineer")
    sh("git", "config", "user.email", "autonomous-local-engineer@users.noreply.github.com")
    rc, out = sh("git", "commit", "-am", "fix(autonomy): apply bounded tested local repair")
    print(out); return rc

if __name__ == "__main__":
    raise SystemExit(main())

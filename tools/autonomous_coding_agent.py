"""Provider-neutral bounded coding engine for the autonomous supervisor."""
from __future__ import annotations
import json, os, subprocess, urllib.request
from urllib.error import HTTPError, URLError
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROMPT="""You are the bounded coding engineer for SEPP-MarketRadar.
Read docs/MANIFEST.md, docs/MANIFEST_ASIS_AUDIT.md, docs/DEBUG_HANDOFF.md, docs/AUTONOMOUS_PROGRESS.md.
Select ONE concrete reproducible defect. Prefer failing CI/test evidence.
Return ONLY a unified git diff. Fix the defect and add focused regression coverage.
Do not weaken security, policy, evidence gates, or tests. Do not touch secrets.
If no safe concrete fix is justified, return NO_SAFE_FIX."""
def sh(*args,timeout=120):
    p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
    return p.returncode,(p.stdout+"\n"+p.stderr).strip()
def call_openai(key):
    body=json.dumps({"model":os.getenv("OPENAI_MODEL","gpt-5"),"input":PROMPT,"max_output_tokens":12000}).encode()
    req=urllib.request.Request("https://api.openai.com/v1/responses",data=body,headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as r: return json.load(r).get("output_text","")
def call_anthropic(key):
    body=json.dumps({"model":os.getenv("ANTHROPIC_MODEL","claude-sonnet-4-5"),"max_tokens":12000,"messages":[{"role":"user","content":PROMPT}]}).encode()
    req=urllib.request.Request("https://api.anthropic.com/v1/messages",data=body,headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as r: return "".join(x.get("text","") for x in json.load(r).get("content",[]) if x.get("type")=="text")
def call_gemini(key):
    model=os.getenv("GEMINI_MODEL","gemini-2.5-pro")
    body=json.dumps({"contents":[{"parts":[{"text":PROMPT}]}]}).encode()
    req=urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/"+model+":generateContent?key="+key,data=body,headers={"content-type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as r: return json.load(r)["candidates"][0]["content"]["parts"][0]["text"]
def main():
    engine=os.getenv("AUTONOMOUS_ENGINE","").lower()
    key={"openai":os.getenv("OPENAI_API_KEY"),"anthropic":os.getenv("ANTHROPIC_API_KEY"),"gemini":os.getenv("GEMINI_API_KEY")}.get(engine)
    if not engine or not key: print("NOT_CONFIGURED"); return 20
    try:
        text={"openai":call_openai,"anthropic":call_anthropic,"gemini":call_gemini}[engine](key)
    except HTTPError as exc:
        print(f"ENGINE_HTTP_ERROR: HTTP {exc.code}. The configured provider credential was rejected or the endpoint is unavailable.")
        return 20
    except URLError as exc:
        print(f"ENGINE_NETWORK_ERROR: {exc}")
        return 20
    if text.strip()=="NO_SAFE_FIX": print("NO_SAFE_FIX"); return 0
    diff=text
    if "```diff" in diff: diff=diff.split("```diff",1)[1].split("```",1)[0].strip()
    elif "```" in diff: diff=diff.split("```",1)[1].split("```",1)[0].strip()
    if not diff.startswith("diff --git "): print("INVALID_AGENT_OUTPUT"); return 21
    rc,clean=sh("git","status","--porcelain")
    if rc or clean: print("DIRTY_WORKTREE"); return 22
    patch=ROOT/".agent"/"proposed.patch"; patch.parent.mkdir(exist_ok=True); patch.write_text(diff+"\n",encoding="utf-8")
    rc,out=sh("git","apply","--check",str(patch))
    if rc: print("PATCH_REJECTED"); print(out); return 23
    rc,out=sh("git","apply","--index",str(patch))
    if rc: print("PATCH_APPLY_FAILED"); print(out); return 24
    test_cmd=os.getenv("AUTONOMOUS_TEST_COMMAND","python -m pytest -q").split()
    rc,out=sh(*test_cmd,timeout=int(os.getenv("AUTONOMOUS_TEST_TIMEOUT","600"))); print(out[-12000:])
    if rc: sh("git","reset","--hard","HEAD"); print("TEST_FAILED_PATCH_DISCARDED"); return 25
    sh("git","config","user.name","autonomous-engineer"); sh("git","config","user.email","autonomous-engineer@users.noreply.github.com")
    rc,out=sh("git","commit","-am","fix(autonomy): apply bounded tested repair"); print(out); return rc
if __name__=="__main__": raise SystemExit(main())
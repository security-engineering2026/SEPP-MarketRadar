from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from marketradar import __version__
VALID = {"PASS", "OPEN", "FAIL", "SKIPPED"}

def now():
    return datetime.now(timezone.utc).isoformat()

def gate(name, status, details=None):
    if status not in VALID:
        raise ValueError("INVALID_GATE_STATUS:" + status)
    return {"name": name, "status": status, "details": details or {}}

def http_probe(url, timeout=10, method="GET", payload=None):
    req = urllib.request.Request(
        url,
        data=payload,
        method=method,
        headers={
            "User-Agent": f"SEPP-MarketRadar-FullQualification/{__version__}",
            "Accept": "application/json,text/plain,text/html,*/*",
            "X-MarketRadar-Qualification": "sandbox",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(4096)
            return {
                "reachable": True,
                "status_code": int(resp.status),
                "content_type": resp.headers.get("Content-Type"),
                "bytes_sampled": len(body),
            }
    except urllib.error.HTTPError as exc:
        return {
            "reachable": True,
            "status_code": int(exc.code),
            "content_type": exc.headers.get("Content-Type") if exc.headers else None,
            "error": "HTTPError:" + str(exc.code),
        }
    except Exception as exc:
        return {
            "reachable": False,
            "status_code": None,
            "error": type(exc).__name__ + ":" + str(exc),
        }

def network_gate():
    urls = ["https://www.python.org/", "https://github.com/"]
    results = {u: http_probe(u) for u in urls}
    good = sum(bool(v.get("reachable")) for v in results.values())
    status = "PASS" if good == len(urls) else ("OPEN" if good else "FAIL")
    return gate("NETWORK_PRECONDITION", status, {"probes": results})

def taxonomy_gate():
    from marketradar.taxonomy import BUNDLED_WORKFLOWS, TASKS
    required_tasks = {
        "pdf_to_word", "pdf_to_excel", "pdf_to_powerpoint",
        "image_to_word", "image_to_text", "audio_to_text",
        "translation_general", "word_formatting", "word_to_powerpoint",
        "excel_cleaning", "excel_automation", "data_entry",
    }
    required_bundles = {
        "pdf_to_word_formatted",
        "translation_to_word_layout",
        "translation_to_powerpoint",
        "excel_merge_clean_analyze_dashboard",
    }
    missing_tasks = sorted(required_tasks - set(TASKS))
    missing_bundles = sorted(required_bundles - set(BUNDLED_WORKFLOWS))
    return gate(
        "WORK_TAXONOMY_OUTPUT_CONTRACT",
        "PASS" if not missing_tasks and not missing_bundles else "FAIL",
        {"missing_tasks": missing_tasks, "missing_bundles": missing_bundles},
    )

def behavioral_output_gate():
    from marketradar.operationalization import run_local_operationalization_lab
    result = run_local_operationalization_lab()
    expected = {
        "opportunities": 1000,
        "evidence_min": 1000,
        "top7": 7,
        "do_now": 3,
        "state_after_claim": "DELIVERED",
        "final_state": "PAID",
    }
    actual = {
        "opportunities": result.get("opportunities"),
        "evidence": result.get("evidence"),
        "top7": result.get("top7"),
        "do_now": result.get("do_now"),
        "state_after_claim": (result.get("lifecycle") or {}).get("state_after_claim"),
        "final_state": (result.get("lifecycle") or {}).get("final_state"),
    }
    ok = (
        actual["opportunities"] == expected["opportunities"]
        and int(actual["evidence"] or 0) >= expected["evidence_min"]
        and actual["top7"] == expected["top7"]
        and actual["do_now"] == expected["do_now"]
        and actual["state_after_claim"] == expected["state_after_claim"]
        and actual["final_state"] == expected["final_state"]
        and bool(result.get("pass"))
    )
    return gate(
        "BEHAVIORAL_OUTPUT_AND_GOAL_MATCH",
        "PASS" if ok else "FAIL",
        {"expected": expected, "actual": actual, "fixture_warning": result.get("fixture_warning")},
    )

def resilience_gate():
    code = (
        "from marketradar.operationalization import run_local_operationalization_lab;"
        "r=run_local_operationalization_lab();"
        "raise SystemExit(0 if r.get('pass') else 1)"
    )
    runs = []
    for i in range(3):
        p = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        runs.append({"cycle": i + 1, "returncode": p.returncode, "stderr": p.stderr[-500:]})
        if p.returncode != 0:
            return gate("RESTART_AND_RECOVERY_REPEATABILITY", "FAIL", {"runs": runs})
    return gate("RESTART_AND_RECOVERY_REPEATABILITY", "PASS", {"cycles": 3, "runs": runs})

def live_discovery_gate():
    if not os.environ.get("SEARXNG_URL"):
        return gate("LIVE_GLOBAL_DISCOVERY", "OPEN", {"reason": "SEARXNG_URL is not configured."})
    with tempfile.TemporaryDirectory(prefix="mr-discovery-") as td:
        env = dict(os.environ)
        env["MARKETRADAR_DATA_ROOT"] = td
        env["MARKETRADAR_SEARCH_PROVIDER"] = "searxng"
        p = subprocess.run(
            [sys.executable, "-B", "-m", "marketradar.cli", "autonomous-discovery", "--max-cycles", "1"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
    return gate(
        "LIVE_GLOBAL_DISCOVERY",
        "PASS" if p.returncode == 0 else "FAIL",
        {"returncode": p.returncode, "stdout_tail": p.stdout[-4000:], "stderr_tail": p.stderr[-2000:]},
    )

def _select_acquisition_sample(records, sample_size=20):
    """Pick a deterministic, family-balanced sample instead of records[:N]."""
    candidates=[x for x in records if x.get("status") != "disabled" and x.get("base_url")]
    families={}
    for record in candidates:
        family=str(record.get("source_family") or "unknown").lower()
        families.setdefault(family,[]).append(record)
    for rows in families.values():
        rows.sort(key=lambda x:x.get("name",""))
    ordered=[]
    while families and len(ordered)<sample_size:
        progressed=False
        for family in sorted(list(families)):
            rows=families[family]
            if not rows:
                del families[family]
                continue
            ordered.append(rows.pop(0))
            progressed=True
            if len(ordered)>=sample_size:
                break
        if not progressed:
            break
    return ordered

def live_source_scale_gate(limit=500):
    from marketradar.db import connect, sync_source_contracts
    from marketradar.source_registry import load_source_records
    from marketradar.source_search import WebSearchProvider
    from marketradar.source_verification import SourceVerificationEngine

    records = load_source_records(ROOT / "config" / "sources.json")
    if len(records) < limit:
        return gate(
            "LIVE_SOURCE_REACHABILITY_500",
            "OPEN",
            {"registered_records": len(records), "requested": limit, "reason": "Fewer than 500 registry candidates."},
        )

    selected = records
    with tempfile.TemporaryDirectory(prefix="mr-sources-") as td:
        conn = connect(Path(td) / "qualification.db")
        sync_source_contracts(conn, selected)
        engine = SourceVerificationEngine(
            conn,
            selected,
            timeout=8,
            max_workers=16,
            max_policy_pages=3,
            search_provider=WebSearchProvider(timeout=8),
        )
        results = engine.verify([x["name"] for x in selected])
        confirmed = sum(x.get("source_verification_state") == "LIVE_CONFIRMED" for x in results)
        dead = sum(x.get("source_verification_state") == "DEAD" for x in results)
        conn.close()

    return gate(
        "LIVE_SOURCE_REACHABILITY_500",
        "PASS" if confirmed >= limit else "OPEN",
        {
            "candidate_registry": len(records),
            "checked": len(results),
            "live_reachable": confirmed,
            "dead": dead,
            "other": len(results) - confirmed - dead,
            "criterion": f"{limit} live-reachable source endpoints",
            "method": "all current registry candidates verified; endpoint reachability only; not a connector-capability claim",
        },
    )

def live_acquisition_sample_gate(sample_size=20):
    from marketradar.db import connect, sync_source_contracts
    from marketradar.runtime import MarketRadarRuntime
    from marketradar.source_registry import load_source_records

    records = load_source_records(ROOT / "config" / "sources.json")
    verified = _select_acquisition_sample(records, sample_size)
    if not verified:
        return gate("LIVE_ACQUISITION_SAMPLE", "OPEN", {"reason": "No candidate sources with URLs."})

    selected = verified
    with tempfile.TemporaryDirectory(prefix="mr-acquisition-") as td:
        conn = connect(Path(td) / "qualification.db")
        sync_source_contracts(conn, selected)
        runtime = MarketRadarRuntime(conn, selected, None, http_timeout=10, settings={})
        results = []
        for source in selected:
            try:
                result = runtime.federate(source["name"], force=True)
                results.append({"source": source["name"], "status": result.get("status"), "observations": result.get("observations", 0), "error": result.get("error")})
            except Exception as exc:
                results.append({"source": source["name"], "status": "ERROR", "observations": 0, "error": type(exc).__name__ + ":" + str(exc)})
        observed = sum(int(x.get("observations") or 0) for x in results if x.get("status") == "OK")
        ok = sum(x.get("status") == "OK" for x in results)
        conn.close()

    status = "PASS" if ok > 0 and observed > 0 else "OPEN"
    return gate(
        "LIVE_ACQUISITION_SAMPLE",
        status,
        {
            "attempted": len(results),
            "successful_federations": ok,
            "observations": observed,
            "criterion": "At least one real source acquisition must produce an observed opportunity/event",
            "results": results,
        },
    )

def family_surface_gate(family):
    from marketradar.source_registry import load_source_records
    records = load_source_records(ROOT / "config" / "sources.json")
    candidates = [
        x for x in records
        if str(x.get("source_family", "")).lower() == family
        and x.get("base_url")
        and x.get("status") != "disabled"
    ][:3]
    if not candidates:
        return gate(f"{family.upper()}_SOURCE_SURFACE", "OPEN", {"reason": "No registry candidates."})
    results = [
        {"name": x["name"], "url": x["base_url"], "probe": http_probe(x["base_url"])}
        for x in candidates
    ]
    reachable = sum(bool(x["probe"].get("reachable")) for x in results)
    return gate(
        f"{family.upper()}_SOURCE_SURFACE",
        "PASS" if reachable == len(results) else "OPEN",
        {"checked": results},
    )

def dynamic_browser_gate():
    url = os.environ.get("QUALIFY_DYNAMIC_URL")
    if not url:
        return gate("DYNAMIC_JS_BROWSER", "OPEN", {"reason": "QUALIFY_DYNAMIC_URL is not configured."})
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return gate("DYNAMIC_JS_BROWSER", "OPEN", {"reason": "Playwright is not installed.", "error": str(exc)})
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            title = page.title()
            body = page.locator("body").inner_text(timeout=10000)
            out = Path(os.environ.get("QUALIFICATION_ARTIFACT_DIR", "qualification-artifacts"))
            out.mkdir(parents=True, exist_ok=True)
            screenshot = out / "dynamic-browser.png"
            page.screenshot(path=str(screenshot), full_page=True)
            browser.close()
        return gate(
            "DYNAMIC_JS_BROWSER",
            "PASS" if title and len(body.strip()) >= 20 else "FAIL",
            {"url": url, "title": title, "body_text_chars": len(body.strip()), "screenshot": str(screenshot)},
        )
    except Exception as exc:
        return gate("DYNAMIC_JS_BROWSER", "FAIL", {"url": url, "error": type(exc).__name__ + ":" + str(exc)})

def engine_contract_gate():
    from marketradar.engine_contract import EngineManifest, EngineQA, EngineResult, build_job
    manifest = EngineManifest(
        "qualification-engine", "Qualification Engine", "1.0",
        standalone=True, connectable=True, capabilities=("qualification",),
        execution_mode="ENGINE_UNCONNECTED", health="UNKNOWN",
    )
    manifest.validate()
    job = build_job("qualification-engine", 1, "python_automation", operations=("validate",))
    result = EngineResult(job.job_id, "SUCCEEDED", outputs={"artifact": "qualification.txt"}, qa=EngineQA("PASS"))
    return gate("ENGINE_CONTRACT_LOCAL", "PASS", {"job": job.task_type, "result": result.status, "qa": result.qa.status})

def sandbox_endpoint_gate(name, env_name):
    url = os.environ.get(env_name)
    if not url:
        return gate(name, "OPEN", {"reason": env_name + " is not configured; no production side effect attempted."})
    payload = json.dumps({"market_radar_qualification": True, "mode": "sandbox", "timestamp": now()}).encode()
    probe = http_probe(url, timeout=20, method="POST", payload=payload)
    status = "PASS" if probe.get("reachable") and int(probe.get("status_code") or 0) < 300 else "FAIL"
    return gate(name, status, {"url": url, "probe": probe})

def main():
    out = Path(os.environ.get("QUALIFICATION_ARTIFACT_DIR", "qualification-artifacts"))
    out.mkdir(parents=True, exist_ok=True)

    funcs = [
        network_gate,
        taxonomy_gate,
        behavioral_output_gate,
        resilience_gate,
        live_discovery_gate,
        live_source_scale_gate,
        live_acquisition_sample_gate,
        lambda: family_surface_gate("social"),
        lambda: family_surface_gate("procurement"),
        dynamic_browser_gate,
        engine_contract_gate,
        lambda: sandbox_endpoint_gate("EXTERNAL_ENGINE_E2E", "QUALIFY_ENGINE_URL"),
        lambda: sandbox_endpoint_gate("APPLICATION_SANDBOX_E2E", "QUALIFY_APPLICATION_URL"),
        lambda: sandbox_endpoint_gate("PAYMENT_SANDBOX_E2E", "QUALIFY_PAYMENT_URL"),
        lambda: sandbox_endpoint_gate("PUSH_NOTIFICATION_E2E", "QUALIFY_PUSH_URL"),
    ]

    gates = []
    for fn in funcs:
        try:
            gates.append(fn())
        except Exception as exc:
            gates.append(gate(getattr(fn, "__name__", "UNKNOWN_GATE"), "FAIL", {"error": type(exc).__name__ + ":" + str(exc)}))

    summary = {
        "pass": sum(x["status"] == "PASS" for x in gates),
        "open": sum(x["status"] == "OPEN" for x in gates),
        "fail": sum(x["status"] == "FAIL" for x in gates),
        "skipped": sum(x["status"] == "SKIPPED" for x in gates),
    }
    report = {
        "qualification_version": "FULL-QUALIFICATION-V1",
        "product_version": __version__,
        "generated_at": now(),
        "summary": summary,
        "gates": gates,
        "policy": {
            "open_is_not_pass": True,
            "production_side_effects_forbidden": True,
            "sandbox_only_for_external_application_payment_push": True,
            "fixture_data_is_not_live_market_evidence": True,
        },
    }

    (out / "full_qualification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md = [
        "MarketRadar Full Qualification V1",
        "",
        "Product version: " + report["product_version"],
        "Generated: " + report["generated_at"],
        "",
        "PASS: " + str(summary["pass"]),
        "OPEN: " + str(summary["open"]),
        "FAIL: " + str(summary["fail"]),
        "SKIPPED: " + str(summary["skipped"]),
        "",
        "Gate | Status",
        "--- | ---",
    ]
    md.extend(x["name"] + " | " + x["status"] for x in gates)
    (out / "full_qualification.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if (summary["fail"] or summary["open"]) else 0

if __name__ == "__main__":
    raise SystemExit(main())

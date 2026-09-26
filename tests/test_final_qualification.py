from pathlib import Path
import os
import importlib.util


def _load_full_qualification():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("full_qualification", root / "tools" / "full_qualification.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_unconfigured_external_qualification_gates_are_explicitly_skipped(monkeypatch):
    fq = _load_full_qualification()
    for name in (
        "SEARXNG_URL",
        "QUALIFY_DYNAMIC_URL",
        "QUALIFY_ENGINE_URL",
        "QUALIFY_APPLICATION_URL",
        "QUALIFY_PAYMENT_URL",
        "QUALIFY_PUSH_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    assert fq.live_discovery_gate()["status"] == "SKIPPED"
    assert fq.dynamic_browser_gate()["status"] == "SKIPPED"
    assert fq.sandbox_endpoint_gate("EXTERNAL_ENGINE_E2E", "QUALIFY_ENGINE_URL")["status"] == "SKIPPED"
    assert fq.sandbox_endpoint_gate("APPLICATION_SANDBOX_E2E", "QUALIFY_APPLICATION_URL")["status"] == "SKIPPED"
    assert fq.sandbox_endpoint_gate("PAYMENT_SANDBOX_E2E", "QUALIFY_PAYMENT_URL")["status"] == "SKIPPED"
    assert fq.sandbox_endpoint_gate("PUSH_NOTIFICATION_E2E", "QUALIFY_PUSH_URL")["status"] == "SKIPPED"


def test_full_qualification_acceptance_blocks_on_open_or_fail():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "full-qualification.yml").read_text(encoding="utf-8")
    assert 'if ([int]$r.summary.open -gt 0 -or [int]$r.summary.fail -gt 0) {' in workflow


def test_live_source_scale_gate_uses_one_shallow_probe_per_endpoint(monkeypatch):
    fq = _load_full_qualification()

    records = [
        {"name": f"S{i:03d}", "base_url": f"https://example{i}.test/", "status": "active"}
        for i in range(500)
    ]
    calls = []

    monkeypatch.setattr(
        fq,
        "http_probe",
        lambda url, timeout=8: calls.append((url, timeout)) or {
            "reachable": True,
            "status_code": 403,
        },
    )
    monkeypatch.setattr(
        "marketradar.source_registry.load_source_records",
        lambda _path: records,
    )

    result = fq.live_source_scale_gate(limit=500)

    assert result["status"] == "PASS"
    assert result["details"]["checked"] == 500
    assert result["details"]["live_reachable"] == 500
    assert len(calls) == 500
    assert all(timeout == 8 for _, timeout in calls)
    assert result["details"]["method"].startswith("one bounded HTTP reachability probe")


def test_live_source_scale_gate_excludes_disabled_endpoints(monkeypatch):
    fq = _load_full_qualification()
    records = [
        {"name": "LIVE", "base_url": "https://live.example/", "status": "active"},
        {"name": "DISABLED", "base_url": "https://disabled.example/", "status": "disabled"},
    ]
    calls = []
    monkeypatch.setattr(
        fq,
        "http_probe",
        lambda url, timeout=8: calls.append(url) or {"reachable": True, "status_code": 200},
    )
    monkeypatch.setattr(
        "marketradar.source_registry.load_source_records",
        lambda _path: records,
    )

    result = fq.live_source_scale_gate(limit=1)

    assert result["status"] == "PASS"
    assert result["details"]["eligible_candidates"] == 1
    assert calls == ["https://live.example/"]

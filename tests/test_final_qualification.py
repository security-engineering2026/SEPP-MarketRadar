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


def test_full_qualification_acceptance_blocks_only_on_failures():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "full-qualification.yml").read_text(encoding="utf-8")
    assert 'if ([int]$r.summary.fail -gt 0) {' in workflow
    assert 'or [int]$r.summary.open -gt 0' not in workflow

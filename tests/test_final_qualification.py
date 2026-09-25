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


def test_full_qualification_acceptance_blocks_on_open_or_failure():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "full-qualification.yml").read_text(encoding="utf-8")
    assert 'if ([int]$r.summary.open -gt 0 -or [int]$r.summary.fail -gt 0) {' in workflow

def test_family_surface_gate_uses_registry_taxonomy_aliases(monkeypatch):
    fq = _load_full_qualification()
    records = [
        {"name": "social-a", "source_family": "social_platform", "base_url": "https://social.example", "status": "candidate"},
        {"name": "social-b", "source_family": "telegram", "base_url": "https://telegram.example", "status": "candidate"},
        {"name": "proc-a", "source_family": "market_intelligence", "base_url": "https://proc.example", "status": "candidate"},
    ]
    monkeypatch.setattr(
        "marketradar.source_registry.load_source_records",
        lambda _path: records,
    )
    monkeypatch.setattr(
        fq,
        "http_probe",
        lambda url: {"reachable": True, "status_code": 200, "url": url},
    )

    social = fq.family_surface_gate("social")
    procurement = fq.family_surface_gate("procurement")

    assert social["status"] == "PASS"
    assert procurement["status"] == "PASS"
    assert len(social["details"]["checked"]) == 2
    assert len(procurement["details"]["checked"]) == 1


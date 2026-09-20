import json
from pathlib import Path
from marketradar.source_registry import load_source_records
from marketradar.source_onboarding import audit_registry

ROOT=Path(__file__).parents[1]

def test_no_exact_duplicate_source_urls():
    rows=load_source_records(ROOT/"config/sources.json")
    urls=[r["base_url"] for r in rows]
    assert len(urls)==len(set(urls))

def test_iran_policy_metadata_exists_for_allow_and_block():
    rows=load_source_records(ROOT/"config/sources.json")
    for r in rows:
        if r.get("iran_status") in {"ALLOW","BLOCK"}:
            assert r.get("iran_policy_basis")
            assert r.get("policy_checked_at")

def test_registry_has_no_active_daily_unknown_sources():
    rows=load_source_records(ROOT/"config/sources.json")
    assert not [r["name"] for r in rows if r.get("status")=="active" and r.get("policy_lane")=="DAILY_PROJECT_SCAN" and r.get("iran_status")!="ALLOW"]

def test_known_iran_blocked_evidence_urls_are_recorded():
    rows={r["name"]:r for r in load_source_records(ROOT/"config/sources.json")}
    for name in ("Upwork","Freelancer","PeoplePerHour","Toptal","Bugcrowd","Synack"):
        assert rows[name]["policy_lane"]=="BLOCKED_IRAN"
        assert rows[name].get("iran_policy_url")

def test_product_and_release_audits_pass_policy_shape():
    report=audit_registry(load_source_records(ROOT/"config/sources.json"))
    assert report["invalid"]==0


def test_source_policy_evidence_persists_to_db():
    import tempfile
    from marketradar.db import connect, sync_source_contracts
    with tempfile.TemporaryDirectory() as d:
        c=connect(Path(d)/"x.db")
        try:
            rows=load_source_records(ROOT/"config/sources.json")
            sync_source_contracts(c,rows)
            row=c.execute("SELECT iran_policy_basis,iran_policy_url,policy_checked_at,source_origin FROM sources WHERE name='Kaya_Iran_Intermediary'").fetchone()
            assert row and row[0]=='iran_friendly_intermediary' and row[1]=='https://kaya.ir/' and row[2]=='2026-09-11' and row[3]=='iran_intermediary'
        finally:
            c.close()

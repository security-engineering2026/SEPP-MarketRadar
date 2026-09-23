from __future__ import annotations

import tempfile
from pathlib import Path

from marketradar.application import transition
from marketradar.db import connect
from marketradar.policy import POLICY_VERSION


def test_manifest_application_state_and_policy_binding():
    with tempfile.TemporaryDirectory() as td:
        c = connect(Path(td) / "test.db")
        c.execute("INSERT INTO opportunities(source,title,url,state) VALUES(?,?,?,?)", ("test", "Test", "https://example.test/op/1", "DISCOVERED"))
        oid = c.execute("SELECT id FROM opportunities WHERE url=?", ("https://example.test/op/1",)).fetchone()["id"]

        transition(c, oid, "ELIGIBILITY_CHECK", actor="test")
        row = c.execute("SELECT state FROM opportunities WHERE id=?", (oid,)).fetchone()
        assert row["state"] == "ELIGIBILITY_CHECK"

        c.execute(
            "INSERT INTO evidence(opportunity_id,kind,source,url,finding,confidence,provenance_root,observed_at,evidence_hash) VALUES(?,?,?,?,?,?,?,?,?)",
            (oid, "policy", "test", "https://example.test/policy", "test evidence", 0.9, "test", "2026-09-22T00:00:00+00:00", "a" * 64),
        )
        evidence_id = c.execute("SELECT id FROM evidence WHERE evidence_hash=?", ("a" * 64,)).fetchone()["id"]
        c.execute(
            "INSERT INTO claims(entity_type,entity_id,opportunity_id,claim_type,claim_value,confidence,observed_at,policy_version) VALUES(?,?,?,?,?,?,?,?)",
            ("Opportunity", oid, oid, "eligibility", "REVIEW", 0.9, "2026-09-22T00:00:00+00:00", POLICY_VERSION),
        )
        claim_id = c.execute("SELECT id FROM claims WHERE opportunity_id=? AND claim_type=?", (oid, "eligibility")).fetchone()["id"]
        c.execute("INSERT INTO claim_evidence(claim_id,evidence_id) VALUES(?,?)", (claim_id, evidence_id))
        linked = c.execute("SELECT 1 FROM claim_evidence WHERE claim_id=? AND evidence_id=?", (claim_id, evidence_id)).fetchone()
        assert linked is not None
        c.close()


def test_manifest_source_capability_contract_columns_exist():
    with tempfile.TemporaryDirectory() as td:
        c = connect(Path(td) / "test.db")
        source_cols = {row["name"] for row in c.execute("PRAGMA table_info(sources)")}
        contract_cols = {row["name"] for row in c.execute("PRAGMA table_info(source_contracts)")}
        for required in {"capability_maturity", "capability_evidence_json", "capability_checked_at", "stale_at"}:
            assert required in source_cols
            assert required in contract_cols
        c.close()


def test_manifest_identity_resolution_records_non_merge_states():
    from marketradar.goal_completion import resolve_entity

    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        first = resolve_entity(cdb, "Client", "Acme Consulting", domain="acme.example")
        second = resolve_entity(cdb, "Client", "Acme Consult", domain="other.example")
        rows = cdb.execute("SELECT decision FROM identity_matches ORDER BY id").fetchall()
        assert first is not None
        assert any(row["decision"] in {"POSSIBLE_MATCH", "NO_MATCH"} for row in rows)
        cdb.close()


def test_manifest_temporal_claim_conflict_is_immutable_and_explicit():
    from marketradar.pipeline import Pipeline
    from marketradar.db import connect
    with tempfile.TemporaryDirectory() as td:
        c = connect(Path(td) / "test.db")
        c.execute("INSERT INTO opportunities(source,title,url,state) VALUES(?,?,?,?)", ("test", "Temporal", "https://example.test/op/temporal", "DISCOVERED"))
        oid = c.execute("SELECT id FROM opportunities WHERE url=?", ("https://example.test/op/temporal",)).fetchone()["id"]
        c.execute("INSERT INTO evidence(opportunity_id,kind,source,url,finding,confidence,provenance_root,observed_at,evidence_hash) VALUES(?,?,?,?,?,?,?,?,?)", (oid, "policy", "test", "https://example.test/policy", "eligibility observed", 0.9, "test", "2026-09-22T00:00:00+00:00", "b" * 64))
        evidence_id = c.execute("SELECT id FROM evidence WHERE evidence_hash=?", ("b" * 64,)).fetchone()["id"]
        c.execute("INSERT INTO claims(entity_type,entity_id,opportunity_id,claim_type,claim_value,confidence,observed_at) VALUES(?,?,?,?,?,?,?)", ("Opportunity", oid, oid, "eligibility", "EXECUTE", 0.9, "2026-09-22T00:00:00+00:00"))
        old_id = c.execute("SELECT id FROM claims WHERE opportunity_id=? AND claim_type=?", (oid, "eligibility")).fetchone()["id"]
        c.execute("INSERT INTO claims(entity_type,entity_id,opportunity_id,claim_type,claim_value,confidence,observed_at) VALUES(?,?,?,?,?,?,?)", ("Opportunity", oid, oid, "eligibility", "BLOCK", 0.95, "2026-09-22T01:00:00+00:00"))
        new_id = c.execute("SELECT id FROM claims WHERE opportunity_id=? AND claim_value='BLOCK'", (oid,)).fetchone()["id"]
        c.execute("INSERT INTO claim_evidence(claim_id,evidence_id) VALUES(?,?)", (new_id, evidence_id))
        c.execute("INSERT INTO claim_conflicts(opportunity_id,claim_type,previous_claim_id,new_claim_id,relation,detected_at,details_json) VALUES(?,?,?,?,?,?,?)", (oid, "eligibility", old_id, new_id, "CONTRADICTS", "2026-09-22T01:00:00+00:00", "{}"))
        row = c.execute("SELECT relation FROM claim_conflicts WHERE previous_claim_id=? AND new_claim_id=?", (old_id, new_id)).fetchone()
        assert row["relation"] == "CONTRADICTS"
        try:
            c.execute("DELETE FROM claim_conflicts WHERE previous_claim_id=? AND new_claim_id=?", (old_id, new_id))
            assert False, "immutable conflict ledger allowed deletion"
        except Exception as exc:
            assert "immutable" in str(exc).lower()
        c.close()



def test_manifest_decision_trace_is_claim_evidence_bound_and_immutable():
    from marketradar.goal_completion import decision_center, record_decision_trace
    with tempfile.TemporaryDirectory() as td:
        c = connect(Path(td) / "test.db")
        c.execute("INSERT INTO opportunities(source,title,url,state,eligibility,application_ready,rank_score,score) VALUES(?,?,?,?,?,?,?,?)", ("test","Trace","https://example.test/op/trace","DISCOVERED","REVIEW",0,0.88,0.88))
        oid = c.execute("SELECT id FROM opportunities WHERE url=?", ("https://example.test/op/trace",)).fetchone()["id"]
        c.execute("INSERT INTO evidence(opportunity_id,kind,source,url,finding,confidence,provenance_root,observed_at,evidence_hash) VALUES(?,?,?,?,?,?,?,?,?)", (oid,"policy","test","https://example.test/e","verified fact",0.9,"test","2026-09-22T00:00:00+00:00","c"*64))
        eid = c.execute("SELECT id FROM evidence WHERE evidence_hash=?", ("c"*64,)).fetchone()["id"]
        did = record_decision_trace(c, decision_type="TEST_DECISION", policy_version=POLICY_VERSION, target_type="OPPORTUNITY", target_id=oid, action="RECOMMEND", parameters={"opportunity_id":oid}, evidence_ids=[eid], claims={"eligibility":{"value":"REVIEW"}}, state_snapshot={"state":"DISCOVERED"}, ranking_context={"rank_score":0.88}, actor="test", reason="evidence-backed test")
        row = c.execute("SELECT * FROM decision_traces WHERE decision_id=?", (did,)).fetchone()
        assert row["evidence_digest"]
        assert row["parameters_digest"]
        assert row["policy_version"] == POLICY_VERSION
        assert str(eid) in row["evidence_ids_json"]
        try:
            c.execute("DELETE FROM decision_traces WHERE decision_id=?", (did,))
            assert False, "decision trace allowed deletion"
        except Exception as exc:
            assert "immutable" in str(exc).lower()
        try:
            c.execute("UPDATE decision_traces SET reason='tampered' WHERE decision_id=?", (did,))
            assert False, "decision trace allowed update"
        except Exception as exc:
            assert "immutable" in str(exc).lower()
        c.close()



def test_manifest_source_capability_maturity_is_monotonic():
    from marketradar.capability import CAPABILITY_STAGES, CapabilityEvidence, advance_capability, capability_evidence_for_verification
    assert CAPABILITY_STAGES == ("REGISTERED", "DISCOVERED", "DOCUMENTED", "REACHABLE", "PARSEABLE", "VALIDATED", "POLICY_VERIFIED", "EXECUTION_READY")
    assert advance_capability("POLICY_VERIFIED", CapabilityEvidence("REACHABLE")) == "POLICY_VERIFIED"
    assert advance_capability("REGISTERED", CapabilityEvidence("PARSEABLE")) == "PARSEABLE"
    assert capability_evidence_for_verification(reachable=True, parseable=True, validated=True, policy_verified=True, execution_ready=False).stage == "POLICY_VERIFIED"
    assert capability_evidence_for_verification(reachable=True, parseable=True, validated=True, policy_verified=True, execution_ready=True).stage == "EXECUTION_READY"



def test_manifest_authorized_execution_has_immutable_outcome_trace():
    from marketradar.goal_completion import authorize_action, execute_authorized
    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        cdb.execute("INSERT INTO opportunities(source,title,url,state,eligibility) VALUES(?,?,?,?,?)", ("test","Exec","https://example.test/op/exec","DISCOVERED","EXECUTE"))
        oid = cdb.execute("SELECT id FROM opportunities WHERE url=?", ("https://example.test/op/exec",)).fetchone()["id"]
        cdb.execute("INSERT INTO evidence(opportunity_id,kind,source,url,finding,confidence,provenance_root,observed_at,evidence_hash) VALUES(?,?,?,?,?,?,?,?,?)", (oid,"policy","test","https://example.test/e","authorized test",0.95,"test","2026-09-22T00:00:00+00:00","d"*64))
        eid = cdb.execute("SELECT id FROM evidence WHERE evidence_hash=?", ("d"*64,)).fetchone()["id"]
        aid = authorize_action(cdb, "TEST_ACTION", str(oid), {"opportunity_id":oid,"x":1}, [eid], POLICY_VERSION, "test", ttl_seconds=60)
        execute_authorized(cdb, aid, "TEST_ACTION", str(oid), {"opportunity_id":oid,"x":1}, [eid], lambda: {"ok":True})
        row = cdb.execute("SELECT outcome,approval_ref,evidence_digest FROM decision_traces WHERE decision_type='ACTION_EXECUTION'").fetchone()
        assert row["outcome"] == "EXECUTED"
        assert row["approval_ref"] == aid
        assert row["evidence_digest"]
        cdb.close()


def test_manifest_daily_snapshot_has_immutable_trace_for_all_decision_buckets():
    from marketradar.goal_completion import decision_center
    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        rows = [
            ("top", "https://example.test/top", "DISCOVERED", "REVIEW", 0.95),
            ("blocked", "https://example.test/blocked", "DISCOVERED", "BLOCK", 0.80),
            ("unknown", "https://example.test/unknown", "DISCOVERED", "UNKNOWN", 0.70),
        ]
        for title, url, state, eligibility, score in rows:
            cdb.execute(
                "INSERT INTO opportunities(source,title,url,state,eligibility,application_ready,rank_score,score) VALUES(?,?,?,?,?,?,?,?)",
                ("test", title, url, state, eligibility, 0, score, score),
            )
        cdb.commit()
        decision_center(cdb)
        trace = cdb.execute(
            "SELECT * FROM decision_traces WHERE decision_type='DAILY_SNAPSHOT' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert trace is not None
        assert trace["target_type"] == "DECISION_SNAPSHOT"
        assert '"blocked"' in trace["claims_json"]
        assert '"unknown"' in trace["claims_json"]
        assert trace["evidence_digest"]
        try:
            cdb.execute("UPDATE decision_traces SET reason='tampered' WHERE id=?", (trace["id"],))
            assert False, "snapshot decision trace allowed update"
        except Exception as exc:
            assert "immutable" in str(exc).lower()
        cdb.close()
def test_manifest_qualification_report_uses_current_version_and_gate_name():
    root = Path(__file__).resolve().parents[1]
    source = (root / "tools" / "full_qualification.py").read_text(encoding="utf-8")
    from marketradar import __version__

    assert '"product_version": __version__' in source
    assert '"LIVE_SOURCE_REACHABILITY_500"' in source
    assert '"LIVE_SOURCE_SCALE_500"' not in source
    assert '"product_version": "16.1.1"' not in source
    assert '"User-Agent": f"SEPP-MarketRadar-FullQualification/{__version__}"' in source

def test_manifest_runtime_version_surfaces_are_not_hardcoded():
    root = Path(__file__).resolve().parents[1]
    android = (root / "marketradar" / "android_gateway.py").read_text(encoding="utf-8")
    cli = (root / "marketradar" / "cli.py").read_text(encoding="utf-8")
    release = (root / "packaging" / "build_windows_release.ps1").read_text(encoding="utf-8")

    assert "return {'version':__version__" in android
    assert "FINAL_VERIFICATION_{__version__}.json" in cli
    assert 'Unexpected version: $version' not in release
    assert "16.1.1" not in android
    assert "FINAL_VERIFICATION_16.1.1.json" not in cli
    assert '16.1.1' not in release

def test_self_hosted_full_qualification_uses_local_python():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "full-qualification.yml").read_text(encoding="utf-8")
    assert "runs-on: [self-hosted, Windows, X64, marketradar]" in workflow
    assert "actions/setup-python@" not in workflow
    assert "Prepare self-hosted Python" in workflow
    assert "PYTHON_3_12_PLUS_NOT_FOUND" in workflow
    assert "PYTHON_VERSION_TOO_OLD" in workflow

def test_manifest_recommendation_is_not_authorization():
    from marketradar.recommendation_engine import recommend

    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        cdb.execute(
            "INSERT INTO sources(name,source_lane,iran_eligibility) VALUES(?,?,?)",
            ("test", "DAILY_PROJECT_SCAN", "ALLOW"),
        )
        cdb.execute(
            "INSERT INTO opportunities(source,title,url,state,eligibility,rank_score,score,task_type,difficulty_score,evidence_confidence) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("test", "Recommended", "https://example.test/recommend", "DISCOVERED", "EXECUTE", 0.95, 0.95, "python_automation", 2, 0.9),
        )
        cdb.commit()

        result = recommend(cdb, {"selected_domains": ["python"]})
        assert result["top7"]
        assert result["top7"][0]["opportunity_id"] == cdb.execute("SELECT id FROM opportunities WHERE title=?", ("Recommended",)).fetchone()["id"]
        assert cdb.execute("SELECT COUNT(*) AS n FROM action_authorizations").fetchone()["n"] == 0
        assert cdb.execute("SELECT state FROM opportunities WHERE title=?", ("Recommended",)).fetchone()["state"] == "DISCOVERED"
        cdb.close()


def test_manifest_payment_claim_is_not_payment_verification():
    from marketradar.application import record_revenue, verify_payment

    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        cdb.execute(
            "INSERT INTO opportunities(source,title,url,state) VALUES(?,?,?,?)",
            ("test", "Payment", "https://example.test/payment", "DELIVERED"),
        )
        oid = cdb.execute("SELECT id FROM opportunities WHERE url=?", ("https://example.test/payment",)).fetchone()["id"]

        record_revenue(
            cdb, oid, 100, "USD", "2026-09-23T12:00:00+00:00", "PAY-001", commit=True
        )
        assert cdb.execute("SELECT state FROM opportunities WHERE id=?", (oid,)).fetchone()["state"] == "DELIVERED"
        assert cdb.execute("SELECT verification_state FROM revenue WHERE payment_ref=?", ("PAY-001",)).fetchone()["verification_state"] == "RECORDED_UNVERIFIED"

        result = verify_payment(cdb, oid, "PAY-001", status="NOT_VERIFIED", actor="test")
        assert result["status"] == "NOT_VERIFIED"
        assert cdb.execute("SELECT state FROM opportunities WHERE id=?", (oid,)).fetchone()["state"] == "DELIVERED"

        try:
            record_revenue(cdb, oid, 100, "USD", "2026-09-23T12:01:00+00:00", "PAY-001", commit=True)
            assert False, "duplicate payment reference was accepted"
        except Exception as exc:
            assert "unique" in str(exc).lower() or "constraint" in str(exc).lower()

        verify_payment(cdb, oid, "PAY-001", status="VERIFIED", actor="test")
        assert cdb.execute("SELECT state FROM opportunities WHERE id=?", (oid,)).fetchone()["state"] == "PAID"
        verification = cdb.execute(
            "SELECT status FROM payment_verification WHERE opportunity_id=? AND payment_ref=? ORDER BY id DESC LIMIT 1",
            (oid, "PAY-001"),
        ).fetchone()
        assert verification["status"] == "VERIFIED"
        cdb.close()

def test_manifest_outcomes_are_immutable_learning_inputs():
    from marketradar.outcome_learning import learning_summary
    from marketradar.runtime import MarketRadarRuntime

    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        cdb.execute(
            "INSERT INTO opportunities(source,title,url,state,category,budget) VALUES(?,?,?,?,?,?)",
            ("test", "Outcome", "https://example.test/outcome", "DISCOVERED", "python_debugging", 500),
        )
        oid = cdb.execute("SELECT id FROM opportunities WHERE url=?", ("https://example.test/outcome",)).fetchone()["id"]
        runtime = object.__new__(MarketRadarRuntime)
        runtime.c = cdb

        result = runtime.record_outcome(oid, "REJECTED", reason="budget", notes="immutable test")
        assert result["acceptance_probability"] >= 0
        row = cdb.execute(
            "SELECT outcome,reason,notes FROM opportunity_outcomes WHERE opportunity_id=? ORDER BY id DESC LIMIT 1",
            (oid,),
        ).fetchone()
        assert row["outcome"] == "REJECTED"
        assert row["reason"] == "budget"
        assert row["notes"] == "immutable test"
        assert cdb.execute("SELECT state FROM opportunities WHERE id=?", (oid,)).fetchone()["state"] == "REJECTED"
        assert any(item["reason"] == "budget" and item["outcome"] == "REJECTED" for item in learning_summary(cdb)["reasons"])

        try:
            cdb.execute("UPDATE opportunity_outcomes SET notes='tampered' WHERE opportunity_id=?", (oid,))
            assert False, "opportunity outcome ledger allowed update"
        except Exception as exc:
            assert "immutable" in str(exc).lower()

        try:
            cdb.execute("DELETE FROM opportunity_outcomes WHERE opportunity_id=?", (oid,))
            assert False, "opportunity outcome ledger allowed deletion"
        except Exception as exc:
            assert "immutable" in str(exc).lower()

        cdb.close()


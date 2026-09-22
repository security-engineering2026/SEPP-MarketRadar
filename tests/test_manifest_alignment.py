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

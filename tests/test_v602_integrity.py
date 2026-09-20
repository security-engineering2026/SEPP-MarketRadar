import hashlib
import tempfile
from pathlib import Path

import pytest

from marketradar.db import connect
from marketradar.operational_completion import (
    OperationalError, operational_gate, record_delivery, submit_with_approval,
)
from marketradar.pipeline import Pipeline


def _opp(c, state="IN_PROGRESS"):
    c.execute("INSERT INTO opportunities(source,title,url,description,eligibility,state,application_ready) VALUES(?,?,?,?,?,?,?)",
              ("s", "t", "https://example.test/o", "job", "EXECUTE", state, 1))
    c.commit()
    return c.execute("SELECT id FROM opportunities").fetchone()[0]


def _evidence(c, oid):
    c.execute("INSERT INTO evidence(opportunity_id,kind,source,url,finding,confidence,provenance_root,observed_at,evidence_hash) VALUES(?,?,?,?,?,?,?,?,?)",
              (oid, "listing", "s", "https://example.test/o", "listing", .9, "s", "2026-09-11T00:00:00+00:00", hashlib.sha256(f"{oid}".encode()).hexdigest()))
    c.commit()
    return [c.execute("SELECT id FROM evidence WHERE opportunity_id=?", (oid,)).fetchone()[0]]


def test_delivery_rejects_false_checksum_and_leaves_state_unchanged():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/"x.db"); oid=_opp(c)
            artifact=Path(d)/"artifact.txt"; artifact.write_text("real", encoding="utf-8")
            with pytest.raises(OperationalError, match="DELIVERY_CHECKSUM_MISMATCH"):
                record_delivery(c, oid, str(artifact), checksum="0"*64)
            assert c.execute("SELECT state FROM opportunities WHERE id=?", (oid,)).fetchone()[0] == "IN_PROGRESS"
            assert c.execute("SELECT COUNT(*) FROM delivery_evidence").fetchone()[0] == 0
            c.close()
        finally:
            if 'c' in locals():
                c.close()


def test_submission_cannot_bypass_approval_pending():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/"x.db"); oid=_opp(c, "DISCOVERED"); ids=_evidence(c, oid)
            with pytest.raises(OperationalError, match="SUBMISSION_REQUIRES_APPROVAL_PENDING"):
                submit_with_approval(c, dict(c.execute("SELECT * FROM opportunities WHERE id=?", (oid,)).fetchone()), {}, "proposal", ids)
            assert c.execute("SELECT COUNT(*) FROM action_authorizations").fetchone()[0] == 0
            c.close()
        finally:
            if 'c' in locals():
                c.close()


def test_operational_gate_does_not_call_discovered_opportunity_execution_ready():
    with tempfile.TemporaryDirectory() as d:
        try:
            c=connect(Path(d)/"x.db"); oid=_opp(c, "DISCOVERED"); _evidence(c, oid)
            assert operational_gate(c)["execution_ready_opportunities"] == 0
            c.close()
        finally:
            if 'c' in locals():
                c.close()


def test_provider_spec_points_to_repository_root():
    spec=Path(__file__).parents[1]/"packaging"/"marketradar.spec"
    text=spec.read_text(encoding="utf-8")
    assert "ROOT = Path(SPECPATH).resolve().parent" in text
    assert 'ROOT / "desktop" / "MarketRadar.pyw"' in text

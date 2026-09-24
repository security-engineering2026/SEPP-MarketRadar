from __future__ import annotations

import tempfile
from pathlib import Path
import hashlib

from marketradar.db import connect
from marketradar.goal_completion import authorize_action, execute_authorized
from marketradar.outcome_learning import learning_summary, record_outcome
from marketradar.pipeline import AcquisitionAttestation, Pipeline
from marketradar.policy import POLICY_VERSION


def test_r049_final_architecture_preserves_end_to_end_truth_chain():
    with tempfile.TemporaryDirectory() as td:
        db = connect(Path(td) / "r049.db")
        try:
            source = {
                "name": "R049_CHAIN",
                "base_url": "https://example.test/feed",
                "adapter": "json",
                "status": "active",
                "source_kind": "job_source",
                "acquisition": "http",
                "access_scope": "public",
                "iran_status": "ALLOW",
                "kyc_status": "ALLOW",
                "payment_status": "USDT",
                "terms_status": "allowed",
            }
            payload = b'{"items":[{"title":"R049 opportunity","url":"https://example.test/op/r049","iran_access":"ALLOW"}]}'

            digest = hashlib.sha256(payload).hexdigest()
            db.execute(
                "INSERT INTO raw_observations(source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind) VALUES(?,?,?,?,?,?,?,?)",
                (source["name"], source["base_url"], "2026-09-24T07:00:00+00:00", payload, digest, 200, "application/json", "source_response"),
            )
            db.commit()

            result = Pipeline(db).ingest(
                source,
                {
                    "title": "R049 opportunity",
                    "url": "https://example.test/op/r049",
                    "description": "final architecture chain",
                    "iran_access": "ALLOW",
                    "evidence": [
                        {
                            "kind": "listing",
                            "url": "https://example.test/op/r049",
                            "finding": "observed opportunity",
                            "confidence": 0.95,
                        }
                    ],
                },
                AcquisitionAttestation(
                    source["name"],
                    source["base_url"],
                    digest,
                    200,
                ),
            )
            db.commit()
            assert result

            opportunity = db.execute(
                "SELECT id,state FROM opportunities WHERE url=?",
                ("https://example.test/op/r049",),
            ).fetchone()
            assert opportunity is not None
            oid = opportunity["id"]

            raw = db.execute(
                "SELECT COUNT(*) AS n FROM raw_observations WHERE source=?",
                (source["name"],),
            ).fetchone()["n"]
            evidence = db.execute(
                "SELECT COUNT(*) AS n FROM evidence WHERE opportunity_id=?",
                (oid,),
            ).fetchone()["n"]
            claims = db.execute(
                "SELECT COUNT(*) AS n FROM claims WHERE opportunity_id=?",
                (oid,),
            ).fetchone()["n"]
            assert raw >= 1
            assert evidence >= 1
            assert claims >= 1

            from marketradar.goal_completion import decision_center

            decision_center(db)
            snapshot = db.execute(
                "SELECT id FROM decision_snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert snapshot is not None

            evidence_id = db.execute(
                "SELECT id FROM evidence WHERE opportunity_id=? ORDER BY id DESC LIMIT 1",
                (oid,),
            ).fetchone()["id"]
            authorization_id = authorize_action(
                db,
                "R049_TEST_ACTION",
                str(oid),
                {"opportunity_id": oid},
                [evidence_id],
                POLICY_VERSION,
                "r049-test",
                ttl_seconds=60,
            )
            execute_authorized(
                db,
                authorization_id,
                "R049_TEST_ACTION",
                str(oid),
                {"opportunity_id": oid},
                [evidence_id],
                lambda: {"accepted": True},
            )

            trace = db.execute(
                "SELECT outcome,approval_ref,evidence_digest FROM decision_traces "
                "WHERE decision_type='ACTION_EXECUTION' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            assert trace is not None
            assert trace["outcome"] == "EXECUTED"
            assert trace["approval_ref"] == authorization_id
            assert trace["evidence_digest"]

            outcome = record_outcome(
                db,
                oid,
                "ACCEPTED",
                reason="R049 architecture integration",
                notes="end-to-end learning signal",
            )
            assert outcome["acceptance_probability"] >= 0

            learning = learning_summary(db)
            assert learning
            stored_outcome = db.execute(
                "SELECT outcome,reason FROM opportunity_outcomes "
                "WHERE opportunity_id=? ORDER BY id DESC LIMIT 1",
                (oid,),
            ).fetchone()
            assert stored_outcome["outcome"] == "ACCEPTED"
            assert stored_outcome["reason"] == "R049 architecture integration"
        finally:
            db.close()

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



def test_manifest_observation_layer_preserves_acquisition_metadata_and_provenance():
    from marketradar.source_health import persist_health
    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        source = {
            "name": "OBS_TEST",
            "base_url": "https://example.test/feed",
            "adapter": "json",
            "status": "active",
            "source_kind": "website",
            "acquisition": "http",
            "access_scope": "public",
        }
        payload = b'{"items":[{"title":"observed"}]}'
        import hashlib
        digest = hashlib.sha256(payload).hexdigest()
        observed_at = "2026-09-23T18:00:00+00:00"
        cdb.execute(
            "INSERT INTO raw_observations(source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind) VALUES(?,?,?,?,?,?,?,?)",
            ("OBS_TEST", source["base_url"], observed_at, payload, digest, 200, "application/json", "source_response"),
        )
        cdb.commit()
        persist_health(cdb, source, {
            "status": "OK", "http_status": 200, "sha256": digest,
            "parse_ok": True, "parsed_count": 1, "error": None, "parse_error": None,
        })
        raw = cdb.execute(
            "SELECT source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind "
            "FROM raw_observations WHERE payload_sha256=?", (digest,)
        ).fetchone()
        run = cdb.execute(
            "SELECT source,status,http_status,observation_count,snapshot_sha256 "
            "FROM federation_runs WHERE snapshot_sha256=? ORDER BY id DESC LIMIT 1", (digest,)
        ).fetchone()
        health = cdb.execute(
            "SELECT source,http_status,parse_ok,parsed_count,snapshot_sha256 "
            "FROM source_health_history WHERE snapshot_sha256=? ORDER BY id DESC LIMIT 1", (digest,)
        ).fetchone()
        assert raw is not None and run is not None and health is not None
        assert raw["source"] == run["source"] == health["source"] == "OBS_TEST"
        assert raw["url"] == source["base_url"]
        assert raw["observed_at"] == observed_at
        assert raw["payload"] == payload
        assert raw["payload_sha256"] == digest
        assert raw["http_status"] == run["http_status"] == health["http_status"] == 200
        assert raw["content_type"] == "application/json"
        assert raw["observation_kind"] == "source_response"
        assert run["snapshot_sha256"] == health["snapshot_sha256"] == digest
        assert health["parse_ok"] == 1 and health["parsed_count"] == 1
        cdb.close()

    
def test_manifest_canonical_opportunity_preserves_observation_and_conflicting_evidence():
    from marketradar.pipeline import AcquisitionAttestation, Pipeline
    import hashlib

    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        source = {
            "name": "CANONICAL_TEST", "base_url": "https://example.test/feed",
            "adapter": "json", "status": "active", "source_kind": "website",
            "acquisition": "http", "access_scope": "public", "iran_status": "ALLOW",
            "kyc_status": "ALLOW", "payment_status": "USDT", "terms_status": "allowed",
        }
        url = "https://example.test/op/1"
        payloads = [
            b'{"items":[{"title":"First observation","url":"https://example.test/op/1"}]}',
            b'{"items":[{"title":"Second observation","url":"https://example.test/op/1"}]}',
        ]
        digests = [hashlib.sha256(p).hexdigest() for p in payloads]
        for i, (payload, digest) in enumerate(zip(payloads, digests), 1):
            cdb.execute(
                "INSERT INTO raw_observations(source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind) VALUES(?,?,?,?,?,?,?,?)",
                ("CANONICAL_TEST", source["base_url"], f"2026-09-23T18:0{i}:00+00:00", payload, digest, 200, "application/json", "source_response"),
            )
        cdb.commit()
        p = Pipeline(cdb)
        for i, digest in enumerate(digests):
            item = {
                "title": f"Observation {i}", "url": url,
                "description": "same opportunity observed with different policy evidence",
                "iran_access": "ALLOW" if i == 0 else "BLOCK",
                "evidence": [{"kind": "listing", "url": url, "finding": f"observation-{i}", "confidence": 0.95}],
            }
            p.ingest(source, item, AcquisitionAttestation("CANONICAL_TEST", source["base_url"], digest, 200))
            cdb.commit()
        opportunity = cdb.execute("SELECT id FROM opportunities WHERE url=?", (url,)).fetchone()
        assert opportunity is not None
        evidence_rows = cdb.execute("SELECT observation_id,finding FROM evidence WHERE opportunity_id=? ORDER BY id", (opportunity["id"],)).fetchall()
        assert len(evidence_rows) == 2
        assert all(row["observation_id"] is not None for row in evidence_rows)
        assert len({row["observation_id"] for row in evidence_rows}) == 2
        assert {row["finding"] for row in evidence_rows} == {"observation-0", "observation-1"}
        claim_conflicts = cdb.execute("SELECT relation FROM claim_conflicts WHERE opportunity_id=? AND claim_type='iran_access'", (opportunity["id"],)).fetchall()
        assert any(row["relation"] == "CONTRADICTS" for row in claim_conflicts)
        raw_count = cdb.execute("SELECT COUNT(*) AS n FROM raw_observations WHERE source='CANONICAL_TEST'").fetchone()["n"]
        assert raw_count == 2
        cdb.close()

    
def test_manifest_deduplication_uses_canonical_opportunity_identity_and_retains_history():
    from marketradar.pipeline import Pipeline

    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        source = {
            "name": "DEDUP_TEST", "base_url": "https://example.test/feed",
            "adapter": "json", "status": "active", "source_kind": "website",
            "acquisition": "http", "access_scope": "public", "iran_status": "ALLOW",
            "kyc_status": "ALLOW", "payment_status": "USDT", "terms_status": "allowed",
        }
        p = Pipeline(cdb)
        first = {
            "title": "Stable identity",
            "url": "https://example.test/op/42?utm_source=feed",
            "description": "first observation",
            "evidence": [{"kind": "listing", "url": "https://example.test/op/42", "finding": "first", "confidence": 0.9}],
        }
        second = {
            "title": "Stable identity updated",
            "url": "https://EXAMPLE.TEST/op/42#tracking",
            "description": "second observation",
            "evidence": [{"kind": "listing", "url": "https://example.test/op/42", "finding": "second", "confidence": 0.9}],
        }
        p.ingest(source, first)
        cdb.commit()
        p.ingest(source, second)
        cdb.commit()

        opportunities = cdb.execute("SELECT id,title FROM opportunities").fetchall()
        assert len(opportunities) == 1
        oid = opportunities[0]["id"]
        assert cdb.execute("SELECT url FROM opportunities WHERE id=?", (oid,)).fetchone()["url"] == "https://example.test/op/42"

        evidence = cdb.execute("SELECT finding FROM evidence WHERE opportunity_id=? ORDER BY id", (oid,)).fetchall()
        assert {row["finding"] for row in evidence} == {"first", "second"}
        assert cdb.execute("SELECT COUNT(*) AS n FROM opportunity_sources WHERE opportunity_id=?", (oid,)).fetchone()["n"] == 1
        cdb.close()

    
def test_manifest_entity_resolution_exposes_match_possible_and_no_match_with_evidence():
    from marketradar.goal_completion import resolve_entity

    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        existing = resolve_entity(cdb, "Client", "Acme Consulting", domain="acme.example")
        matched = resolve_entity(cdb, "Client", "Acme Consulting Ltd", domain="acme.example", evidence={"source": "exact"})
        possible_seed = resolve_entity(cdb, "Client", "Acme Consulting", evidence={"source": "seed"})
        possible = resolve_entity(cdb, "Client", "Acme Consulting Group", evidence={"source": "similar"})
        no_match = resolve_entity(cdb, "Client", "Completely Different Buyer", domain="different.example", evidence={"source": "distinct"})

        assert matched == existing
        assert possible != existing
        assert no_match != existing
        rows = cdb.execute(
            "SELECT decision,confidence,evidence_json FROM identity_matches WHERE entity_type='Client' ORDER BY id"
        ).fetchall()
        decisions = {row["decision"] for row in rows}
        assert {"MATCH", "POSSIBLE_MATCH", "NO_MATCH"} <= decisions
        for row in rows:
            assert row["confidence"] is not None
            assert row["evidence_json"] is not None
        cdb.close()

    
def test_manifest_party_resolution_keeps_party_roles_distinct():
    from marketradar.goal_completion import party_from_opportunity

    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        base = {"name": "Same Organization", "domain": "same.example"}
        client_id = party_from_opportunity(cdb, {"party_type": "Client", "client": base, "url": "https://example.test/client"}, 1)
        employer_id = party_from_opportunity(cdb, {"party_type": "Employer", "employer": base, "url": "https://example.test/employer"}, 2)
        agency_id = party_from_opportunity(cdb, {"party_type": "Agency", "agency": base, "url": "https://example.test/agency"}, 3)

        assert len({client_id, employer_id, agency_id}) == 3
        rows = cdb.execute(
            "SELECT entity_id,party_type FROM parties WHERE entity_id IN (?,?,?) ORDER BY party_type",
            (client_id, employer_id, agency_id),
        ).fetchall()
        assert {row["party_type"] for row in rows} == {"Agency", "Client", "Employer"}
        assert all(row["entity_id"] != rows[(i + 1) % len(rows)]["entity_id"] for i, row in enumerate(rows))
        cdb.close()

    
def test_manifest_evidence_graph_links_source_observation_evidence_claim_and_domain_object():
    from marketradar.pipeline import AcquisitionAttestation, Pipeline
    import hashlib

    with tempfile.TemporaryDirectory() as td:
        cdb = connect(Path(td) / "test.db")
        source = {
            "name": "GRAPH_TEST", "base_url": "https://example.test/feed",
            "adapter": "json", "status": "active", "source_kind": "website",
            "acquisition": "http", "access_scope": "public", "iran_status": "ALLOW",
            "kyc_status": "ALLOW", "payment_status": "USDT", "terms_status": "allowed",
        }
        payloads = [
            b'{"items":[{"title":"Graph opportunity","url":"https://example.test/op/graph","iran_access":"ALLOW"}]}',
            b'{"items":[{"title":"Graph opportunity","url":"https://example.test/op/graph","iran_access":"BLOCK"}]}',
        ]
        digests = [hashlib.sha256(p).hexdigest() for p in payloads]
        for i, (payload, digest) in enumerate(zip(payloads, digests), 1):
            cdb.execute(
                "INSERT INTO raw_observations(source,url,observed_at,payload,payload_sha256,http_status,content_type,observation_kind) VALUES(?,?,?,?,?,?,?,?)",
                ("GRAPH_TEST", source["base_url"], f"2026-09-23T20:0{i}:00+00:00", payload, digest, 200, "application/json", "source_response"),
            )
        cdb.commit()

        for i, digest in enumerate(digests):
            Pipeline(cdb).ingest(
                source,
                {
                    "title": "Graph opportunity",
                    "url": "https://example.test/op/graph",
                    "description": "graph evidence",
                    "iran_access": "ALLOW" if i == 0 else "BLOCK",
                    "evidence": [{"kind": "listing", "url": "https://example.test/op/graph", "finding": f"observed-{i}", "confidence": 0.95}],
                },
                AcquisitionAttestation("GRAPH_TEST", source["base_url"], digest, 200),
            )
            cdb.commit()

        opportunity = cdb.execute("SELECT id,source FROM opportunities WHERE url=?", ("https://example.test/op/graph",)).fetchone()
        observations = cdb.execute("SELECT id,source,payload_sha256 FROM raw_observations WHERE payload_sha256 IN (?,?) ORDER BY id", (digests[0], digests[1])).fetchall()
        evidence_rows = cdb.execute("SELECT id,opportunity_id,observation_id,source,finding FROM evidence WHERE opportunity_id=? ORDER BY id", (opportunity["id"],)).fetchall()
        claims = cdb.execute("SELECT id,opportunity_id,claim_type,claim_value FROM claims WHERE opportunity_id=? ORDER BY id", (opportunity["id"],)).fetchall()
        claim_links = cdb.execute("SELECT claim_id,evidence_id FROM claim_evidence WHERE claim_id IN (SELECT id FROM claims WHERE opportunity_id=?)", (opportunity["id"],)).fetchall()
        conflicts = cdb.execute("SELECT relation FROM claim_conflicts WHERE opportunity_id=? AND claim_type='iran_access'", (opportunity["id"],)).fetchall()

        assert len(observations) == 2
        assert all(row["source"] == "GRAPH_TEST" for row in observations)
        assert opportunity["source"] == "GRAPH_TEST"
        assert len(evidence_rows) == 2
        assert {row["observation_id"] for row in evidence_rows} == {row["id"] for row in observations}
        assert all(row["opportunity_id"] == opportunity["id"] and row["source"] == "GRAPH_TEST" for row in evidence_rows)
        assert {row["finding"] for row in evidence_rows} == {"observed-0", "observed-1"}
        assert len(claims) >= 1
        assert all(row["opportunity_id"] == opportunity["id"] for row in claims)
        assert {row["evidence_id"] for row in claim_links} == {row["id"] for row in evidence_rows}
        assert all(row["claim_id"] in {c["id"] for c in claims} for row in claim_links)
        assert any(row["relation"] == "CONTRADICTS" for row in conflicts)
        cdb.close()

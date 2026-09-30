import json
from pathlib import Path
from marketradar.source_registry import load_source_records
from marketradar.source_onboarding import audit_registry
from marketradar import __version__

ROOT=Path(__file__).parents[1]

def test_registry_has_explicit_verification_fields():
    rows=load_source_records(ROOT/'config/sources.json')
    required={'source_verification_state','iran_eligibility','kyc_requirement','evidence_confidence','market_intelligence_value','execution_ready','discovery_basis'}
    assert all(required.issubset(r) for r in rows)

def test_daily_execution_gate_is_strict():
    rows=load_source_records(ROOT/'config/sources.json')
    bad=[r['name'] for r in rows if r.get('policy_lane')=='DAILY_PROJECT_SCAN' and r.get('execution_ready') and (r.get('iran_eligibility')!='ALLOW' or r.get('source_verification_state')!='LIVE_CONFIRMED')]
    assert not bad

def test_blocked_sources_never_execution_ready():
    rows=load_source_records(ROOT/'config/sources.json')
    assert not [r['name'] for r in rows if r.get('policy_lane')=='BLOCKED_IRAN' and r.get('execution_ready')]

def test_release_snapshot_matches_registry():
    rows=load_source_records(ROOT/'config/sources.json')
    snap=json.loads((ROOT/'reports/release_snapshot.json').read_text())
    assert snap['version']==__version__
    assert snap['sources']==len(rows)
    assert snap['active']==sum(r.get('status')=='active' for r in rows)
    assert snap['daily_execution_ready']==sum(r.get('policy_lane')=='DAILY_PROJECT_SCAN' and r.get('execution_ready') for r in rows)

def test_explicit_iran_restrictions_are_blocked():
    rows={r['name']:r for r in load_source_records(ROOT/'config/sources.json')}
    for name in ('Kwork','Mostaql','Khamsat'):
        assert rows[name]['policy_lane']=='BLOCKED_IRAN'
        assert rows[name]['iran_eligibility']=='BLOCK'
        assert rows[name]['terms_status']=='blocked'
        assert rows[name]['iran_policy_url']

def test_source_audit_has_no_invalid_records():
    report=audit_registry(load_source_records(ROOT/'config/sources.json'))
    assert report['invalid']==0


def test_row4_verification_fetches_direct_terms_candidate(tmp_path):
    from marketradar.db import connect
    from marketradar.source_verification import SourceVerificationEngine

    connection = connect(tmp_path / "row4-terms.db")
    source = {
        "name": "Row4TermsSource",
        "base_url": "https://example.test/jobs",
        "adapter": "json",
        "status": "active",
        "allow_hosts": ["example.test"],
        "access_scope": "public",
        "terms_status": "needs_review",
        "execution_capability": "authorized_api",
    }
    engine = SourceVerificationEngine(connection, [source], search_provider=None, surface_scan_pages=1)

    def fake_fetch(name, url=None):
        if url is None:
            return {"body": b"<html><body>Jobs</body></html>", "url": "https://example.test/jobs",
                    "status": 200, "bytes": 32, "sha256": "home"}
        if url == "https://example.test/terms-and-conditions":
            return {"body": b"<html><body>Terms of Service. These conditions apply to users.</body></html>",
                    "url": url, "status": 200, "bytes": 74, "sha256": "terms"}
        raise RuntimeError("not found")

    engine.http.fetch = fake_fetch
    engine.policy_http.fetch = fake_fetch
    result = engine._one("Row4TermsSource")
    assert result["terms_evidence_url"] == "https://example.test/terms-and-conditions"
    assert result["terms_status"] == "reviewed"
    assert "https://example.test/terms-and-conditions" in result["evidence_urls"]
    connection.close()


def test_row4_declared_policy_path_is_probed_before_default_candidates(tmp_path):
    from marketradar.db import connect
    from marketradar.source_verification import SourceVerificationEngine

    connection = connect(tmp_path / "row4-policy-path.db")
    source = {
        "name": "Row4DeclaredPolicyPathSource",
        "base_url": "https://example.test/jobs",
        "adapter": "json",
        "status": "active",
        "allow_hosts": ["example.test"],
        "access_scope": "public",
        "terms_status": "needs_review",
        "policy_paths": ["/legal/terms-of-service"],
    }
    engine = SourceVerificationEngine(connection, [source], search_provider=None, surface_scan_pages=1)
    seen = []

    def fake_fetch(name, url=None):
        if url is None:
            return {"body": b"<html><body>Jobs</body></html>", "url": source["base_url"],
                    "status": 200, "bytes": 32, "sha256": "home"}
        seen.append(url)
        if url == "https://example.test/legal/terms-of-service":
            return {"body": b"<html><body>Terms of Service. These conditions apply to users.</body></html>",
                    "url": url, "status": 200, "bytes": 74, "sha256": "terms"}
        raise RuntimeError("not found")

    engine.http.fetch = fake_fetch
    engine.policy_http.fetch = fake_fetch
    result = engine._one(source["name"])

    assert seen
    assert seen[0] == "https://example.test/legal/terms-of-service"
    assert result["terms_evidence_url"] == "https://example.test/legal/terms-of-service"
    assert result["terms_status"] == "reviewed"
    connection.close()


def test_row4_terms_close_when_operational_api_is_unavailable(tmp_path):
    from marketradar.db import connect
    from marketradar.source_verification import SourceVerificationEngine

    connection = connect(tmp_path / "row4-operational-down.db")
    source = {
        "name": "Row4OperationalDownSource",
        "base_url": "https://api.example.test/v1/jobs",
        "adapter": "json",
        "status": "active",
        "allow_hosts": ["api.example.test"],
        "policy_hosts": ["www.example.test"],
        "access_scope": "public",
        "terms_status": "needs_review",
    }
    engine = SourceVerificationEngine(connection, [source], search_provider=None, surface_scan_pages=1)

    def operational_fetch(name, url=None):
        raise RuntimeError("HTTPError: HTTP Error 403: Forbidden")

    def policy_fetch(name, url=None):
        if url == "https://www.example.test/terms-and-conditions":
            return {"body": b"<html><body>Terms of Service. These conditions apply to users.</body></html>",
                    "url": url, "status": 200, "bytes": 74, "sha256": "terms"}
        raise RuntimeError("not found")

    engine.http.fetch = operational_fetch
    engine.policy_http.fetch = policy_fetch
    result = engine._one(source["name"])

    assert result["source_verification_state"] == "DEAD"
    assert result["terms_status"] == "reviewed"
    assert result["terms_evidence_url"] == "https://www.example.test/terms-and-conditions"
    assert "operational API" not in result.get("error", "")
    connection.close()


def test_row4_policy_fetch_uses_html_accept_header(tmp_path):
    from marketradar.db import connect
    from marketradar.source_verification import SourceVerificationEngine

    connection = connect(tmp_path / "row4-policy-headers.db")
    source = {
        "name": "Row4PolicyHeaderSource",
        "base_url": "https://api.example.test/v1/jobs",
        "adapter": "json",
        "status": "active",
        "allow_hosts": ["api.example.test"],
        "policy_hosts": ["www.example.test"],
        "access_scope": "public",
        "terms_status": "needs_review",
    }
    engine = SourceVerificationEngine(connection, [source], search_provider=None, surface_scan_pages=1)
    headers = dict(engine.policy_http.sources[source["name"]].headers)
    assert headers["Accept"] == "text/html,application/xhtml+xml,text/plain,*/*"
    connection.close()


def test_row4_policy_host_is_separate_from_operational_host(tmp_path):
    from marketradar.db import connect
    from marketradar.source_verification import SourceVerificationEngine

    connection = connect(tmp_path / "row4-policy-host.db")
    source = {
        "name": "Row4PolicyHostSource",
        "base_url": "https://api.example.test/v1/jobs",
        "adapter": "json",
        "status": "active",
        "allow_hosts": ["api.example.test"],
        "policy_hosts": ["www.example.test"],
        "access_scope": "public",
        "terms_status": "needs_review",
        "execution_capability": "authorized_api",
    }
    engine = SourceVerificationEngine(connection, [source], search_provider=None, surface_scan_pages=1)
    seen = []

    def fake_operational_fetch(name, url=None):
        if url is not None:
            raise AssertionError("policy fetch must not use operational federation")
        return {"body": b"<html><body>Jobs</body></html>", "url": source["base_url"],
                "status": 200, "bytes": 32, "sha256": "home"}

    def fake_policy_fetch(name, url=None):
        seen.append(url)
        if url == "https://www.example.test/terms-and-conditions":
            return {"body": b"<html><body>Terms of Service. These conditions apply to users.</body></html>",
                    "url": url, "status": 200, "bytes": 74, "sha256": "terms"}
        raise RuntimeError("not found")

    engine.http.fetch = fake_operational_fetch
    engine.policy_http.fetch = fake_policy_fetch
    result = engine._one(source["name"])

    assert seen
    assert seen[0] == "https://www.example.test/terms-and-conditions"
    assert all("api.example.test" not in u for u in seen)
    assert result["terms_evidence_url"] == "https://www.example.test/terms-and-conditions"
    assert result["terms_status"] == "reviewed"
    connection.close()


def test_row4_active_source_review_warning_closes_when_policy_evidence_is_execution_ready(tmp_path):
    from marketradar.db import connect
    from marketradar.source_verification import SourceVerificationEngine

    connection = connect(tmp_path / "row4.db")
    source = {
        "name": "Row4TestSource",
        "base_url": "https://example.test",
        "adapter": "json",
        "status": "active",
        "allow_hosts": ["example.test"],
        "access_scope": "public",
        "terms_status": "needs_review",
        "execution_capability": "authorized_api",
    }
    engine = SourceVerificationEngine(connection, [source], search_provider=None)
    result = {
        "source": "Row4TestSource",
        "source_verification_state": "LIVE_CONFIRMED",
        "review_reason": "ACTIVE_SOURCE_TERMS_NOT_REVIEWED",
        "execution_ready": True,
        "terms_status": "reviewed",
        "evidence_urls": ["https://example.test/terms"],
        "last_verified_at": "2026-09-26T12:00:00+00:00",
        "source_constraints": [],
    }
    engine.persist([result])
    row = connection.execute(
        "SELECT status, resolution, evidence_url FROM source_review_queue WHERE source=?",
        ("Row4TestSource",),
    ).fetchone()
    assert row is not None
    assert row[0] == "RESOLVED"
    assert row[1] == "AUTOMATIC_POLICY_VERIFICATION"
    assert row[2] == "https://example.test/terms"
    connection.close()


def test_row4_default_privacy_policy_candidate_can_close_terms(tmp_path):
    from marketradar.db import connect
    from marketradar.source_verification import SourceVerificationEngine

    connection = connect(tmp_path / "row4-privacy-policy.db")
    source = {
        "name": "Row4PrivacyPolicySource",
        "base_url": "https://example.test/jobs",
        "adapter": "json",
        "status": "active",
        "allow_hosts": ["example.test"],
        "access_scope": "public",
        "terms_status": "needs_review",
    }
    engine = SourceVerificationEngine(connection, [source], search_provider=None, surface_scan_pages=7)
    seen = []

    def fake_fetch(name, url=None):
        if url is None:
            return {"body": b"<html><body>Jobs</body></html>", "url": source["base_url"],
                    "status": 200, "bytes": 32, "sha256": "home"}
        seen.append(url)
        if url == "https://example.test/privacy-policy":
            return {"body": b"<html><body>Privacy Policy and terms governing use of the service.</body></html>",
                    "url": url, "status": 200, "bytes": 86, "sha256": "privacy"}
        raise RuntimeError("not found")

    engine.http.fetch = fake_fetch
    engine.policy_http.fetch = fake_fetch
    result = engine._one(source["name"])

    assert "https://example.test/privacy-policy" in seen
    assert result["terms_evidence_url"] == "https://example.test/privacy-policy"
    assert result["terms_status"] == "reviewed"
    connection.close()

def test_row4_declared_policy_endpoint_counts_as_terms_evidence_without_terms_slug(tmp_path):
    from marketradar.db import connect
    from marketradar.source_verification import SourceVerificationEngine

    connection = connect(tmp_path / "row4-declared-policy-evidence.db")
    source = {
        "name": "Row4DeclaredPrivacyEndpointSource",
        "base_url": "https://example.test/jobs",
        "adapter": "json",
        "status": "active",
        "allow_hosts": ["example.test"],
        "access_scope": "public",
        "terms_status": "needs_review",
        "policy_paths": ["/article/detail-590"],
    }
    engine = SourceVerificationEngine(connection, [source], search_provider=None, surface_scan_pages=1)

    def fake_fetch(name, url=None):
        if url is None:
            return {"body": b"<html><body>Jobs</body></html>", "url": source["base_url"],
                    "status": 200, "bytes": 32, "sha256": "home"}
        if url == "https://example.test/article/detail-590":
            return {"body": b"<html><body>Privacy Statement. This policy governs personal data.</body></html>",
                    "url": url, "status": 200, "bytes": 88, "sha256": "policy"}
        raise RuntimeError("not found")

    engine.http.fetch = fake_fetch
    engine.policy_http.fetch = fake_fetch
    result = engine._one(source["name"])

    assert result["terms_evidence_url"] == "https://example.test/article/detail-590"
    assert result["terms_status"] == "reviewed"
    connection.close()

def test_row4_karlancer_registry_declares_official_policy_host_and_terms_path():
    import json
    from pathlib import Path
    rows = json.loads((Path(__file__).parents[1] / "config" / "sources.json").read_text(encoding="utf-8"))
    source = next(x for x in rows if x["name"] == "Karlancer_Iran")
    assert source["policy_hosts"] == ["www.karlancer.com"]
    assert source["policy_paths"] == ["https://www.karlancer.com/terms"]


def test_row4_policy_registry_uses_verified_official_endpoints():
    import json
    from pathlib import Path
    rows = json.loads((Path(__file__).parents[1] / 'config' / 'sources.json').read_text(encoding='utf-8'))
    expected = {
        'Bayt_MENA': 'https://www.bayt.com/en/pages/terms/',
        'CareerCross_Japan': 'https://www.careercross.com/en/article/detail-1697',
        'Daijob_Japan': 'https://www.daijob.com/en/top/terms',
        'GulfTalent': 'https://www.gulftalent.com/terms',
        'HiredChina': 'https://www.hiredchina.com/en/terms',
        'Naukrigulf': 'https://www.naukrigulf.com/terms-and-conditions',
        'TokyoDev': 'https://www.tokyodev.com/privacy-policy',
        'WeWorkRemotely': 'https://weworkremotely.com/terms-and-conditions',
    }
    by_name = {row['name']: row for row in rows}
    for name, url in expected.items():
        assert url in by_name[name].get('policy_paths', [])


def test_row4_policy_fallback_uses_proxy_stack_without_disabling_tls(tmp_path, monkeypatch):
    from marketradar.db import connect
    from marketradar.source_verification import SourceVerificationEngine
    import marketradar.source_verification as sv

    connection = connect(tmp_path / "row4-policy-fallback.db")
    source = {
        "name": "Row4FallbackSource",
        "base_url": "https://api.example.test/jobs",
        "adapter": "json",
        "status": "active",
        "allow_hosts": ["api.example.test"],
        "policy_hosts": ["www.example.test"],
        "access_scope": "public",
        "terms_status": "needs_review",
    }
    engine = SourceVerificationEngine(connection, [source], search_provider=None)

    class FakeResponse:
        status = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}
        def read(self, limit):
            return b"<html><body>Terms of Service</body></html>"
        def geturl(self):
            return "https://www.example.test/terms"
        def close(self):
            pass

    class FakeOpener:
        def open(self, request, timeout):
            assert request.full_url == "https://www.example.test/terms"
            assert request.get_header("User-agent")
            return FakeResponse()

    monkeypatch.setattr(sv.urllib.request, "build_opener", lambda *args: FakeOpener())
    result = engine._policy_fetch_fallback(source["name"], "https://www.example.test/terms")

    assert result["status"] == 200
    assert result["url"] == "https://www.example.test/terms"
    assert result["acquisition_provider"] == "policy-urlopen-fallback"
    connection.close()


def test_row4_policy_registry_includes_new_official_surfaces():
    import json
    from pathlib import Path
    rows = json.loads((Path(__file__).parents[1] / "config" / "sources.json").read_text(encoding="utf-8"))
    by_name = {row["name"]: row for row in rows}
    assert "https://tbilisi.headhunter.ge/terms" in by_name["Headhunter_GE"].get("policy_paths", [])
    assert "https://www.superjob.ru/info/hr_service.html" in by_name["SuperJob_Russia"].get("policy_paths", [])
    assert "https://s.zigbang.com/agree/user-agreement-last.html" in by_name["Zigbang_Jobs"].get("policy_paths", [])

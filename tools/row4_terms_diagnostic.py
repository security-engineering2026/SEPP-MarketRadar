from __future__ import annotations

import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    from marketradar.db import connect, sync_source_contracts
    from marketradar.source_registry import load_source_records
    from marketradar.source_search import WebSearchProvider
    from marketradar.source_verification import SourceVerificationEngine

    records = [
        x for x in load_source_records(ROOT / "config" / "sources.json")
        if str(x.get("status", "")).lower() == "active" and x.get("base_url")
    ]

    with tempfile.TemporaryDirectory(prefix="mr-row4-diagnostic-") as td:
        conn = connect(Path(td) / "qualification.db")
        sync_source_contracts(conn, records)
        engine = SourceVerificationEngine(
            conn,
            records,
            timeout=8,
            max_workers=16,
            max_policy_pages=3,
            surface_scan_pages=24,
            search_provider=WebSearchProvider(timeout=8),
        )
        results = engine.verify([x["name"] for x in records])
        conn.close()

    pending = [
        {
            "source": x.get("source"),
            "terms_status": x.get("terms_status"),
            "terms_evidence_url": x.get("terms_evidence_url"),
            "verified_terms_urls": x.get("verified_terms_urls", []),
            "evidence_urls": x.get("evidence_urls", []),
            "source_verification_state": x.get("source_verification_state"),
            "http_status": x.get("http_status"),
            "error": x.get("error"),
        }
        for x in results
        if str(x.get("terms_status", "")).lower() != "reviewed"
    ]

    print(json.dumps({
        "active_sources": len(records),
        "checked": len(results),
        "pending_count": len(pending),
        "pending_details": pending,
        "surface_scan_pages": 24,
        "max_workers": 16,
        "max_policy_pages": 3,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

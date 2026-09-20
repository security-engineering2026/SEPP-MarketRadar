"""MarketRadar orchestration facade: source lanes, scheduling, recommendation and product intelligence."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .capability_registry import load_provider_config, sync_provider_registry
from .db import connect, load_dynamic_source_records, sync_source_contracts
from .paths import app_root, data_root
from .recommendation_engine import daily_center
from .runtime import MarketRadarRuntime
from .source_registry import dedupe_source_records, load_source_records
from .source_verification import SourceVerificationEngine
from .source_search import WebSearchProvider
from .source_policy import EXECUTION_ELIGIBLE, MARKET_INTELLIGENCE_ONLY, BLACKLIST_ARCHIVE
from .logging_setup import close_logging

logger = logging.getLogger("marketradar")


class MarketRadar:
    def __init__(self, root=None):
        self.root = Path(root) if root else app_root()
        configured = load_source_records(self.root / "config" / "sources.json")
        self.conn = connect((self.root / 'data' / 'marketradar.db') if root else (data_root() / 'marketradar.db'))
        dynamic = load_dynamic_source_records(self.conn)
        merged = configured + [x for x in dynamic if x["name"] not in {r["name"] for r in configured}]
        self.sources, self.duplicates = dedupe_source_records(merged)
        sync_source_contracts(self.conn, self.sources)
        settings_path = self.root / "config" / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {
            'http_timeout': 10, 'default_profile': 'config/profile.example.json',
            'execution_blacklist_countries': ['Israel'], 'language': 'fa'
        }
        settings["profile"] = self._load_profile(settings)
        self.settings = settings
        provider_path = self.root / "config" / "capability_providers.json"
        load_provider_config(provider_path)
        sync_provider_registry(self.conn)
        self.runtime = MarketRadarRuntime(self.conn, self.sources, None, http_timeout=settings.get("http_timeout", 10), settings=settings)

    def _load_profile(self, settings: dict) -> dict:
        profile_path = data_root() / "profile.json"
        if profile_path.exists():
            try:
                data = json.loads(profile_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        default = self.root / settings.get("default_profile", "config/profile.example.json")
        if default.exists():
            try:
                data = json.loads(default.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {}

    def _due(self, source: dict, lane: str, now=None) -> bool:
        now = now or datetime.now(timezone.utc)
        interval = int(source.get("project_scan_interval_minutes", 60) if lane == EXECUTION_ELIGIBLE else source.get("intelligence_scan_interval_minutes", 720))
        row = self.conn.execute("SELECT last_project_scan_at,last_intelligence_scan_at FROM source_scan_state WHERE source=?", (source["name"],)).fetchone()
        if not row:
            return True
        stamp = row[0] if lane == "DAILY_PROJECT_SCAN" else row[1]
        if not stamp:
            return True
        try:
            return now >= datetime.fromisoformat(stamp) + timedelta(minutes=interval)
        except ValueError:
            return True

    def _mark_scan(self, source: dict, lane: str, status: str, error: str | None = None):
        now = datetime.now(timezone.utc).isoformat()
        if lane == EXECUTION_ELIGIBLE:
            self.conn.execute("INSERT INTO source_scan_state(source,last_project_scan_at,last_status,last_error,project_scan_count) VALUES(?,?,?,?,1) ON CONFLICT(source) DO UPDATE SET last_project_scan_at=excluded.last_project_scan_at,last_status=excluded.last_status,last_error=excluded.last_error,project_scan_count=source_scan_state.project_scan_count+1", (source["name"], now, status, error))
        else:
            self.conn.execute("INSERT INTO source_scan_state(source,last_intelligence_scan_at,last_status,last_error,intelligence_scan_count) VALUES(?,?,?,?,1) ON CONFLICT(source) DO UPDATE SET last_intelligence_scan_at=excluded.last_intelligence_scan_at,last_status=excluded.last_status,last_error=excluded.last_error,intelligence_scan_count=source_scan_state.intelligence_scan_count+1", (source["name"], now, status, error))
        self.conn.commit()

    def verify_sources(self, names=None):
        provider = WebSearchProvider(timeout=self.settings.get("http_timeout", 10))
        verifier = SourceVerificationEngine(self.conn, self.sources, timeout=self.settings.get("http_timeout", 10), max_workers=12, max_policy_pages=4, search_provider=provider)
        results = verifier.verify(names)
        verifier.persist(results)
        # Reload authoritative DB lane state for the next execution cycle.
        return results

    def verify_due_sources(self):
        days=int(self.settings.get('policy_search_interval_days',7) or 7)
        names=[]
        rows=self.conn.execute("SELECT name,source_lane,last_verified_at FROM sources WHERE COALESCE(source_lane,'REVIEW') <> 'BLACKLIST_ARCHIVE'").fetchall()
        from datetime import datetime,timezone,timedelta
        now=datetime.now(timezone.utc)
        for row in rows:
            stamp=row['last_verified_at']
            due=not stamp
            if stamp:
                try: due=now-datetime.fromisoformat(stamp.replace('Z','+00:00')) >= timedelta(days=days)
                except ValueError: due=True
            if due: names.append(row['name'])
        limit=int(self.settings.get('source_verification_batch_size',0) or 0)
        if limit>0: names=names[:limit]
        if not names: return []
        return self.verify_sources(names)

    def scan(self, mode="project", dry=False):
        lane = EXECUTION_ELIGIBLE if mode == "project" else MARKET_INTELLIGENCE_ONLY
        now = datetime.now(timezone.utc)
        stats = {"mode": mode, "sources_registered": len(self.sources), "unique_source_hosts": len(self.sources), "duplicates_archived": len(self.duplicates), "sources_checked": 0, "observations": 0, "errors": 0}
        for source in self.sources:
            source_state = self.conn.execute("SELECT source_lane,policy_lane,status FROM sources WHERE name=?", (source["name"],)).fetchone()
            effective_lane = (source_state["source_lane"] if source_state and source_state["source_lane"] else source.get("source_lane", "REVIEW")) if source_state else source.get("source_lane", "REVIEW")
            legacy_lane = source_state['policy_lane'] if source_state and source_state['policy_lane'] else source.get('policy_lane','REVIEW')
            lane_map={'DAILY_PROJECT_SCAN': EXECUTION_ELIGIBLE, 'GLOBAL_DISCOVERY': MARKET_INTELLIGENCE_ONLY, 'NEEDS_ANALYSIS': MARKET_INTELLIGENCE_ONLY, 'BLOCKED_IRAN': MARKET_INTELLIGENCE_ONLY}
            effective_lane = lane_map.get(legacy_lane, effective_lane) if legacy_lane in lane_map else lane_map.get(effective_lane, effective_lane)
            if effective_lane == BLACKLIST_ARCHIVE or effective_lane != lane or not self._due(source, lane, now):
                continue
            if lane == EXECUTION_ELIGIBLE and source_state and source_state["status"] != "active":
                continue
            stats["sources_checked"] += 1
            try:
                result = self.runtime.federate(source["name"], dry=dry, force=True)
                stats["observations"] += int(result.get("observations", 0))
                self._mark_scan(source, lane, "OK")
            except Exception as exc:
                logger.exception("MarketRadar scan failed for %s", source["name"])
                stats["errors"] += 1
                self._mark_scan(source, lane, "ERROR", type(exc).__name__ + ": " + str(exc))
        return stats

    def daily_center(self):
        center = daily_center(self.conn, self.settings.get("profile"))
        report = self.root / "reports" / "PRODUCT_BUILD_SPECS.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(center.get("product_opportunities", []), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        pool = self.root / "reports" / "SOURCE_POOL_STATUS.json"
        lanes = {str(r[0] or "UNKNOWN"): int(r[1]) for r in self.conn.execute("SELECT source_lane,COUNT(*) FROM sources GROUP BY source_lane").fetchall()}
        pool.write_text(json.dumps({"registered": self.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0], "unique_hosts": self.conn.execute("SELECT COUNT(DISTINCT lower(replace(replace(base_url,'https://',''),'http://',''))) FROM sources WHERE base_url IS NOT NULL").fetchone()[0], "lanes": lanes}, ensure_ascii=False, indent=2), encoding="utf-8")
        return center

    def actions(self):
        return self.runtime.pipeline.actions()

    def close(self):
        try:
            self.conn.close()
        finally:
            close_logging()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

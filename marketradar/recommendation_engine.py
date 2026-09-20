from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Iterable

from .capability_registry import load_provider_config, match_task

DOMAIN_LABELS_FA = {
    "python": "پایتون",
    "android": "اندروید",
    "web_bug_bounty": "باگ‌بانتی وب",
    "android_bug_bounty": "باگ‌بانتی اندروید",
    "services": "خدمات عمومی",
}

DOMAIN_TASKS = {
    "python": {"python_automation", "python_debugging", "api_integration", "business_automation", "data_pipeline"},
    "android": {"android_development"},
    "web_bug_bounty": {"web_bug_bounty"},
    "android_bug_bounty": {"android_bug_bounty"},
    "services": {"pdf_to_word", "pdf_to_excel", "image_to_word", "image_to_text", "audio_to_text", "translation", "word_formatting", "word_to_powerpoint", "pdf_to_powerpoint", "excel_cleaning", "excel_automation", "data_entry", "ocr", "powerpoint"},
}

DEFAULT_DOMAINS = tuple(DOMAIN_TASKS)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def profile_domains(profile: dict | None) -> dict:
    profile = profile or {}
    domains = profile.get("domains") if isinstance(profile.get("domains"), dict) else {}
    out = {}
    for domain in DEFAULT_DOMAINS:
        item = domains.get(domain) if isinstance(domains.get(domain), dict) else {}
        learning = item.get("learning") if isinstance(item.get("learning"), dict) else {}
        out[domain] = {
            "enabled": bool(item.get("enabled", True if domain in {"python", "android"} else False)),
            "level": max(1, min(5, int(item.get("level", learning.get("level", 2)) or 2))),
            "course_day": int(item.get("course_day", 0) or 0),
            "course_total_days": int(item.get("course_total_days", 504) or 504),
            "stretch": bool(item.get("stretch", False)),
            "skills": [str(x).lower() for x in item.get("skills", [])],
        }
    selected = profile.get("selected_domains")
    if isinstance(selected, list):
        selected_set = {str(x) for x in selected}
        for domain in out:
            out[domain]["enabled"] = domain in selected_set
    return out


def domain_for_task(task_type: str) -> str:
    for domain, task_types in DOMAIN_TASKS.items():
        if task_type in task_types:
            return domain
    return "services"


def _opportunity_score(row: dict) -> float:
    try:
        return float(row.get("rank_score") or row.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _suitable(row: dict, profile_domain: dict) -> tuple[bool, str]:
    difficulty = int(row.get("difficulty_score") or row.get("recommended_level") or 3)
    level = int(profile_domain.get("level", 2))
    stretch = bool(profile_domain.get("stretch", False))
    max_level = level + (1 if stretch else 0)
    if difficulty > max_level:
        return False, f"سطح پروژه {difficulty} از سطح فعلی {level} بالاتر است"
    return True, "سطح پروژه با سطح فعلی هم‌خوان است"


def _automation(row: dict) -> dict:
    status = str(row.get("automation_status") or "MANUAL_OR_UNKNOWN")
    provider_ids = []
    try:
        provider_ids = json.loads(row.get("automation_provider_ids_json") or "[]")
    except Exception:
        pass
    labels = {
        "AUTO_AVAILABLE": "اجرای خودکار آماده",
        "ENGINE_NOT_READY": "Engine هنوز برای اجرا آماده نیست",
        "MANUAL_OR_BUILD": "فعلاً دستی؛ ساخت Engine می‌تواند پیشنهاد شود",
        "MANUAL_OR_UNKNOWN": "فعلاً دستی / نیازمند بررسی",
    }
    return {
        "status": status,
        "status_label_fa": labels.get(status, "فعلاً دستی / نیازمند بررسی"),
        "manual_possible": True,
        "provider_ids": provider_ids,
    }


def _reason(row: dict, domain_label: str, fit_reason: str) -> dict:
    return {
        "domain_label_fa": domain_label,
        "fit_reason_fa": fit_reason,
        "rank_score": _opportunity_score(row),
        "evidence_confidence": float(row.get("evidence_confidence") or 0),
        "time_to_money": row.get("time_to_money"),
        "automation_status": _automation(row),
    }


def _eligible_rows(connection) -> list[dict]:
    rows = connection.execute(
        """
        SELECT o.*, s.source_lane, s.iran_eligibility AS source_iran_eligibility
        FROM opportunities o
        LEFT JOIN sources s ON s.name=o.source
        WHERE COALESCE(o.blacklist_reason,'')=''
          AND COALESCE(s.source_lane,'DAILY_PROJECT_SCAN') = 'DAILY_PROJECT_SCAN'
          AND COALESCE(s.source_lane,'DAILY_PROJECT_SCAN') <> 'BLACKLIST_ARCHIVE'
          AND COALESCE(o.opportunity_type,'OPPORTUNITY') NOT IN ('NAVIGATION','TAXONOMY','INFORMATIONAL')
          AND o.eligibility IN ('EXECUTE','REVIEW')
          AND o.state='DISCOVERED'
        """
    ).fetchall()
    out=[]
    for x in rows:
        source=x['source']
        lim=connection.execute('SELECT max_open_projects,max_pending_applications FROM source_application_limits WHERE source=?',(source,)).fetchone()
        if lim:
            open_count=connection.execute("SELECT COUNT(*) n FROM opportunities WHERE source=? AND state IN ('ACCEPTED','IN_PROGRESS')",(source,)).fetchone()['n']
            pending_count=connection.execute("SELECT COUNT(*) n FROM opportunities WHERE source=? AND state IN ('APPROVAL_PENDING','SUBMITTED','VIEWED','MESSAGE_RECEIVED','NEGOTIATION')",(source,)).fetchone()['n']
            if lim['max_open_projects'] is not None and open_count >= lim['max_open_projects']:
                continue
            if lim['max_pending_applications'] is not None and pending_count >= lim['max_pending_applications']:
                continue
        out.append(dict(x))
    return out


def recommend(connection, profile: dict | None, now: str | None = None) -> dict:
    now = now or _now()
    domains = profile_domains(profile)
    rows = _eligible_rows(connection)
    per_domain = defaultdict(list)

    for row in rows:
        domain = row.get("recommendation_domain") or domain_for_task(str(row.get("task_type") or ""))
        if domain not in domains or not domains[domain]["enabled"]:
            continue
        ok, reason = _suitable(row, domains[domain])
        if ok:
            per_domain[domain].append((row, reason))

    result = {"generated_at": now, "domains": {}, "top7": []}
    candidates = []
    for domain, items in per_domain.items():
        items.sort(key=lambda x: (_opportunity_score(x[0]), float(x[0].get("evidence_confidence") or 0)), reverse=True)
        picked = items[:3]
        result["domains"][domain] = {
            "label_fa": DOMAIN_LABELS_FA[domain],
            "count": len(items),
            "recommendations": [],
        }
        for rank, (row, reason) in enumerate(picked, 1):
            automation = _automation(row)
            recommendation = {
                "opportunity_id": row["id"],
                "title": row["title"],
                "task_type": row.get("task_type"),
                "work_domain": row.get("work_domain"),
                "budget": row.get("budget"),
                "currency": row.get("currency"),
                "source": row.get("source"),
                "rank": rank,
                "reason": _reason(row, DOMAIN_LABELS_FA[domain], reason),
                "automation": automation,
            }
            result["domains"][domain]["recommendations"].append(recommendation)
            candidates.append((row, domain, reason))

    candidates.sort(key=lambda x: (_opportunity_score(x[0]), float(x[0].get("evidence_confidence") or 0)), reverse=True)
    for rank, (row, domain, reason) in enumerate(candidates[:7], 1):
        item = {
            "opportunity_id": row["id"],
            "title": row["title"],
            "domain": domain,
            "domain_label_fa": DOMAIN_LABELS_FA[domain],
            "rank": rank,
            "reason": _reason(row, DOMAIN_LABELS_FA[domain], reason),
            "automation": _automation(row),
        }
        result["top7"].append(item)

    _persist(connection, result)
    return result


def _persist(connection, result: dict) -> None:
    generated_at = result["generated_at"]
    connection.execute("DELETE FROM daily_recommendations")
    for item in result["top7"]:
        connection.execute(
            "INSERT INTO daily_recommendations(generated_at,domain,opportunity_id,rank,scope,visible_default,reason_json,automation_status,suitability_status) VALUES(?,?,?,?,?,?,?,?,?)",
            (generated_at, item["domain"], item["opportunity_id"], item["rank"], "TOP7", 1 if item["rank"] <= 3 else 0, json.dumps(item["reason"], ensure_ascii=False), item["automation"]["status"], "SUITABLE"),
        )
    for domain, payload in result["domains"].items():
        for item in payload["recommendations"]:
            connection.execute(
                "INSERT INTO daily_recommendations(generated_at,domain,opportunity_id,rank,scope,visible_default,reason_json,automation_status,suitability_status) VALUES(?,?,?,?,?,?,?,?,?)",
                (generated_at, domain, item["opportunity_id"], item["rank"], "DOMAIN", 1, json.dumps(item["reason"], ensure_ascii=False), item["automation"]["status"], "SUITABLE"),
            )
    connection.commit()


def generate_product_build_specs(connection) -> list[dict]:
    rows = connection.execute(
        """
        SELECT o.*, s.source_lane
        FROM opportunities o JOIN sources s ON s.name=o.source
        WHERE s.source_lane='MARKET_INTELLIGENCE_ONLY'
          AND COALESCE(o.blacklist_reason,'')=''
          AND COALESCE(o.opportunity_type,'OPPORTUNITY') NOT IN ('NAVIGATION','TAXONOMY','INFORMATIONAL')
        """
    ).fetchall()

    def family(row):
        task = str(row.get('task_type') or '')
        domain = str(row.get('work_domain') or '')
        if task in {'web_bug_bounty'}:
            return 'web_bug_bounty_engine'
        if task in {'android_bug_bounty'}:
            return 'android_bug_bounty_engine'
        if task in {'python_automation','python_debugging','api_integration','business_automation','data_pipeline'}:
            return 'python_automation_engine'
        if domain in {'document_processing','presentation','language_services','media_processing','data_processing'}:
            return 'student_services_engine'
        return domain or 'general_software_engine'

    grouped = defaultdict(list)
    for r in rows:
        grouped[family(dict(r))].append(dict(r))

    names = {
        'student_services_engine': 'Student / Office / Document Services Engine',
        'python_automation_engine': 'Python Automation Engine',
        'web_bug_bounty_engine': 'Web Bug Bounty Engine',
        'android_bug_bounty_engine': 'Android Bug Bounty Engine',
        'general_software_engine': 'General Software Automation Engine',
    }

    specs = []
    for product_key, items in grouped.items():
        task_types = sorted({str(x.get('task_type')) for x in items if x.get('task_type')})
        outputs = set()
        capabilities = set()
        requirements = set()
        source_urls = set()
        for item in items:
            try:
                outputs.update(json.loads(item.get('output_formats_json') or '[]'))
            except Exception:
                pass
            if item.get('task_type'):
                capabilities.add(item['task_type'])
            try:
                requirements.update(json.loads(item.get('requirements_json') or '[]'))
            except Exception:
                pass
            source_urls.add(str(item.get('url') or ''))
        demand_score = min(1.0, len(items) / 20.0)
        spec = {
            'product_key': product_key,
            'product_name': names.get(product_key, f'{product_key}'),
            'demand_score': round(demand_score, 3),
            'opportunity_count': len(items),
            'task_count': len(task_types),
            'output_count': len(outputs),
            'suggested_capabilities': task_types,
            'requirements': sorted(requirements),
            'source_evidence': {'sources': sorted({x['source'] for x in items})[:50], 'sample_urls': sorted(x for x in source_urls if x)[:30], 'sample_opportunities': [x['id'] for x in items[:30]]},
            'business_models': ['LICENSE', 'SUBSCRIPTION', 'API', 'SERVICE'],
            'status': 'PROPOSED',
        }
        specs.append(spec)

    connection.execute('DELETE FROM product_build_specs')
    for spec in specs:
        connection.execute(
            'INSERT INTO product_build_specs(generated_at,product_key,product_name,demand_score,opportunity_count,task_count,output_count,suggested_capabilities_json,requirements_json,source_evidence_json,business_models_json,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (_now(), spec['product_key'], spec['product_name'], spec['demand_score'], spec['opportunity_count'], spec['task_count'], spec['output_count'], json.dumps(spec['suggested_capabilities'], ensure_ascii=False), json.dumps(spec['requirements'], ensure_ascii=False), json.dumps(spec['source_evidence'], ensure_ascii=False), json.dumps(spec['business_models'], ensure_ascii=False), spec['status']),
        )
    connection.commit()
    return specs

def daily_center(connection, profile: dict | None) -> dict:
    recommendations = recommend(connection, profile)
    product_specs = generate_product_build_specs(connection)
    recommendations["product_opportunities"] = product_specs
    return recommendations

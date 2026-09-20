from __future__ import annotations
import re
from datetime import datetime, timezone


def _num(value: str):
    try:
        return int(value.replace(',', '').strip())
    except Exception:
        return None


def extract_source_constraints(text: str, evidence_urls: list[str] | None = None) -> list[dict]:
    """Extract explicit platform/account constraints from first-party text.

    This is evidence extraction, not a hard-coded platform rule. Unknown means
    unresolved and is routed to review/support rather than treated as unlimited.
    """
    evidence_urls = evidence_urls or []
    low = text.lower()
    found: dict[str, dict] = {}

    patterns = [
        ('max_open_projects', r'(?:only|maximum|max\.?|up to)\s*(\d+)\s*(?:open\s+projects?|active\s+projects?)'),
        ('max_pending_applications', r'(?:only|maximum|max\.?|up to)\s*(\d+)\s*(?:pending\s+applications?|active\s+proposals?|open\s+proposals?)'),
        ('max_pending_applications', r'(?:one|1)\s+(?:active|open)\s+(?:proposal|application)\s+(?:at\s+a\s+time|simultaneously)'),
        ('max_open_projects', r'(?:only\s+)?(?:one|1)\s+(?:open|active)\s+project(?:s)?(?:\s+(?:at\s+a\s+time|simultaneously))?'),
        ('max_pending_applications', r'(?:فقط|حداکثر)\s*(\d+)\s*(?:درخواست|پیشنهاد)\s*(?:فعال|همزمان)'),
        ('max_open_projects', r'(?:فقط|حداکثر)\s*(\d+)\s*(?:پروژه)\s*(?:باز|فعال|همزمان)'),
    ]
    for key, pattern in patterns:
        m = re.search(pattern, low, re.I | re.S)
        if not m:
            continue
        raw = m.group(1) if m.lastindex else '1'
        value = 1 if raw in {'one'} else _num(raw)
        if value is None:
            continue
        found[key] = {'key': key, 'value_int': value, 'value_text': m.group(0)[:300], 'confidence': 0.95}

    # Explicit commercial constraints are useful intelligence even when they do
    # not directly gate submission. Preserve the text for later economic ranking.
    commercial = [
        ('subscription_fee', r'(?:membership|subscription|plan|عضویت|اشتراک).{0,140}(?:(?:\$|€|£|تومان|ریال)\s*[\d,.]+|[\d,.]+\s*(?:usd|eur|gbp|irr|تومان|ریال))'),
        ('commission', r'(?:commission|service\s+fee|کارمزد).{0,100}(?:\d+(?:\.\d+)?\s*%)'),
        ('proposal_fee', r'(?:proposal|bid|application|درخواست|پیشنهاد).{0,100}(?:fee|cost|هزینه|کارمزد).{0,80}(?:\$|€|£|تومان|ریال)?\s*[\d,.]+'),
    ]
    for key, pattern in commercial:
        m = re.search(pattern, low, re.I | re.S)
        if m and key not in found:
            found[key] = {'key': key, 'value_int': None, 'value_text': m.group(0)[:400], 'confidence': 0.80}

    for item in found.values():
        item['evidence_url'] = evidence_urls[0] if evidence_urls else None
        item['checked_at'] = datetime.now(timezone.utc).isoformat()
        item['status'] = 'CONFIRMED'
    return list(found.values())


def support_question_for_source(country: str | None, iran_eligibility: str, kyc_requirement: str, constraints: list[dict]) -> str | None:
    if str(country or '').lower() == 'iran':
        if iran_eligibility == 'UNKNOWN':
            return 'آیا کاربران و پیمانکاران ایرانی امکان ثبت‌نام، دریافت پروژه و دریافت وجه در این پلتفرم را دارند؟'
        if not constraints:
            return 'آیا محدودیت اشتراک، تعداد پیشنهاد هم‌زمان، پروژه باز، کارمزد یا شرایط خاص حساب وجود دارد؟'
    if kyc_requirement == 'REQUIRED':
        return 'آیا احراز هویت موردنیاز برای کاربر مقیم ایران قابل انجام و از نظر پرداخت قابل استفاده است؟'
    return None

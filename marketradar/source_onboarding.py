from __future__ import annotations
import re
from dataclasses import dataclass
from urllib.parse import urlparse
from .adapter_registry import supported

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
ALLOWED_STATUS = {"active", "candidate", "disabled"}
ALLOWED_VERIFICATION = {"unverified", "documented", "verified", "degraded", "blocked"}
ALLOWED_ACQUISITION = {"http", "rss", "api", "telegram_api", "linkedin_api", "x_api", "reddit_api", "authorized_integration", "manual"}
ALLOWED_TERMS = {"not_reviewed", "needs_review", "reviewed", "allowed", "n/a", "blocked"}
ALLOWED_ACCESS_SCOPES = {"public", "local", "authorized", "private"}
ALLOWED_POLICY_LANES = {"DAILY_PROJECT_SCAN", "GLOBAL_DISCOVERY", "MARKET_INTELLIGENCE_ONLY", "NEEDS_ANALYSIS", "BLOCKED_IRAN", "REVIEW"}
ALLOWED_SOURCE_VERIFICATION = {"DISCOVERED", "LIVE_CONFIRMED", "DEAD", "LOW_QUALITY", "STALE"}
ALLOWED_IRAN_ELIGIBILITY = {"ALLOW", "BLOCK", "UNKNOWN", "OPPORTUNITY_ONLY"}
ALLOWED_KYC = {"NOT_REQUIRED", "REQUIRED", "UNKNOWN"}
RUNTIME_ACQUISITION_FAMILIES = {"http", "rss", "api"}
PLACEHOLDER_HOSTS = {"example.com", "example.org", "example.net", "localhost", "127.0.0.1"}

@dataclass(frozen=True)
class OnboardingResult:
    name: str
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def validate_source(record: dict) -> OnboardingResult:
    errors, warnings = [], []
    if not isinstance(record, dict):
        return OnboardingResult("<invalid>", False, ("SOURCE_RECORD_INVALID",), ())
    name = str(record.get("name", "<missing>"))
    if not isinstance(record.get("name"), str) or not NAME_RE.fullmatch(record["name"]):
        errors.append("SOURCE_NAME_INVALID")
    base = record.get("base_url")
    if not isinstance(base, str):
        errors.append("SOURCE_BASE_URL_INVALID")
        parsed = None
    else:
        parsed = urlparse(base)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            errors.append("SOURCE_BASE_URL_INVALID")
    hosts = record.get("allow_hosts")
    if not isinstance(hosts, list) or not hosts or any(not isinstance(h, str) or not h.strip() for h in hosts):
        errors.append("SOURCE_ALLOW_HOSTS_REQUIRED")
        hosts = []
    if parsed and parsed.hostname and parsed.hostname.lower().rstrip(".") not in {h.lower().rstrip(".") for h in hosts}:
        errors.append("SOURCE_BASE_HOST_NOT_ALLOWED")
    status = record.get("status", "candidate")
    verification = record.get("verification_state", "unverified")
    acquisition = record.get("acquisition", "http")
    adapter = record.get("adapter", "json")
    terms = record.get("terms_status", "not_reviewed")
    access_scope = record.get("access_scope", "public")
    policy_lane = record.get("policy_lane", "REVIEW")
    source_verification_state = str(record.get('source_verification_state','DISCOVERED')).upper()
    iran_eligibility = str(record.get('iran_eligibility', record.get('iran_status','UNKNOWN'))).upper()
    kyc_requirement = str(record.get('kyc_requirement','UNKNOWN')).upper()
    if status not in ALLOWED_STATUS: errors.append("SOURCE_STATUS_INVALID")
    if verification not in ALLOWED_VERIFICATION: errors.append("SOURCE_VERIFICATION_INVALID")
    if acquisition not in ALLOWED_ACQUISITION: errors.append("SOURCE_ACQUISITION_INVALID")
    if terms not in ALLOWED_TERMS: errors.append("SOURCE_TERMS_STATUS_INVALID")
    if access_scope not in ALLOWED_ACCESS_SCOPES: errors.append("SOURCE_ACCESS_SCOPE_INVALID")
    if policy_lane not in ALLOWED_POLICY_LANES: errors.append("SOURCE_POLICY_LANE_INVALID")
    if source_verification_state not in ALLOWED_SOURCE_VERIFICATION: errors.append('SOURCE_VERIFICATION_STATE_INVALID')
    if iran_eligibility not in ALLOWED_IRAN_ELIGIBILITY: errors.append('SOURCE_IRAN_ELIGIBILITY_INVALID')
    if kyc_requirement not in ALLOWED_KYC: errors.append('SOURCE_KYC_REQUIREMENT_INVALID')
    if not supported(adapter): errors.append("SOURCE_ADAPTER_UNSUPPORTED")
    if acquisition == "rss" and adapter != "rss": warnings.append("ACQUISITION_ADAPTER_MISMATCH")
    if acquisition in {"telegram_api", "linkedin_api", "x_api", "reddit_api", "authorized_integration"} and record.get("access_scope") not in {"authorized", "private", "public"}:
        errors.append("SOURCE_ACCESS_SCOPE_INVALID")
    if status == "active" and verification == "unverified":
        errors.append("ACTIVE_SOURCE_MUST_NOT_BE_UNVERIFIED")
    if status == "active" and verification == "blocked":
        errors.append("ACTIVE_SOURCE_MUST_NOT_BE_BLOCKED")
    if status == "active" and terms == "blocked":
        errors.append("ACTIVE_SOURCE_TERMS_BLOCKED")
    if status == "active" and policy_lane == "DAILY_PROJECT_SCAN" and str(record.get('iran_status','UNKNOWN')).upper() != 'ALLOW':
        errors.append("ACTIVE_DAILY_SOURCE_REQUIRES_IRAN_ALLOW")
    if policy_lane == 'BLOCKED_IRAN' and iran_eligibility != 'BLOCK':
        errors.append('BLOCKED_LANE_REQUIRES_IRAN_BLOCK')
    if policy_lane == 'MARKET_INTELLIGENCE_ONLY' and iran_eligibility not in {'BLOCK','OPPORTUNITY_ONLY','UNKNOWN'}:
        errors.append('MARKET_INTELLIGENCE_LANE_POLICY_MISMATCH')
    if policy_lane == "DAILY_PROJECT_SCAN" and not bool(record.get('daily_scan')):
        errors.append("DAILY_LANE_REQUIRES_DAILY_SCAN")
    if str(record.get('iran_status','UNKNOWN')).upper() in {'ALLOW','BLOCK'} and not record.get('iran_policy_basis'):
        warnings.append("IRAN_POLICY_BASIS_MISSING")
    if status == "active" and acquisition not in RUNTIME_ACQUISITION_FAMILIES:
        errors.append("ACTIVE_SOURCE_ACQUISITION_UNSUPPORTED")
    if parsed and parsed.hostname and parsed.hostname.lower().rstrip(".") in PLACEHOLDER_HOSTS:
        warnings.append("PLACEHOLDER_OR_LOCAL_HOST")
    if status == "active" and terms not in {"reviewed", "allowed", "n/a"}:
        warnings.append("ACTIVE_SOURCE_TERMS_NOT_REVIEWED")
    if status == "active" and not record.get("verification_basis"):
        warnings.append("VERIFICATION_BASIS_MISSING")
    evidence_urls = [record.get(k) for k in ('iran_policy_url','kyc_evidence_url','payout_evidence_url','terms_evidence_url') if record.get(k)]
    if status == 'active' and not evidence_urls:
        warnings.append('SOURCE_EVIDENCE_URLS_MISSING')
    if source_verification_state == 'LIVE_CONFIRMED' and not record.get('last_verified_at'):
        warnings.append('LIVE_CONFIRMATION_DATE_MISSING')
    return OnboardingResult(name, not errors, tuple(errors), tuple(warnings))


def audit_registry(records: list[dict]) -> dict:
    results = [validate_source(x) for x in records]
    record_by_name = {str(x.get("name")): x for x in records if isinstance(x, dict)}
    promotable = []
    for r in results:
        x = record_by_name.get(r.name, {})
        # "Promotable" means eligible for runtime promotion, not merely schema-valid.
        # Never advertise explicitly blocked, stale/dead/low-quality, or policy-unknown
        # sources as promotable.
        if not r.ok or r.warnings:
            continue
        if str(x.get("policy_lane", "REVIEW")) == "BLOCKED_IRAN":
            continue
        if str(x.get("iran_eligibility", x.get("iran_status", "UNKNOWN"))).upper() == "BLOCK":
            continue
        if str(x.get("source_verification_state", "DISCOVERED")).upper() not in {"LIVE_CONFIRMED"}:
            continue
        if str(x.get("verification_state", "unverified")) != "verified":
            continue
        promotable.append(r.name)
    return {
        "total": len(results),
        "valid": sum(r.ok for r in results),
        "invalid": sum(not r.ok for r in results),
        "warnings": sum(bool(r.warnings) for r in results),
        "results": results,
        "promotable": promotable,
    }

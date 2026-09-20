from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from .country_policy import jurisdiction_hits, normalize_country

EXECUTION_ELIGIBLE = "EXECUTION_ELIGIBLE"
MARKET_INTELLIGENCE_ONLY = "MARKET_INTELLIGENCE_ONLY"
BLACKLIST_ARCHIVE = "BLACKLIST_ARCHIVE"
REVIEW_LANE = "REVIEW"
# Backward-compatible aliases retained for older database/tests.
EXECUTION_LANE = EXECUTION_ELIGIBLE
INTELLIGENCE_LANE = MARKET_INTELLIGENCE_ONLY
BLACKLIST_LANE = BLACKLIST_ARCHIVE

LANE_LABELS_FA = {
    EXECUTION_ELIGIBLE: "منبع مناسب اجرای پروژه",
    MARKET_INTELLIGENCE_ONLY: "منبع تحلیل بازار",
    BLACKLIST_ARCHIVE: "آرشیو سیاه",
    REVIEW_LANE: "نیازمند بررسی",
}

CRYPTO_ASSETS = {"BTC", "ETH", "USDT", "USDC", "TRX", "DAI"}


@dataclass(frozen=True)
class SourceClassification:
    lane: str
    lane_label_fa: str
    execution_ready: bool
    blacklisted: bool
    reason: str
    interval_minutes: int


def _host(base_url: str | None) -> str:
    try:
        return (urlparse(str(base_url or "")).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def source_is_domestic(record: dict) -> bool:
    country = normalize_country(record.get("country"))
    region = normalize_country(record.get("region"))
    return country == "Iran" or region == "Iran"


def source_has_crypto_payment(record: dict, evidence: dict | None = None) -> bool:
    evidence = evidence or record
    caps = evidence.get("payment_capabilities") or []
    if isinstance(caps, str):
        caps = [caps]
    caps = {str(x).upper() for x in caps}
    if caps & CRYPTO_ASSETS:
        return True
    for key in ("payment_status", "payment", "currency"):
        value = str(record.get(key) or "").upper()
        if value in CRYPTO_ASSETS or any(asset in value for asset in CRYPTO_ASSETS):
            return True
    return False


def classify_source_lane(
    record: dict,
    evidence: dict | None = None,
    blocked_countries: list[str] | tuple[str, ...] = ("Israel",),
) -> SourceClassification:
    evidence = evidence or record
    blocked_hits = jurisdiction_hits(record, record, blocked_countries)
    host = _host(record.get("base_url"))
    if "Israel" not in blocked_hits and (host.endswith(".il") or host.endswith(".co.il")):
        blocked_hits = [*blocked_hits, "Israel"]

    if blocked_hits:
        return SourceClassification(
            BLACKLIST_LANE,
            LANE_LABELS_FA[BLACKLIST_LANE],
            False,
            True,
            "EXPLICIT_BLOCKED_OPERATIONAL_JURISDICTION",
            0,
        )

    access_scope = str(record.get("access_scope") or "public").lower()
    evidence_conf = float(evidence.get("evidence_confidence") or 0)
    iran = str(evidence.get("iran_eligibility") or record.get("iran_status") or "UNKNOWN").upper()
    kyc = str(evidence.get("kyc_requirement") or record.get("kyc_requirement") or "UNKNOWN").upper()
    crypto = source_has_crypto_payment(record, evidence)

    if source_is_domestic(record):
        # Domestic Iranian work can use local KYC/payment rules. We require evidence
        # of source viability, but do not reject merely because domestic KYC exists.
        ready = evidence_conf >= 0.85 and access_scope in {"public", "authorized"}
        return SourceClassification(
            EXECUTION_LANE if ready else REVIEW_LANE,
            LANE_LABELS_FA[EXECUTION_LANE if ready else REVIEW_LANE],
            ready,
            False,
            "IRAN_DOMESTIC_SOURCE" if ready else "INCOMPLETE_DOMESTIC_EVIDENCE",
            60 if ready else 720,
        )

    # Foreign execution is evidence-gated. Crypto is useful/preferred for many
    # cases but must not be conflated with KYC or Iran eligibility. Payment may be
    # fiat/platform payout, bank transfer, or another documented settlement rail.
    usable_payment = bool(evidence.get("payment_capabilities") or record.get("payment_status") or record.get("payment"))
    if iran == "ALLOW" and kyc == "NOT_REQUIRED" and usable_payment and evidence_conf >= 0.85 and access_scope in {"public", "authorized"}:
        return SourceClassification(
            EXECUTION_ELIGIBLE,
            LANE_LABELS_FA[EXECUTION_ELIGIBLE],
            True,
            False,
            "FOREIGN_IRAN_COMPATIBLE_EVIDENCE_GATED",
            60,
        )

    return SourceClassification(
        MARKET_INTELLIGENCE_ONLY,
        LANE_LABELS_FA[MARKET_INTELLIGENCE_ONLY],
        False,
        False,
        "FOREIGN_SOURCE_NOT_EXECUTION_ELIGIBLE_BUT_VALID_FOR_MARKET_INTELLIGENCE",
        720,
    )


def classify_opportunity_blacklist(item: dict, source: dict, blocked_countries=("Israel",)) -> tuple[bool, list[str]]:
    hits = jurisdiction_hits(item, source, blocked_countries)
    return bool(hits), hits

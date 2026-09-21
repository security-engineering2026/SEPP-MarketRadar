from __future__ import annotations

"""Capability-aware access planning for restricted platforms.

This module never bypasses platform controls. It turns an inaccessible surface
into an actionable connector requirement and keeps discovery usable through
public/indexed evidence.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import urlparse


class AccessMode(str, Enum):
    PUBLIC_INDEX = "PUBLIC_INDEX"
    USER_AUTHORIZED = "USER_AUTHORIZED"
    OFFICIAL_API = "OFFICIAL_API"
    APPROVED_CRAWL = "APPROVED_CRAWL"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class AccessPlan:
    platform: str
    host: str
    mode: AccessMode
    required_action: str
    scope: str
    execution_allowed: bool = False
    bulk_collection_allowed: bool = False


PLATFORM_POLICIES = {
    "linkedin": {
        "hosts": {"linkedin.com", "www.linkedin.com"},
        "modes": (AccessMode.PUBLIC_INDEX, AccessMode.USER_AUTHORIZED, AccessMode.OFFICIAL_API, AccessMode.APPROVED_CRAWL),
        "action": "Connect an approved LinkedIn app/API or request explicit crawl permission; membership alone is not crawl permission.",
    },
    "telegram": {
        "hosts": {"t.me", "telegram.me", "telegram.org"},
        "modes": (AccessMode.PUBLIC_INDEX, AccessMode.USER_AUTHORIZED, AccessMode.OFFICIAL_API),
        "action": "Connect Telegram through an authorized bot/API use-case and select the channel/group scope; do not bulk-harvest public content.",
    },
    "instagram": {
        "hosts": {"instagram.com", "www.instagram.com"},
        "modes": (AccessMode.PUBLIC_INDEX, AccessMode.USER_AUTHORIZED, AccessMode.OFFICIAL_API),
        "action": "Use public/index evidence or an approved Meta/Instagram API integration with the user's authorized scope.",
    },
    "facebook": {
        "hosts": {"facebook.com", "www.facebook.com"},
        "modes": (AccessMode.PUBLIC_INDEX, AccessMode.USER_AUTHORIZED, AccessMode.OFFICIAL_API),
        "action": "Use public/index evidence or an approved Meta API integration with the user's authorized scope.",
    },
    "x": {
        "hosts": {"x.com", "www.x.com", "twitter.com", "www.twitter.com"},
        "modes": (AccessMode.PUBLIC_INDEX, AccessMode.USER_AUTHORIZED, AccessMode.OFFICIAL_API),
        "action": "Use indexed public evidence or an authorized API connection; never evade access controls.",
    },
    "rubika": {
        "hosts": {"rubika.ir", "www.rubika.ir"},
        "modes": (AccessMode.PUBLIC_INDEX, AccessMode.USER_AUTHORIZED),
        "action": "Use indexed public evidence or a user-authorized connector when the platform permits it.",
    },
    "eitaa": {
        "hosts": {"eitaa.com", "www.eitaa.com", "eitaa.ir", "www.eitaa.ir"},
        "modes": (AccessMode.PUBLIC_INDEX, AccessMode.USER_AUTHORIZED),
        "action": "Use indexed public evidence or a user-authorized connector when the platform permits it.",
    },
    "soroush_plus": {
        "hosts": {"splus.ir", "www.splus.ir"},
        "modes": (AccessMode.PUBLIC_INDEX, AccessMode.USER_AUTHORIZED),
        "action": "Use indexed public evidence or a user-authorized connector when the platform permits it.",
    },
    "bale": {
        "hosts": {"ble.ir", "www.ble.ir", "bale.ai", "www.bale.ai"},
        "modes": (AccessMode.PUBLIC_INDEX, AccessMode.USER_AUTHORIZED),
        "action": "Use indexed public evidence or a user-authorized connector when the platform permits it.",
    },
}


def platform_for_host(host: str) -> str | None:
    host = (host or "").lower().rstrip(".")
    for platform, policy in PLATFORM_POLICIES.items():
        if host in policy["hosts"]:
            return platform
    return None


def plan_for_url(url: str, connected: dict | None = None) -> AccessPlan | None:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    platform = platform_for_host(host)
    if not platform:
        return None
    connected = connected or {}
    requested = connected.get(platform) or {}
    mode = AccessMode(requested["mode"]) if requested.get("mode") in {m.value for m in PLATFORM_POLICIES[platform]["modes"]} else AccessMode.PUBLIC_INDEX
    scope = str(requested.get("scope") or "public-index")
    return AccessPlan(
        platform=platform,
        host=host,
        mode=mode,
        required_action=PLATFORM_POLICIES[platform]["action"],
        scope=scope,
        execution_allowed=bool(requested.get("execution_allowed", False)),
        bulk_collection_allowed=bool(requested.get("bulk_collection_allowed", False)),
    )


def connector_setup_message(url: str) -> dict:
    plan = plan_for_url(url)
    if not plan:
        return {"required": False, "status": "NOT_RESTRICTED"}
    return {
        "required": True,
        "platform": plan.platform,
        "mode": plan.mode.value,
        "scope": plan.scope,
        "execution_allowed": plan.execution_allowed,
        "bulk_collection_allowed": plan.bulk_collection_allowed,
        "action": plan.required_action,
        "next_step": "OPEN_ACCESS_WIZARD",
    }


def as_dict(plan: AccessPlan) -> dict:
    return asdict(plan)

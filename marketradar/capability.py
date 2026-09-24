from __future__ import annotations

from dataclasses import dataclass

CAPABILITY_STAGES = (
    "REGISTERED",
    "DISCOVERED",
    "DOCUMENTED",
    "REACHABLE",
    "PARSEABLE",
    "VALIDATED",
    "POLICY_VERIFIED",
    "EXECUTION_READY",
)

_STAGE_INDEX = {name: i for i, name in enumerate(CAPABILITY_STAGES)}

@dataclass(frozen=True)
class CapabilityEvidence:
    stage: str
    reasons: tuple[str, ...] = ()


def advance_capability(current: str | None, evidence: CapabilityEvidence) -> str:
    """Apply a monotonic capability promotion; never silently downgrade evidence."""
    current = str(current or "REGISTERED").upper()
    if current not in _STAGE_INDEX:
        current = "REGISTERED"
    target = str(evidence.stage).upper()
    if target not in _STAGE_INDEX:
        raise ValueError(f"UNKNOWN_CAPABILITY_STAGE:{target}")
    return CAPABILITY_STAGES[max(_STAGE_INDEX[current], _STAGE_INDEX[target])]


def capability_evidence_for_verification(*, reachable: bool, parseable: bool,
                                         validated: bool, policy_verified: bool,
                                         execution_ready: bool) -> CapabilityEvidence:
    """Derive the highest stage directly supported by this verification run."""
    if execution_ready:
        return CapabilityEvidence("EXECUTION_READY", ("explicit execution readiness evidence",))
    if policy_verified:
        return CapabilityEvidence("POLICY_VERIFIED", ("policy evidence verified",))
    if validated:
        return CapabilityEvidence("VALIDATED", ("source contract/content validation succeeded",))
    if parseable:
        return CapabilityEvidence("PARSEABLE", ("source payload parsed successfully",))
    if reachable:
        return CapabilityEvidence("REACHABLE", ("source endpoint responded",))
    return CapabilityEvidence("REGISTERED", ("no stronger capability evidence",))

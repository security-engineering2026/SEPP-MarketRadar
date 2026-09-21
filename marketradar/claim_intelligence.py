from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Iterable


class ClaimStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class EntityKind(str, Enum):
    PLATFORM = "PLATFORM"
    CHANNEL = "CHANNEL"
    WEBSITE = "WEBSITE"
    COMPANY = "COMPANY"
    COMMUNITY = "COMMUNITY"
    OPPORTUNITY = "OPPORTUNITY"


@dataclass(frozen=True)
class ClaimEvidence:
    source_url: str
    evidence_type: str
    observed_at: str
    excerpt: str = ""
    independent: bool = True

    def digest(self) -> str:
        raw = "|".join(
            (self.source_url, self.evidence_type, self.observed_at, self.excerpt)
        )
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EntityRef:
    kind: EntityKind
    key: str
    label: str = ""


@dataclass(frozen=True)
class Relationship:
    subject: EntityRef
    predicate: str
    object: EntityRef
    evidence: tuple[ClaimEvidence, ...] = ()


@dataclass
class IntelligenceClaim:
    subject: EntityRef
    predicate: str
    object_value: str
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    confidence: float = 0.0
    evidence: list[ClaimEvidence] = field(default_factory=list)

    def add_evidence(self, evidence: ClaimEvidence) -> None:
        if evidence not in self.evidence:
            self.evidence.append(evidence)

    def independent_evidence_count(self) -> int:
        return len({e.source_url for e in self.evidence if e.independent})

    def evaluate(self, contradictory: bool = False) -> ClaimStatus:
        if contradictory:
            self.status = ClaimStatus.CONTRADICTED
        elif self.independent_evidence_count() >= 2:
            self.status = ClaimStatus.SUPPORTED
        elif self.evidence:
            self.status = ClaimStatus.INCONCLUSIVE
        else:
            self.status = ClaimStatus.UNVERIFIED
        return self.status


def build_claim(
    subject: EntityRef,
    predicate: str,
    object_value: str,
    evidence: Iterable[ClaimEvidence] = (),
) -> IntelligenceClaim:
    claim = IntelligenceClaim(subject, predicate, object_value)
    for item in evidence:
        claim.add_evidence(item)
    claim.evaluate()
    return claim

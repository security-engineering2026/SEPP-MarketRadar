from dataclasses import dataclass
from .models import Evidence
from .policy import eligibility

@dataclass
class EvidenceDecision:
    status: str
    confidence: float
    reasons: list[str]

class EvidenceEngine:
    def opportunity(self, item):
        if not item.title or not item.url: return EvidenceDecision('REJECT',0,['missing title/url'])
        if not item.evidence: return EvidenceDecision('REJECT',0,['no source evidence'])
        return EvidenceDecision('ACCEPT',max(e.confidence for e in item.evidence),[e.finding for e in item.evidence])

    def eligibility(self, policy):
        state, reasons = eligibility(vars(policy), evidence_ok=True)
        confidence = {'EXECUTE': .9, 'REVIEW': .7, 'UNKNOWN': 0.0, 'BLOCK': 1.0}.get(state, 0.0)
        return EvidenceDecision(state, confidence, reasons)

from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class SourcePolicy:
    name: str
    base_url: str
    adapter: str
    source_type: str
    status: str = 'candidate'
    login_required: Optional[bool] = None
    iran_status: str = 'UNKNOWN'
    kyc_status: str = 'UNKNOWN'
    payment_status: str = 'UNKNOWN'
    terms_status: str = 'not_reviewed'
    execution_mode: str = 'MANUAL'
    proposal_limit: Optional[str] = None
    notes: str = ''

@dataclass
class Evidence:
    kind: str
    source: str
    url: str
    finding: str
    confidence: float

@dataclass
class Opportunity:
    source: str
    title: str
    url: str
    description: str
    category: str = 'general_software'
    budget: Optional[float] = None
    currency: Optional[str] = None
    payment: str = 'UNKNOWN'
    evidence_confidence: float = 0.0
    quality_score: float = 0.0
    evidence: list[Evidence] = field(default_factory=list)
    eligibility: str = 'UNKNOWN'
    score: float = 0.0
    time_to_money: float = 0.0
    state: str = 'DISCOVERED'
    rejection_reason: Optional[str] = None
    rank_score: float = 0.0
    skill_fit: float = 0.0
    difficulty_score: float = 1.0
    learning_value: float = 0.0
    application_speed_score: float = 0.0
    track: str = 'software_engineering'
    application_path: str = 'MANUAL_REVIEW'
    application_ready: bool = False

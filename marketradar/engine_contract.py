from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

ENGINE_CONTRACT_VERSION = '1.0'
VALID_MODES = {'AUTO','MANUAL','BOTH','ENGINE_UNCONNECTED'}
TERMINAL_STATUSES = {'SUCCEEDED','FAILED','CANCELLED'}

@dataclass(frozen=True)
class EngineManifest:
    engine_id: str
    name: str
    version: str
    standalone: bool = True
    connectable: bool = True
    capabilities: tuple[str, ...] = ()
    execution_mode: str = 'ENGINE_UNCONNECTED'
    health: str = 'UNKNOWN'
    endpoint: str | None = None
    input_contract: str = 'job.v1'
    output_contract: str = 'result.v1'
    qa_contract: str = 'qa.v1'
    authorization_scope: str = 'user_approval_required'

    def mode(self) -> str:
        if self.connected and self.enabled:
            return 'AUTO'
        if self.standalone and self.enabled:
            return 'ENGINE_UNCONNECTED'
        return 'MANUAL'

    @property
    def connected(self) -> bool:
        return self.execution_mode.upper() not in {'ENGINE_UNCONNECTED','LOCAL_UNCONNECTED','DISCONNECTED'}

    @property
    def enabled(self) -> bool:
        return self.health.upper() not in {'DISABLED','BROKEN'}

    def validate(self) -> None:
        if not self.engine_id.strip(): raise ValueError('INVALID_ENGINE_ID')
        if self.execution_mode.upper() not in VALID_MODES | {'LOCAL','REMOTE'}: raise ValueError('INVALID_ENGINE_MODE')
        if self.connectable is False and self.connected: raise ValueError('NOT_CONNECTABLE')

@dataclass(frozen=True)
class EngineJob:
    job_id: str
    engine_id: str
    opportunity_id: int
    task_type: str
    operations: tuple[str, ...] = ()
    inputs: dict[str, Any] = field(default_factory=dict)
    authorization_token_ref: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass(frozen=True)
class EngineQA:
    status: str
    checks: tuple[dict[str, Any], ...] = ()
    evidence: tuple[dict[str, Any], ...] = ()

@dataclass(frozen=True)
class EngineResult:
    job_id: str
    status: str
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    qa: EngineQA | None = None
    finished_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

def build_job(engine_id: str, opportunity_id: int, task_type: str, operations=(), inputs=None, authorization_token_ref=None, job_id=None) -> EngineJob:
    import uuid
    return EngineJob(job_id=job_id or str(uuid.uuid4()), engine_id=engine_id, opportunity_id=int(opportunity_id), task_type=str(task_type), operations=tuple(operations), inputs=dict(inputs or {}), authorization_token_ref=authorization_token_ref)

def serialize(value: Any) -> dict[str, Any]:
    if hasattr(value, '__dataclass_fields__'):
        return asdict(value)
    raise TypeError('ENGINE_CONTRACT_VALUE_REQUIRED')

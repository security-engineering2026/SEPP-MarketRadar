from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

WORKFLOW_STEPS = ('LOGIN','SEARCH','OPEN_LISTING','APPLY','UPLOAD','CONFIRM')

@dataclass(frozen=True)
class WorkflowStep:
    step: str
    instruction: str = ''
    requires_approval: bool = False

@dataclass(frozen=True)
class SourceWorkflow:
    source: str
    steps: tuple[WorkflowStep, ...]
    language: str = 'unknown'
    last_observed_at: str = ''


def new_workflow(source: str, language='unknown', steps: Iterable[WorkflowStep] | None = None) -> SourceWorkflow:
    values = tuple(steps or (WorkflowStep(s, requires_approval=s in {'APPLY','CONFIRM'}) for s in WORKFLOW_STEPS))
    names = tuple(x.step for x in values)
    unknown = set(names) - set(WORKFLOW_STEPS)
    if unknown: raise ValueError('UNKNOWN_WORKFLOW_STEP')
    return SourceWorkflow(source, values, language, datetime.now(timezone.utc).isoformat())

def persist_workflow(c, workflow: SourceWorkflow) -> None:
    c.execute('DELETE FROM source_workflows WHERE source=?', (workflow.source,))
    for i,step in enumerate(workflow.steps,1):
        c.execute('INSERT INTO source_workflows(source,step_order,step,instruction,requires_approval,language,observed_at) VALUES(?,?,?,?,?,?,?)',(workflow.source,i,step.step,step.instruction,int(step.requires_approval),workflow.language,workflow.last_observed_at))
    c.commit()

def load_workflow(c, source: str) -> SourceWorkflow | None:
    rows=c.execute('SELECT * FROM source_workflows WHERE source=? ORDER BY step_order',(source,)).fetchall()
    if not rows: return None
    return SourceWorkflow(source, tuple(WorkflowStep(r['step'],r['instruction'],bool(r['requires_approval'])) for r in rows), rows[0]['language'] or 'unknown', rows[0]['observed_at'] or '')

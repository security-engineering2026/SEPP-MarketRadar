from __future__ import annotations
import json
from datetime import datetime, timezone
from .capability_registry import match_task, PROVIDERS
from .engine_contract import VALID_MODES, build_job, serialize

class ExecutionBroker:
    """Separates suitability from execution availability.

    An opportunity remains manually executable even when an Engine is absent or
    unconnected. A prepared Engine job is only a persisted PENDING envelope;
    external execution/submission remains behind approval and authorization.
    """
    def __init__(self, connection):
        self.c = connection

    def _task_from_row(self, row) -> dict:
        return {
            'task_type': row['task_type'],
            'work_domain': row['work_domain'],
            'operations': json.loads(row['operations_json'] or '[]'),
            'input_formats': json.loads(row['input_formats_json'] or '[]'),
            'output_formats': json.loads(row['output_formats_json'] or '[]'),
            'requirements': json.loads(row['requirements_json'] or '[]'),
            'qa_requirements': json.loads(row['qa_requirements_json'] or '[]'),
        }

    def plan(self, opportunity_id: int, mode: str = "AUTO") -> dict:
        requested = mode.upper()
        if requested not in {'AUTO','MANUAL'}:
            raise ValueError('EXECUTION_MODE_INVALID')
        row = self.c.execute("SELECT * FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
        if not row:
            raise ValueError("OPPORTUNITY_NOT_FOUND")
        task = self._task_from_row(row)
        match = match_task(task)
        manual = bool(row['manual_execution_possible'])
        if requested == 'MANUAL':
            return {'status': 'MANUAL_READY' if manual else 'MANUAL_UNAVAILABLE', 'execution_mode':'MANUAL', 'manual_possible': manual, 'match': match, 'opportunity_id': opportunity_id}
        connected = [p for p in match.get('matches',[]) if p.get('connected_provider_ids')]
        installed_unconnected = [p for p in match.get('matches',[]) if p.get('installed_not_connected_provider_ids')]
        if match['status'] == 'FULL_MATCH' and connected:
            return {'status':'AUTO_READY','execution_mode':'AUTO','manual_possible':manual,'match':match,'opportunity_id':opportunity_id}
        if installed_unconnected or match['status'] in {'REGISTERED_NO_PROVIDER','PROVIDER_DISABLED'}:
            return {'status':'ENGINE_UNCONNECTED','execution_mode':'ENGINE_UNCONNECTED','manual_possible':manual,'match':match,'opportunity_id':opportunity_id}
        return {'status':'AUTO_NOT_READY','execution_mode':'MANUAL','manual_possible':manual,'match':match,'opportunity_id':opportunity_id}

    def prepare_job(self, opportunity_id: int, engine_id: str, inputs=None, authorization_token_ref=None) -> dict:
        row = self.c.execute("SELECT * FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
        if not row:
            raise ValueError('OPPORTUNITY_NOT_FOUND')
        provider = PROVIDERS.get(engine_id)
        if not provider:
            raise ValueError('ENGINE_NOT_REGISTERED')
        if not provider.standalone and not provider.connectable:
            raise ValueError('ENGINE_NOT_CONNECTABLE')
        if not provider.connected:
            raise ValueError('ENGINE_UNCONNECTED')
        task=self._task_from_row(row)
        match=match_task(task)
        if engine_id not in [x for m in match.get('matches',[]) for x in m.get('connected_provider_ids',[])]:
            raise ValueError('ENGINE_CAPABILITY_NOT_READY')
        if authorization_token_ref is None:
            raise ValueError('AUTHORIZATION_REQUIRED')
        job=build_job(engine_id, opportunity_id, row['task_type'], task['operations'], inputs or {}, authorization_token_ref)
        payload=json.dumps(serialize(job),ensure_ascii=False)
        now=datetime.now(timezone.utc).isoformat()
        self.c.execute('INSERT INTO engine_job_runs(job_id,engine_id,opportunity_id,task_type,status,job_json,started_at) VALUES(?,?,?,?,?,?,?)',(job.job_id,job.engine_id,job.opportunity_id,job.task_type,'PENDING',payload,now))
        self.c.commit()
        return {'status':'PENDING','execution_mode':'AUTO','job':serialize(job)}

    def available_modes(self, opportunity_id: int) -> dict:
        auto = self.plan(opportunity_id, 'AUTO')
        manual = self.plan(opportunity_id, 'MANUAL')
        return {
            'automatic': auto['status'] == 'AUTO_READY',
            'engine_unconnected': auto['status'] == 'ENGINE_UNCONNECTED',
            'manual': manual['status'] == 'MANUAL_READY',
            'automatic_plan': auto,
            'manual_plan': manual,
        }

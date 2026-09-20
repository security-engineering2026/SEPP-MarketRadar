from __future__ import annotations
import time
from datetime import datetime, timezone

class BrowserRecovery:
    def __init__(self,c,max_attempts=3,base_delay=0.2): self.c=c; self.max_attempts=max_attempts; self.base_delay=base_delay
    def execute(self,opportunity_id,adapter,plan):
        attempts=[]; last=None
        for n in range(1,self.max_attempts+1):
            started=datetime.now(timezone.utc).isoformat()
            try:
                result=adapter.execute(plan); status=str(result.get('status','UNKNOWN')) if isinstance(result,dict) else 'UNKNOWN'
                self.c.execute('INSERT INTO application_attempts(opportunity_id,attempt_no,started_at,status,error) VALUES(?,?,?,?,?)',(opportunity_id,n,started,status,None)); self.c.commit()
                return {'attempts':n,'recovered':n>1,'result':result}
            except Exception as exc:
                last=str(exc)
                self.c.execute('INSERT INTO application_attempts(opportunity_id,attempt_no,started_at,status,error) VALUES(?,?,?,?,?)',(opportunity_id,n,started,'ERROR',last)); self.c.commit()
                if n < self.max_attempts: time.sleep(self.base_delay*(2**(n-1)))
        raise RuntimeError(f'APPLICATION_BROWSER_FAILED:{last}')

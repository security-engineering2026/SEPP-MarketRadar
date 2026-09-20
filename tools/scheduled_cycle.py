from __future__ import annotations
import json
from datetime import datetime
from marketradar.engine import MarketRadar


def main():
    with MarketRadar() as mr:
        verification = mr.verify_due_sources()
        project = mr.scan(mode='project')
        now = datetime.now().astimezone()
        intel = {'mode':'intelligence','sources_checked':0,'observations':0,'errors':0,'skipped':True}
        if now.hour in (8, 20) and now.minute <= 30:
            # verify_source_policies is handled during explicit verification cycles.
            intel = mr.scan(mode='intelligence')
        center = mr.daily_center()
        print(json.dumps({'version':'16.0.0','verification':{'checked':len(verification),'blacklisted':sum(1 for x in verification if x.get('source_lane')=='BLACKLIST_ARCHIVE'),'execution_ready':sum(1 for x in verification if x.get('execution_ready'))},'project_scan':project,'intelligence_scan':intel,'daily_center':center}, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()

# compatibility marker: verify_source_policies remains available through MarketRadarRuntime.

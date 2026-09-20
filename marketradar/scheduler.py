from __future__ import annotations
from datetime import datetime, timedelta


class ScanScheduler:
    """Schedule project discovery hourly and market intelligence twice daily."""
    def __init__(self, project_interval_minutes=60, intelligence_times=('08:00', '20:00')):
        self._legacy_fixed_times = isinstance(project_interval_minutes, (tuple, list))
        if self._legacy_fixed_times:
            intelligence_times = tuple(project_interval_minutes)
            project_interval_minutes = 60
        self.project_interval_minutes = int(project_interval_minutes)
        self.intelligence_times = tuple(int(x.split(':')[0]) * 60 + int(x.split(':')[1]) for x in intelligence_times)

    def project_due(self, last_run, now=None):
        now = now or datetime.now().astimezone()
        if not last_run:
            return True
        return now - last_run >= timedelta(minutes=self.project_interval_minutes)

    def intelligence_due(self, last_run, now=None):
        now = now or datetime.now().astimezone()
        if last_run and now - last_run < timedelta(hours=12):
            return False
        minute_of_day = now.hour * 60 + now.minute
        return any(abs(minute_of_day - target) <= 30 for target in self.intelligence_times)

    def next_runs(self, now=None, count=6):
        now = now or datetime.now().astimezone()
        if self._legacy_fixed_times:
            out=[]
            day=now.date()
            for offset in range(0, 8):
                d=day + timedelta(days=offset)
                for minutes in self.intelligence_times:
                    candidate=now.replace(year=d.year,month=d.month,day=d.day,hour=minutes//60,minute=minutes%60,second=0,microsecond=0)
                    if candidate>now: out.append(candidate)
                if len(out)>=count: return out[:count]
            return out[:count]
        return [now + timedelta(minutes=self.project_interval_minutes*i) for i in range(1,count+1)]

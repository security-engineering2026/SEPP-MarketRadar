from __future__ import annotations
import json, csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .notifications import create as create_notification


def now(): return datetime.now(timezone.utc).isoformat()

# Platform constraints are explicit and extensible. A missing limit means UNKNOWN,
# never "unlimited". ParsCoders currently allows one open project per account.
DEFAULT_SOURCE_LIMITS = {
    'ParsCoders_Iran': {'max_open_projects': 1, 'max_pending_applications': 1, 'reason': 'Platform/account allows only one open request at a time.'},
}

def _contract_limits(c, source):
    row = c.execute('SELECT proposal_limit FROM sources WHERE name=?', (source,)).fetchone()
    raw = row['proposal_limit'] if row else None
    limits = {}
    if raw:
        for part in str(raw).replace(',', ';').split(';'):
            if '=' not in part: continue
            k,v = [x.strip() for x in part.split('=',1)]
            if k in {'max_open_projects','max_pending_applications'}:
                try: limits[k]=int(v)
                except ValueError: pass
    if not limits and source in DEFAULT_SOURCE_LIMITS:
        limits.update(DEFAULT_SOURCE_LIMITS[source])
    return limits


def ensure_schema(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS project_contracts(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER UNIQUE NOT NULL,
      accepted_at TEXT, started_at TEXT, deadline_at TEXT, delivered_at TEXT,
      agreed_amount REAL, currency TEXT, payment_due_at TEXT, status TEXT NOT NULL DEFAULT 'ACTIVE',
      notes TEXT, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS followup_schedule(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL, scheduled_at TEXT NOT NULL,
      channel TEXT NOT NULL DEFAULT 'MANUAL', subject TEXT, message TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'SCHEDULED', requires_approval INTEGER NOT NULL DEFAULT 1,
      sent_at TEXT, result TEXT, created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_followup_due ON followup_schedule(status, scheduled_at);
    CREATE TABLE IF NOT EXISTS operation_reminders(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER, reminder_type TEXT NOT NULL,
      due_at TEXT NOT NULL, severity TEXT NOT NULL DEFAULT 'INFO', status TEXT NOT NULL DEFAULT 'OPEN',
      message TEXT NOT NULL, created_at TEXT NOT NULL, resolved_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_reminders_due ON operation_reminders(status, due_at);
    CREATE TABLE IF NOT EXISTS source_application_limits(
      source TEXT PRIMARY KEY, max_open_projects INTEGER, max_pending_applications INTEGER,
      reason TEXT, evidence_url TEXT, checked_at TEXT
    );
    CREATE TABLE IF NOT EXISTS payment_checks(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL, checked_at TEXT NOT NULL,
      status TEXT NOT NULL, amount REAL, currency TEXT, evidence_ref TEXT, notes TEXT, actor TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS final_reports(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL, generated_at TEXT NOT NULL,
      report_json TEXT NOT NULL, report_path TEXT
    );
    ''')
    # Existing source-specific defaults are seeded; verified source constraints are added dynamically by Source Verification.
    for source, cfg in DEFAULT_SOURCE_LIMITS.items():
        c.execute('''INSERT INTO source_application_limits(source,max_open_projects,max_pending_applications,reason,checked_at)
                     VALUES(?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET max_open_projects=excluded.max_open_projects,
                     max_pending_applications=excluded.max_pending_applications,reason=excluded.reason,checked_at=excluded.checked_at''',
                  (source,cfg['max_open_projects'],cfg['max_pending_applications'],cfg['reason'],now()))
    c.commit()


def record_contract(c, opportunity_id, accepted_at=None, started_at=None, deadline_at=None,
                    agreed_amount=None, currency=None, payment_due_at=None, notes=None):
    ts=now()
    c.execute('''INSERT INTO project_contracts(opportunity_id,accepted_at,started_at,deadline_at,agreed_amount,currency,payment_due_at,status,notes,updated_at)
                 VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(opportunity_id) DO UPDATE SET accepted_at=COALESCE(excluded.accepted_at,project_contracts.accepted_at),
                 started_at=COALESCE(excluded.started_at,project_contracts.started_at),deadline_at=COALESCE(excluded.deadline_at,project_contracts.deadline_at),
                 agreed_amount=COALESCE(excluded.agreed_amount,project_contracts.agreed_amount),currency=COALESCE(excluded.currency,project_contracts.currency),
                 payment_due_at=COALESCE(excluded.payment_due_at,project_contracts.payment_due_at),notes=COALESCE(excluded.notes,project_contracts.notes),updated_at=excluded.updated_at''',
              (opportunity_id,accepted_at,started_at,deadline_at,agreed_amount,currency,payment_due_at,'ACTIVE',notes,ts))
    c.commit(); return c.execute('SELECT * FROM project_contracts WHERE opportunity_id=?',(opportunity_id,)).fetchone()


def schedule_followup(c, opportunity_id, scheduled_at, message, channel='MANUAL', subject=None, requires_approval=1):
    c.execute('''INSERT INTO followup_schedule(opportunity_id,scheduled_at,channel,subject,message,status,requires_approval,created_at)
                 VALUES(?,?,?,?,?,'SCHEDULED',?,?)''',
              (opportunity_id,scheduled_at,channel,subject,message,int(bool(requires_approval)),now()))
    c.commit(); return c.execute('SELECT last_insert_rowid()').fetchone()[0]


def due_followups(c, at=None):
    at=at or now(); return c.execute("SELECT * FROM followup_schedule WHERE status='SCHEDULED' AND scheduled_at<=? ORDER BY scheduled_at",(at,)).fetchall()


def mark_followup(c, followup_id, status, result=None):
    sent=now() if status in {'SENT','FAILED','CANCELLED'} else None
    c.execute('UPDATE followup_schedule SET status=?,sent_at=COALESCE(?,sent_at),result=? WHERE id=?',(status,sent,result,followup_id)); c.commit()


def check_payment(c, opportunity_id, status, amount=None, currency=None, evidence_ref=None, notes=None, actor='human'):
    c.execute('INSERT INTO payment_checks(opportunity_id,checked_at,status,amount,currency,evidence_ref,notes,actor) VALUES(?,?,?,?,?,?,?,?)',
              (opportunity_id,now(),status,amount,currency,evidence_ref,notes,actor)); c.commit()
    return c.execute('SELECT * FROM payment_checks WHERE id=last_insert_rowid()').fetchone()


def operation_dashboard(c):
    return {
      'submitted': c.execute("SELECT COUNT(*) FROM opportunities WHERE state IN ('SUBMITTED','VIEWED','MESSAGE_RECEIVED','NEGOTIATION')").fetchone()[0],
      'accepted': c.execute("SELECT COUNT(*) FROM opportunities WHERE state IN ('ACCEPTED','IN_PROGRESS')").fetchone()[0],
      'rejected': c.execute("SELECT COUNT(*) FROM opportunities WHERE state='REJECTED'").fetchone()[0],
      'waiting_payment': c.execute("SELECT COUNT(*) FROM opportunities WHERE state='DELIVERED' AND NOT EXISTS(SELECT 1 FROM revenue r WHERE r.opportunity_id=opportunities.id)").fetchone()[0],
      'paid': c.execute("SELECT COUNT(*) FROM opportunities WHERE state='PAID'").fetchone()[0],
      'open_reminders': c.execute("SELECT COUNT(*) FROM operation_reminders WHERE status='OPEN'").fetchone()[0],
      'due_followups': c.execute("SELECT COUNT(*) FROM followup_schedule WHERE status='SCHEDULED' AND scheduled_at<=?",(now(),)).fetchone()[0],
    }


def project_report(c, opportunity_id):
    row=c.execute('SELECT o.*,pc.accepted_at,pc.started_at,pc.deadline_at,pc.delivered_at,pc.agreed_amount,pc.currency AS contract_currency,pc.payment_due_at,pc.status AS project_status FROM opportunities o LEFT JOIN project_contracts pc ON pc.opportunity_id=o.id WHERE o.id=?',(opportunity_id,)).fetchone()
    if not row: raise ValueError('OPPORTUNITY_NOT_FOUND')
    payment=c.execute('SELECT * FROM revenue WHERE opportunity_id=? ORDER BY received_at DESC LIMIT 1',(opportunity_id,)).fetchone()
    checks=c.execute('SELECT * FROM payment_checks WHERE opportunity_id=? ORDER BY checked_at DESC',(opportunity_id,)).fetchall()
    payment_attempts=c.execute('SELECT * FROM payment_verification_attempts WHERE opportunity_id=? ORDER BY checked_at DESC',(opportunity_id,)).fetchall()
    events=c.execute('SELECT * FROM application_events WHERE opportunity_id=? ORDER BY at',(opportunity_id,)).fetchall()
    followups=c.execute('SELECT * FROM followup_schedule WHERE opportunity_id=? ORDER BY scheduled_at',(opportunity_id,)).fetchall()
    milestones=c.execute('SELECT * FROM project_milestones WHERE opportunity_id=? ORDER BY due_at,id',(opportunity_id,)).fetchall()
    communications=c.execute('SELECT * FROM project_communications WHERE opportunity_id=? ORDER BY occurred_at',(opportunity_id,)).fetchall()
    finance_entries=c.execute('''SELECT fl.*,fa.name AS account_name,fa.iban,fa.institution
                                 FROM finance_ledger fl LEFT JOIN financial_accounts fa ON fa.id=fl.account_id
                                 WHERE fl.opportunity_id=? ORDER BY fl.occurred_at''',(opportunity_id,)).fetchall()
    stage_durations=[]
    ev=[dict(x) for x in events]
    for i,e in enumerate(ev):
        if i+1 < len(ev):
            try:
                a=datetime.fromisoformat(str(e['at']).replace('Z','+00:00')); b=datetime.fromisoformat(str(ev[i+1]['at']).replace('Z','+00:00'))
                stage_durations.append({'from_state':e['from_state'],'to_state':e['to_state'],'duration_hours':round((b-a).total_seconds()/3600,3)})
            except Exception: pass
    p=dict(row); pay=dict(payment) if payment else None
    actual_payment_status = 'NOT_RECEIVED'
    if pay:
        actual_payment_status = pay.get('verification_state') or 'RECORDED_UNVERIFIED'
    if payment_attempts and any(x['status']=='VERIFIED' for x in payment_attempts): actual_payment_status='VERIFIED'
    deadline_variance_hours=None
    if p.get('deadline_at') and pay and pay.get('received_at'):
        try:
            deadline_variance_hours=round((datetime.fromisoformat(str(pay['received_at']).replace('Z','+00:00'))-datetime.fromisoformat(str(p['deadline_at']).replace('Z','+00:00'))).total_seconds()/3600,3)
        except Exception: pass
    return {
      'project': p, 'payment': pay, 'payment_status': actual_payment_status,
      'payment_checks':[dict(x) for x in checks], 'payment_verification_attempts':[dict(x) for x in payment_attempts],
      'lifecycle':ev, 'stage_durations':stage_durations, 'followups':[dict(x) for x in followups],
      'milestones':[dict(x) for x in milestones], 'communications':[dict(x) for x in communications],
      'finance_entries':[dict(x) for x in finance_entries],
      'deadline_variance_hours':deadline_variance_hours, 'generated_at': now()
    }


def generate_final_report(c, opportunity_id, out_dir: Path):
    report=project_report(c,opportunity_id); out_dir.mkdir(parents=True,exist_ok=True)
    path=out_dir/f'project-{opportunity_id}-final.json'; path.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    p=report['project']; pay=report.get('payment') or {}
    lifecycle_rows=''.join(f"<tr><td>{i+1}</td><td>{e.get('from_state','')}</td><td>{e.get('to_state','')}</td><td>{e.get('at','')}</td><td>{e.get('actor','')}</td></tr>" for i,e in enumerate(report['lifecycle']))
    finance_rows=''.join(f"<tr><td>{x.get('entry_type','')}</td><td>{x.get('amount','')}</td><td>{x.get('currency','')}</td><td>{x.get('occurred_at','')}</td><td>{x.get('account_name','')}</td><td>{x.get('iban','')}</td><td>{x.get('institution','')}</td><td>{x.get('payment_ref','')}</td></tr>" for x in report['finance_entries'])
    comm_rows=''.join(f"<tr><td>{x.get('channel','')}</td><td>{x.get('direction','')}</td><td>{x.get('occurred_at','')}</td><td>{x.get('subject') or ''}</td><td>{x.get('external_ref') or ''}</td></tr>" for x in report['communications'])
    html=f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>MarketRadar Project Report #{opportunity_id}</title><style>@page{{size:A4;margin:14mm}}body{{font-family:"Segoe UI",Arial,sans-serif;color:#172033;line-height:1.45}}table{{border-collapse:collapse;width:100%;margin:10px 0 20px;direction:ltr}}td,th{{border:1px solid #d7dce4;padding:7px;font-size:10.5px;text-align:left;vertical-align:top}}th{{background:#eef2f7}}h1,h2{{page-break-after:avoid}}.kpi{{padding:6px 10px;border:1px solid #d5dbe5;border-radius:7px;margin:3px;display:inline-block;direction:ltr}}.section{{page-break-inside:avoid}}.muted{{color:#667085;direction:ltr}}.footer{{font-size:10px;color:#667085}}</style></head><body><h1>MarketRadar — Project Final Report #{opportunity_id}</h1><p class="muted">Generated: {report['generated_at']}</p><div><span class="kpi"><b>Source</b>: {p['source']}</span><span class="kpi"><b>Status</b>: {p.get('state') or ''}</span><span class="kpi"><b>Amount</b>: {p.get('agreed_amount') or ''} {p.get('contract_currency') or ''}</span></div><div class="section"><h2>Request</h2><table><tr><th>Project</th><td>{p['title']}</td></tr><tr><th>Source</th><td>{p['source']}</td></tr><tr><th>URL</th><td>{p.get('url') or ''}</td></tr><tr><th>Accepted at</th><td>{p.get('accepted_at') or ''}</td></tr><tr><th>Started at</th><td>{p.get('started_at') or ''}</td></tr><tr><th>Deadline</th><td>{p.get('deadline_at') or ''}</td></tr><tr><th>Agreed amount</th><td>{p.get('agreed_amount') or ''} {p.get('contract_currency') or ''}</td></tr><tr><th>Payment due</th><td>{p.get('payment_due_at') or ''}</td></tr><tr><th>Payment received</th><td>{pay.get('received_at') or ''}</td></tr><tr><th>Payment status</th><td>{report.get('payment_status') or pay.get('verification_state') or 'NOT RECORDED'}</td></tr></table></div><div class="section"><h2>Lifecycle Timeline</h2><table><tr><th>#</th><th>From</th><th>To</th><th>Timestamp</th><th>Actor</th></tr>{lifecycle_rows or '<tr><td colspan="5">No lifecycle events.</td></tr>'}</table></div><div class="section"><h2>Receiving Account / Finance Evidence</h2><table><tr><th>Type</th><th>Amount</th><th>Currency</th><th>Timestamp</th><th>Account</th><th>IBAN</th><th>Institution</th><th>Payment Ref</th></tr>{finance_rows or '<tr><td colspan="8">No finance entry.</td></tr>'}</table></div><div class="section"><h2>Communications</h2><table><tr><th>Channel</th><th>Direction</th><th>Timestamp</th><th>Subject</th><th>External Ref</th></tr>{comm_rows or '<tr><td colspan="5">No communications.</td></tr>'}</table></div><p class="footer">This report is generated from MarketRadar application, communication, evidence and finance ledgers. External settlement is verified only when explicit payment evidence exists.</p></body></html>"""
    html_path=out_dir/f'project-{opportunity_id}-final.html'; html_path.write_text(html,encoding='utf-8')
    c.execute('INSERT INTO final_reports(opportunity_id,generated_at,report_json,report_path) VALUES(?,?,?,?)',(opportunity_id,report['generated_at'],json.dumps(report,ensure_ascii=False,default=str),str(html_path))); c.commit()
    return str(html_path), report


def source_application_gate(c, source, opportunity_id=None):
    """Enforce source-declared application/project concurrency constraints."""
    lim=c.execute('SELECT max_open_projects,max_pending_applications,reason FROM source_application_limits WHERE source=?',(source,)).fetchone()
    row=c.execute('SELECT proposal_limit FROM sources WHERE name=?',(source,)).fetchone()
    raw=row['proposal_limit'] if row else None
    contract={}
    if raw:
        for part in str(raw).replace(',', ';').split(';'):
            if '=' not in part: continue
            k,v=[x.strip() for x in part.split('=',1)]
            if k in {'max_open_projects','max_pending_applications'}:
                try: contract[k]=int(v)
                except ValueError: pass
    if contract:
        max_open=contract.get('max_open_projects'); max_pending=contract.get('max_pending_applications'); reason='Source-declared constraint'
    elif lim:
        max_open=lim['max_open_projects']; max_pending=lim['max_pending_applications']; reason=lim['reason'] or 'Declared source constraint'
    else:
        return {'allowed':True,'reason':'NO_DECLARED_LIMIT'}
    open_count=c.execute("SELECT COUNT(*) FROM opportunities WHERE source=? AND state IN ('ACCEPTED','IN_PROGRESS')",(source,)).fetchone()[0]
    pending_count=c.execute("SELECT COUNT(*) FROM opportunities WHERE source=? AND state IN ('APPROVAL_PENDING','SUBMITTED','VIEWED','MESSAGE_RECEIVED','NEGOTIATION')",(source,)).fetchone()[0]
    if max_open is not None and open_count >= max_open and (opportunity_id is None or not c.execute("SELECT 1 FROM opportunities WHERE id=? AND state IN ('ACCEPTED','IN_PROGRESS')",(opportunity_id,)).fetchone()):
        return {'allowed':False,'reason':'OPEN_PROJECT_LIMIT','detail':reason,'current':open_count,'limit':max_open}
    if max_pending is not None and pending_count >= max_pending and (opportunity_id is None or not c.execute("SELECT 1 FROM opportunities WHERE id=? AND state IN ('APPROVAL_PENDING','SUBMITTED','VIEWED','MESSAGE_RECEIVED','NEGOTIATION')",(opportunity_id,)).fetchone()):
        return {'allowed':False,'reason':'PENDING_APPLICATION_LIMIT','detail':reason,'current':pending_count,'limit':max_pending}
    return {'allowed':True,'reason':'WITHIN_LIMIT','open_projects':open_count,'pending_applications':pending_count}


def operation_tick(c):
    """Convert deadlines and scheduled follow-ups into durable reminders; never silently sends external messages."""
    ts=now()
    rows=c.execute("SELECT o.id,o.title,o.deadline_at,pc.deadline_at AS project_deadline,pc.payment_due_at FROM opportunities o LEFT JOIN project_contracts pc ON pc.opportunity_id=o.id WHERE o.state IN ('SUBMITTED','NEGOTIATION','ACCEPTED','IN_PROGRESS','DELIVERED')").fetchall()
    for r in rows:
        deadline=r['project_deadline'] or r['deadline_at']
        if deadline:
            try:
                dt=datetime.fromisoformat(str(deadline).replace('Z','+00:00'))
                hours=(dt-datetime.now(timezone.utc)).total_seconds()/3600
                if hours <= 24:
                    severity='CRITICAL' if hours <= 0 else ('HIGH' if hours <= 6 else 'WARN')
                    msg=f"Project deadline {'passed' if hours<=0 else 'is approaching'}: {r['title']}"
                    exists=c.execute("SELECT 1 FROM operation_reminders WHERE opportunity_id=? AND reminder_type='DEADLINE' AND status='OPEN'",(r['id'],)).fetchone()
                    if not exists: c.execute("INSERT INTO operation_reminders(opportunity_id,reminder_type,due_at,severity,message,created_at) VALUES(?,?,?,?,?,?)",(r['id'],'DEADLINE',deadline,severity,msg,ts))
            except Exception: pass
        if r['payment_due_at'] and r['id']:
            try:
                dt=datetime.fromisoformat(str(r['payment_due_at']).replace('Z','+00:00'))
                if dt <= datetime.now(timezone.utc) and r['id']:
                    exists=c.execute("SELECT 1 FROM operation_reminders WHERE opportunity_id=? AND reminder_type='PAYMENT_DUE' AND status='OPEN'",(r['id'],)).fetchone()
                    if not exists: c.execute("INSERT INTO operation_reminders(opportunity_id,reminder_type,due_at,severity,message,created_at) VALUES(?,?,?,?,?,?)",(r['id'],'PAYMENT_DUE',r['payment_due_at'],'HIGH',f"Payment follow-up due: {r['title']}",ts))
            except Exception: pass
    due=c.execute("SELECT * FROM followup_schedule WHERE status='SCHEDULED' AND scheduled_at<=? ORDER BY scheduled_at",(ts,)).fetchall()
    for f in due:
        exists=c.execute("SELECT 1 FROM operation_reminders WHERE opportunity_id=? AND reminder_type='FOLLOWUP_DUE' AND message=? AND status='OPEN'",(f['opportunity_id'],f['message'])).fetchone()
        if not exists: c.execute("INSERT INTO operation_reminders(opportunity_id,reminder_type,due_at,severity,message,created_at) VALUES(?,?,?,?,?,?)",(f['opportunity_id'],'FOLLOWUP_DUE',f['scheduled_at'],'INFO',f"Follow-up due: {f['message']}",ts))
    rows=c.execute("SELECT * FROM operation_reminders WHERE status='OPEN' ORDER BY CASE severity WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'WARN' THEN 2 ELSE 3 END,due_at").fetchall()
    for r in rows:
        exists=c.execute("SELECT 1 FROM notifications WHERE opportunity_id=? AND kind=? AND due_at=?",(r['opportunity_id'],r['reminder_type'],r['due_at'])).fetchone()
        if not exists:
            create_notification(c,r['reminder_type'],r['severity']+' — MarketRadar',r['message'],r['opportunity_id'],r['severity'],r['due_at'])
    c.commit()
    return rows

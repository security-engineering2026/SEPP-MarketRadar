from __future__ import annotations
import json, math
from datetime import datetime, timezone

def record_outcome(c, opportunity_id, outcome, reason=None, amount=None, currency=None, notes=None):
    allowed={'SUBMITTED','VIEWED','MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','REJECTED','CANCELLED','EXPIRED','DELIVERED','PAID'}
    outcome=str(outcome).upper()
    if outcome not in allowed: raise ValueError('INVALID_OUTCOME')
    now=datetime.now(timezone.utc).isoformat()
    c.execute('INSERT INTO opportunity_outcomes(opportunity_id,observed_at,outcome,reason,amount,currency,notes) VALUES(?,?,?,?,?,?,?)',(opportunity_id,now,outcome,reason,amount,currency,notes))
    if reason:
        c.execute('INSERT INTO outcome_reason_learning(reason,outcome,count,last_seen) VALUES(?,?,1,?) ON CONFLICT(reason,outcome) DO UPDATE SET count=count+1,last_seen=excluded.last_seen',(str(reason)[:256],outcome,now))
    return update_learning_snapshot(c, opportunity_id)

def _stats(c, where='', params=()):
    row=c.execute(f'''SELECT COUNT(*) total, SUM(CASE WHEN outcome='ACCEPTED' THEN 1 ELSE 0 END) accepted, SUM(CASE WHEN outcome='REJECTED' THEN 1 ELSE 0 END) rejected, COALESCE(SUM(CASE WHEN outcome='PAID' THEN amount ELSE 0 END),0) revenue FROM opportunity_outcomes {where}''',params).fetchone()
    total=int(row['total'] or 0); accepted=int(row['accepted'] or 0); rejected=int(row['rejected'] or 0)
    return {'total':total,'accepted':accepted,'rejected':rejected,'revenue':float(row['revenue'] or 0),'acceptance_rate':(accepted+1)/(total+2)}

def estimate_acceptance_prior(c, source, category):
    def rate(where, value):
        row=c.execute(f"SELECT COUNT(*) total, SUM(CASE WHEN outcome='ACCEPTED' THEN 1 ELSE 0 END) accepted FROM opportunity_outcomes WHERE opportunity_id IN (SELECT id FROM opportunities WHERE {where})",(value,)).fetchone()
        total=int(row['total'] or 0); accepted=int(row['accepted'] or 0)
        return (accepted+1)/(total+2)
    source_rate=rate('source=?',source); category_rate=rate('category=?',category)
    return 0.55*source_rate+0.30*category_rate+0.15*0.5

def update_learning_snapshot(c, opportunity_id):
    opp=c.execute('SELECT source,category,budget,currency FROM opportunities WHERE id=?',(opportunity_id,)).fetchone()
    if not opp: raise ValueError('OPPORTUNITY_NOT_FOUND')
    global_s=_stats(c)
    source_s=_stats(c,'WHERE opportunity_id IN (SELECT id FROM opportunities WHERE source=?)',(opp['source'],))
    cat_s=_stats(c,'WHERE opportunity_id IN (SELECT id FROM opportunities WHERE category=?)',(opp['category'],))
    source_rate=source_s['acceptance_rate']; cat_rate=cat_s['acceptance_rate']; global_rate=global_s['acceptance_rate']
    acceptance=0.50*source_rate+0.30*cat_rate+0.20*global_rate
    revenue=source_s['revenue']+cat_s['revenue']*0.5
    expected_value=acceptance*float(opp['budget'] or 0)
    c.execute('''INSERT INTO opportunity_learning(opportunity_id,acceptance_probability,source_acceptance_rate,category_acceptance_rate,global_acceptance_rate,expected_value,observed_revenue,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(opportunity_id) DO UPDATE SET acceptance_probability=excluded.acceptance_probability,source_acceptance_rate=excluded.source_acceptance_rate,category_acceptance_rate=excluded.category_acceptance_rate,global_acceptance_rate=excluded.global_acceptance_rate,expected_value=excluded.expected_value,observed_revenue=excluded.observed_revenue,updated_at=excluded.updated_at''',(opportunity_id,acceptance,source_rate,cat_rate,global_rate,expected_value,revenue,datetime.now(timezone.utc).isoformat()))
    return {'acceptance_probability':round(acceptance,4),'expected_value':round(expected_value,2),'observed_revenue':round(revenue,2)}

def learning_summary(c):
    rows=c.execute('SELECT reason,outcome,count FROM outcome_reason_learning ORDER BY count DESC,reason').fetchall()
    return {'reasons':[dict(r) for r in rows],'opportunities':[_row for _row in map(dict,c.execute('SELECT * FROM opportunity_learning ORDER BY expected_value DESC LIMIT 50').fetchall())]}

def negative_outcome_summary(c):
    """Summarize negative operational signals without rewriting historical outcomes."""
    rows = c.execute(
        "SELECT outcome, COUNT(*) AS count FROM opportunity_outcomes "
        "WHERE outcome IN ('REJECTED','EXPIRED','CANCELLED') GROUP BY outcome ORDER BY outcome"
    ).fetchall()
    by_outcome = {row["outcome"]: int(row["count"]) for row in rows}
    blocked = int(c.execute("SELECT COUNT(*) FROM opportunities WHERE eligibility='BLOCK'").fetchone()[0])
    failed_actions = int(c.execute("SELECT COUNT(*) FROM action_attempts WHERE status='FAILED'").fetchone()[0])
    reasons = [
        dict(row)
        for row in c.execute(
            "SELECT reason,outcome,count,last_seen FROM outcome_reason_learning "
            "WHERE outcome IN ('REJECTED','EXPIRED','CANCELLED') "
            "ORDER BY count DESC,reason"
        ).fetchall()
    ]
    return {
        "by_outcome": by_outcome,
        "blocked_opportunities": blocked,
        "failed_action_attempts": failed_actions,
        "reasons": reasons,
    }

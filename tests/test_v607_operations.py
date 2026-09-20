import sqlite3
from datetime import datetime, timezone, timedelta
from marketradar.db import connect
from marketradar.application import transition, record_revenue, verify_payment
from marketradar.operations import record_contract, schedule_followup, operation_tick, source_application_gate, project_report


def make_db(tmp_path):
    c=connect(tmp_path/'x.db')
    c.execute("INSERT INTO sources(name,base_url,status) VALUES('ParsCoders_Iran','https://parscoders.com/','active')")
    c.execute("INSERT INTO opportunities(source,title,url,state,eligibility) VALUES('ParsCoders_Iran','P1','https://example/1','DISCOVERED','EXECUTE')")
    c.execute("INSERT INTO opportunities(source,title,url,state,eligibility) VALUES('ParsCoders_Iran','P2','https://example/2','DISCOVERED','EXECUTE')")
    c.commit(); return c


def test_payment_claim_does_not_mark_paid_until_verified(tmp_path):
    c=make_db(tmp_path); oid=1
    transition(c,oid,'ELIGIBILITY_CHECK'); transition(c,oid,'RECOMMENDED'); transition(c,oid,'APPROVAL_PENDING'); transition(c,oid,'SUBMITTED'); transition(c,oid,'VIEWED'); transition(c,oid,'NEGOTIATION'); transition(c,oid,'ACCEPTED'); transition(c,oid,'IN_PROGRESS'); transition(c,oid,'DELIVERED')
    record_revenue(c,oid,100,'USD','2026-09-11T10:00:00+00:00','ref-1')
    assert c.execute('select state from opportunities where id=?',(oid,)).fetchone()[0]=='DELIVERED'
    verify_payment(c,oid,'ref-1','VERIFIED')
    assert c.execute('select state from opportunities where id=?',(oid,)).fetchone()[0]=='PAID'
    c.close()


def test_contract_report_has_project_and_payment_fields(tmp_path):
    c=make_db(tmp_path); oid=1
    transition(c,oid,'ELIGIBILITY_CHECK'); transition(c,oid,'RECOMMENDED'); transition(c,oid,'APPROVAL_PENDING'); transition(c,oid,'SUBMITTED'); transition(c,oid,'VIEWED'); transition(c,oid,'NEGOTIATION'); transition(c,oid,'ACCEPTED')
    accepted='2026-09-11T09:00:00+00:00'; deadline='2026-09-20T18:00:00+00:00'
    record_contract(c,oid,accepted_at=accepted,started_at='2026-09-11T10:00:00+00:00',deadline_at=deadline,agreed_amount=250,currency='USD')
    transition(c,oid,'IN_PROGRESS'); transition(c,oid,'DELIVERED')
    record_revenue(c,oid,250,'USD','2026-09-20T12:30:00+00:00','ref-2')
    r=project_report(c,oid)
    assert r['project']['accepted_at']==accepted
    assert r['payment']['amount']==250
    assert r['payment']['received_at']=='2026-09-20T12:30:00+00:00'
    c.close()


def test_followup_and_deadline_become_reminders(tmp_path):
    c=make_db(tmp_path); oid=1
    transition(c,oid,'ELIGIBILITY_CHECK'); transition(c,oid,'RECOMMENDED'); transition(c,oid,'APPROVAL_PENDING'); transition(c,oid,'SUBMITTED')
    due=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    record_contract(c,oid,deadline_at=due)
    schedule_followup(c,oid,due,'check status')
    reminders=operation_tick(c)
    kinds={r['reminder_type'] for r in reminders if r['opportunity_id']==oid}
    assert 'DEADLINE' in kinds and 'FOLLOWUP_DUE' in kinds
    c.close()


def test_parscoders_open_application_limit(tmp_path):
    c=make_db(tmp_path)
    transition(c,1,'ELIGIBILITY_CHECK'); transition(c,1,'RECOMMENDED'); transition(c,1,'APPROVAL_PENDING'); transition(c,1,'SUBMITTED'); transition(c,1,'VIEWED'); transition(c,1,'NEGOTIATION'); transition(c,1,'ACCEPTED'); transition(c,1,'IN_PROGRESS')
    gate=source_application_gate(c,'ParsCoders_Iran',2)
    assert gate['allowed'] is False and gate['reason']=='OPEN_PROJECT_LIMIT'
    c.close()


def test_parscoders_limit_is_enforced_by_submission_path(tmp_path):
    c=make_db(tmp_path)
    transition(c,1,'ELIGIBILITY_CHECK'); transition(c,1,'RECOMMENDED'); transition(c,1,'APPROVAL_PENDING'); transition(c,1,'SUBMITTED'); transition(c,1,'VIEWED'); transition(c,1,'NEGOTIATION'); transition(c,1,'ACCEPTED'); transition(c,1,'IN_PROGRESS')
    from marketradar.operational_completion import submit_with_approval, OperationalError
    row=dict(c.execute('select * from opportunities where id=2').fetchone())
    transition(c,2,'ELIGIBILITY_CHECK'); transition(c,2,'RECOMMENDED'); transition(c,2,'APPROVAL_PENDING')
    try:
        submit_with_approval(c,row,{},'proposal',[],provider=None)
    except OperationalError as exc:
        assert 'SOURCE_APPLICATION_LIMIT:OPEN_PROJECT_LIMIT' in str(exc)
    else:
        raise AssertionError('source concurrency limit was bypassed')
    c.close()


def test_final_report_writes_html(tmp_path):
    c=make_db(tmp_path); oid=1
    transition(c,oid,'ELIGIBILITY_CHECK'); transition(c,oid,'RECOMMENDED'); transition(c,oid,'APPROVAL_PENDING'); transition(c,oid,'SUBMITTED'); transition(c,oid,'VIEWED'); transition(c,oid,'NEGOTIATION'); transition(c,oid,'ACCEPTED')
    record_contract(c,oid,accepted_at='2026-09-11T09:00:00+00:00',agreed_amount=100,currency='USD')
    transition(c,oid,'IN_PROGRESS'); transition(c,oid,'DELIVERED'); record_revenue(c,oid,100,'USD','2026-09-11T12:00:00+00:00','r-final')
    from marketradar.operations import generate_final_report
    path,_=generate_final_report(c,oid,tmp_path/'reports')
    assert path.endswith('.html') and (tmp_path/'reports'/f'project-{oid}-final.html').exists()
    c.close()

from datetime import datetime, timezone, timedelta
from marketradar.db import connect
from marketradar.application import transition, record_revenue, verify_payment
from marketradar.economic_loop import register_tracking, record_status_observation, add_milestone, complete_milestone, add_communication

def seed(c):
    c.execute("INSERT INTO sources(name,base_url,status,proposal_limit) VALUES('P','https://example.com','active','max_open_projects=1;max_pending_applications=2')")
    c.execute("INSERT INTO opportunities(source,title,url,state,eligibility) VALUES('P','T','https://example.com/a','DISCOVERED','EXECUTE')")
    c.commit()

def advance_to(c, state):
    path=['ELIGIBILITY_CHECK','RECOMMENDED','APPROVAL_PENDING','SUBMITTED']
    for s in path:
        transition(c,1,s)

def test_application_tracking_observation_moves_state(tmp_path):
    c=connect(tmp_path/'x.db'); seed(c); advance_to(c,'SUBMITTED')
    register_tracking(c,1,'P',external_ref='EXT-1',status_url='https://example.com/status',mode='MANUAL_EVIDENCE')
    r=record_status_observation(c,1,'P','viewed',0.95,'https://example.com/status','seen', 'EXT-1')
    assert r['accepted'] is True
    assert c.execute('select state from opportunities where id=1').fetchone()[0]=='VIEWED'
    c.close()

def test_project_milestone_and_communication_are_durable(tmp_path):
    c=connect(tmp_path/'x.db'); seed(c)
    mid=add_milestone(c,1,'Design', (datetime.now(timezone.utc)+timedelta(days=1)).isoformat())
    complete_milestone(c,mid,'artifact:sha256')
    add_communication(c,1,'email','OUT','Acceptance','accepted','MSG-1','evidence-1')
    assert c.execute('select status from project_milestones where id=?',(mid,)).fetchone()[0]=='COMPLETED'
    assert c.execute('select external_ref from project_communications where opportunity_id=1').fetchone()[0]=='MSG-1'
    c.close()

def test_payment_claim_and_verification_remain_separate(tmp_path):
    c=connect(tmp_path/'x.db'); seed(c); advance_to(c,'SUBMITTED')
    for s in ('VIEWED','NEGOTIATION','ACCEPTED','IN_PROGRESS','DELIVERED'): transition(c,1,s)
    record_revenue(c,1,100,'USD','2026-09-11T10:00:00+00:00','REF')
    assert c.execute('select state from opportunities where id=1').fetchone()[0]=='DELIVERED'
    verify_payment(c,1,'REF','VERIFIED')
    assert c.execute('select state from opportunities where id=1').fetchone()[0]=='PAID'
    c.close()


def test_runtime_payment_claim_does_not_mark_paid(tmp_path):
    from marketradar.runtime import MarketRadarRuntime
    c=connect(tmp_path/'x.db'); seed(c); advance_to(c,'SUBMITTED')
    for s in ('VIEWED','NEGOTIATION','ACCEPTED','IN_PROGRESS','DELIVERED'): transition(c,1,s)
    rt=MarketRadarRuntime(c, [], 'test-secret', settings={'profile':{}})
    rt.record_payment(1,100,'USD','2026-09-11T10:00:00+00:00','REF')
    assert c.execute('select state from opportunities where id=1').fetchone()[0]=='DELIVERED'
    c.close()


def test_application_tracker_cannot_mark_paid(tmp_path):
    c=connect(tmp_path/'x.db'); seed(c); advance_to(c,'SUBMITTED')
    for s in ('VIEWED','NEGOTIATION','ACCEPTED','IN_PROGRESS','DELIVERED'): transition(c,1,s)
    register_tracking(c,1,'P',external_ref='EXT',status_url='https://example.com/status',mode='MANUAL_EVIDENCE')
    r=record_status_observation(c,1,'P','paid',0.99,'https://example.com/status','paid','EXT')
    assert r['accepted'] is False
    assert r['reason']=='PAYMENT_STATUS_REQUIRES_PAYMENT_VERIFICATION'
    assert c.execute('select state from opportunities where id=1').fetchone()[0]=='DELIVERED'
    c.close()


def test_source_limit_blocks_second_pending_application(tmp_path):
    c=connect(tmp_path/'x.db'); seed(c)
    c.execute("INSERT INTO opportunities(source,title,url,state,eligibility) VALUES('P','T2','https://example.com/b','SUBMITTED','EXECUTE')")
    c.commit()
    from marketradar.operations import source_application_gate
    assert source_application_gate(c,'P')['allowed'] is True
    c.execute("INSERT INTO opportunities(source,title,url,state,eligibility) VALUES('P','T3','https://example.com/c','SUBMITTED','EXECUTE')")
    c.commit()
    assert source_application_gate(c,'P')['allowed'] is False
    c.close()


def test_windows_packaging_contains_scheduler_script():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    build=(root/'packaging'/'build_windows.ps1').read_text(encoding='utf-8')
    installer=(root/'packaging'/'installer.iss').read_text(encoding='utf-8')
    assert 'install_scheduled_scan.ps1' in build
    assert 'install_scheduled_scan.ps1' in installer


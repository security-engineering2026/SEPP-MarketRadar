import random,tempfile,sqlite3
from marketradar.security import ApprovalBroker
from marketradar.reputation import review_intel
from marketradar.policy import eligibility
from marketradar.db import connect
from marketradar.demo import seed
def test_approval_replay_and_binding():
 b=ApprovalBroker();a=b.issue('SUBMIT','o',{'p':1},{'e':1},'p1',0,10);assert b.authorize(a,'SUBMIT','o',{'p':1},{'e':1},'p1',1)[0];assert b.authorize(a,'SUBMIT','o',{'p':1},{'e':1},'p1',2)[1]=='REPLAY'
def test_mutation_blocked():
 b=ApprovalBroker();a=b.issue('SUBMIT','o',{'p':1},{'e':1},'p1',0);assert not b.authorize(a,'SUBMIT','o',{'p':2},{'e':1},'p1',1)[0]
def test_unknown_not_execute():
 assert eligibility({'iran_status':'UNKNOWN','kyc_status':'UNKNOWN','payment_status':'USDT'})[0]=='UNKNOWN';assert eligibility({'iran_status':'ALLOW','kyc_status':'UNKNOWN','payment_status':'USDT'})[0]=='REVIEW'
def test_review_provenance():
 rs=[{'author':str(i),'text':'great','sentiment':'positive','provenance_root':'same','verified':False,'timestamp':i} for i in range(6)];x=review_intel(rs);assert not x['authoritative'];assert 'PROVENANCE_CONCENTRATION' in x['flags']
def test_negative_independent_reviews():
 rs=[{'author':'a','text':'bad','sentiment':'negative','provenance_root':'r1'},{'author':'b','text':'bad2','sentiment':'negative','provenance_root':'r2'}];assert review_intel(rs)['state']=='HIGH_RISK'
def test_raw_immutable():
 with tempfile.TemporaryDirectory() as d:
     try:
      c=connect(d+'/x.db');c.execute("insert into raw_observations(source,url,observed_at,payload,payload_sha256) values('s','u','t','p','h')");c.commit()
      try:c.execute("update raw_observations set payload='x'");c.commit();assert False
      except sqlite3.DatabaseError:c.rollback()
      try:c.execute("delete from raw_observations");c.commit();assert False
      except sqlite3.DatabaseError:pass
     finally:
         if 'c' in locals():
             c.close()
def test_daily_center():
 with tempfile.TemporaryDirectory() as d:
     try:
      c=connect(d+'/x.db');x=seed(c).daily_center();assert len(x['top7'])==7;assert len(x['do_now'])==3
     finally:
         if 'c' in locals():
             c.close()
def test_fuzz_10000():
 b=ApprovalBroker()
 for i in range(10000):
  a=b.issue('SUBMIT','o',{'amount':100},{'e':'x'},'p',0,1000);amt=random.randint(0,1000);ok,_=b.authorize(a,'SUBMIT','o',{'amount':amt},{'e':'x'},'p',1);assert ok==(amt==100)
def test_unknown_property_500():
 for _ in range(500):
  s={'iran_status':random.choice(['UNKNOWN','BLOCK']),'kyc_status':'UNKNOWN','payment_status':random.choice(['UNKNOWN','USDT'])};assert eligibility(s)[0] != 'EXECUTE'


def test_terms_not_reviewed_cannot_yield_execute():
    from marketradar.policy import eligibility
    source={'iran_status':'ALLOW','kyc_status':'ALLOW','payment_status':'USDT','terms_status':'needs_review'}
    assert eligibility(source)[0] == 'REVIEW'
    source['terms_status']='allowed'
    assert eligibility(source)[0] == 'EXECUTE'


def test_unknown_is_never_authorized_and_hard_block_dominates_uncertainty():
    source = {
        'iran_status': 'ALLOW',
        'kyc_status': 'ALLOW',
        'payment_status': 'USDT',
        'terms_status': 'allowed',
    }
    assert eligibility(source, evidence_ok=False)[0] == 'UNKNOWN'
    blocked = dict(source, iran_status='BLOCK')
    assert eligibility(blocked, evidence_ok=False)[0] == 'BLOCK'
    blocked_terms = dict(source, terms_status='blocked')
    assert eligibility(blocked_terms, evidence_ok=False)[0] == 'BLOCK'

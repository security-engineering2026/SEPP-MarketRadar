from marketradar.models import Opportunity, Evidence, SourcePolicy
from marketradar.evidence import EvidenceEngine
from marketradar.analysis import classify,payment_hint,time_to_money,score

def test_no_evidence_means_reject():
 x=Opportunity('x','Real project','https://x.test/p/1','need python'); assert EvidenceEngine().opportunity(x).status=='REJECT'

def test_verified_evidence_accepts():
 x=Opportunity('x','Need Python automation','https://x.test/p/1','budget $100',evidence_confidence=.9,evidence=[Evidence('opportunity','x','https://x.test/p/1','project-specific listing',.9)])
 assert EvidenceEngine().opportunity(x).status=='ACCEPT'

def test_unknown_eligibility_is_not_execute():
 p=SourcePolicy('x','https://x','generic','marketplace',status='active',iran_status='UNKNOWN',payment_status='USDT')
 assert EvidenceEngine().eligibility(p).status=='UNKNOWN'

def test_payment_and_classification():
 assert payment_hint('pay 50 USDT')=='USDT'; assert classify('Python web scraping automation') in {'web_scraping','business_automation'}

def test_time_to_money_rewards_verified_execute():
 x=Opportunity('x','Small Python fix','u','simple minor bug',budget=100,payment='USDT',eligibility='EXECUTE',evidence_confidence=.9); assert time_to_money(x)>0 and score(x)>50

def test_block_never_scores_high():
 x=Opportunity('x','x','u','',budget=100,payment='USDT',eligibility='BLOCK',evidence_confidence=1); assert score(x)<20

from __future__ import annotations
import tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from marketradar.db import connect
from marketradar.opportunity_signals import extract_signals
from marketradar.opportunity_ranker import rank_opportunity
from marketradar.outcome_learning import record_outcome, update_learning_snapshot
from marketradar.application_adapters import AdapterRegistry, SourceApplicationAdapter


def judge_maker_pass(c, n):
    item={'title':f'Python automation {n}','description':'urgent apply now, 3 proposals, deadline 2026-09-20','category':'python_debugging','budget':500,'eligibility':'EXECUTE','evidence_confidence':.9,'quality_score':.9}
    sig=extract_signals(item)
    assert sig['proposal_count']==3 and sig['deadline_at']
    profile={'skills':['Python'],'learning':{'level':2,'tracks':['software_engineering'],'stretch':True}}
    rank=rank_opportunity({**item,'_signals':sig,'acceptance_probability':.5,'expected_value':250},profile)
    assert 0 <= rank['rank_score'] <= 100
    if n == 1:
        c.execute("INSERT INTO opportunities(source,title,url,description,category,eligibility,state,budget) VALUES('A','seed','https://a/seed','x','python_debugging','EXECUTE','DISCOVERED',500)")
        oid=c.execute('select id from opportunities').fetchone()[0]
        record_outcome(c,oid,'REJECTED','budget')
        record_outcome(c,oid,'ACCEPTED','fit')
        update_learning_snapshot(c,oid)
    assert c.execute('select count(*) from opportunity_learning').fetchone()[0] >= 1
    # Maker action: verify adapter resolution remains deterministic and safe.
    reg=AdapterRegistry(); reg.register_source('A',SourceApplicationAdapter)
    assert reg.resolve('A','https://a/seed').source_key=='A'


def main():
    with tempfile.TemporaryDirectory() as d:
        c=connect(Path(d)/'audit.db')
        for n in range(1,101):
            judge_maker_pass(c,n)
        c.commit()
    print('100-PASS JUDGE→MAKER AUDIT: PASS')

if __name__=='__main__': main()

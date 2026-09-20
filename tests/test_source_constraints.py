from marketradar.db import connect
from marketradar.source_constraints import extract_source_constraints, support_question_for_source


def test_extract_explicit_account_limits():
    text='Free plan allows only one active proposal at a time and maximum 1 open project.'
    rows=extract_source_constraints(text,['https://example.test/terms'])
    got={x['key']:x['value_int'] for x in rows if x['value_int'] is not None}
    assert got['max_pending_applications']==1
    assert got['max_open_projects']==1


def test_unknown_is_support_review_not_block():
    q=support_question_for_source('Iran','UNKNOWN','UNKNOWN',[])
    assert q and 'ایرانی' in q


def test_schema_has_constraint_and_review_tables(tmp_path):
    c=connect(tmp_path/'x.db')
    assert c.execute("select 1 from sqlite_master where type='table' and name='source_constraints'").fetchone()
    assert c.execute("select 1 from sqlite_master where type='table' and name='source_review_queue'").fetchone()
    c.close()

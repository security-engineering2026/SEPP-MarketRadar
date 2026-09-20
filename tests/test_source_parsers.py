from marketradar.source_parsers import parse_rss, parse_remoteok, parse_jobicy, parse_jobremotely

RSS=b'''<?xml version="1.0"?><rss><channel><item><title>Python Engineer</title><link>https://jobs.example/a</link><description>Build APIs</description></item></channel></rss>'''

def test_rss_parser_preserves_listing_evidence():
    rows=parse_rss(RSS,'https://example.com/feed')
    assert rows[0]['title']=='Python Engineer'
    assert rows[0]['url']=='https://jobs.example/a'
    assert rows[0]['evidence'][0]['confidence']==.95

def test_remoteok_parser():
    body=b'{"jobs":[{"position":"Python","url":"https://remoteok.com/abc","description":"remote"}]}'
    assert parse_remoteok(body)[0]['title']=='Python'

def test_jobicy_parser():
    body=b'{"jobs":[{"jobTitle":"Data Engineer","url":"https://jobicy.com/a","jobDescription":"data"}]}'
    assert parse_jobicy(body)[0]['title']=='Data Engineer'

def test_jobremotely_parser():
    body=b'{"jobs":[{"title":"Backend","slug":"backend-1","description":"api"}]}'
    assert parse_jobremotely(body)[0]['url']=='https://jobremotely.io/jobs/backend-1'


def test_parse_rss1_namespaced_items():
    body=b'''<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"><item><title>Python</title><link>https://example.test/job</link><description>Build software</description></item></rdf:RDF>'''
    rows=parse_rss(body,'https://example.test/feed')
    assert rows and rows[0]['title']=='Python'

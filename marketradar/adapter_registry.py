from __future__ import annotations
from .source_parsers import parse_jobicy, parse_jobremotely, parse_remoteok, parse_rss, parse_hh, parse_html_jobs, parse_telegram_bot
PARSERS={
 'rss':lambda body,url:parse_rss(body,url),
 'remoteok_json':lambda body,url:parse_remoteok(body),
 'jobicy_json':lambda body,url:parse_jobicy(body),
 'jobremotely_json':lambda body,url:parse_jobremotely(body,url),
 'hh_json':lambda body,url:parse_hh(body,url),
 'html_jobs':lambda body,url:parse_html_jobs(body,url),
 'telegram_bot_json':lambda body,url:parse_telegram_bot(body,url),
}
def parse(adapter,body,url,generic_parser):
    parser=PARSERS.get(adapter)
    return generic_parser({'body':body,'url':url}) if parser is None else parser(body,url)
def supported(adapter): return adapter in {'json','html','html_jobs','manual_catalog'} or adapter in PARSERS
def content_type_ok(adapter,content_type):
    c=(content_type or '').lower().split(';',1)[0].strip()
    if adapter in {'json','remoteok_json','jobicy_json','jobremotely_json','hh_json','telegram_bot_json'}: return c in {'application/json','application/problem+json','text/json','text/plain',''} or c.endswith('+json')
    if adapter=='rss': return c in {'application/rss+xml','application/atom+xml','application/xml','text/xml','text/rss+xml','text/atom+xml','text/plain',''} or c.endswith('+xml')
    if adapter in {'html','html_jobs'}: return c in {'text/html','application/xhtml+xml','text/plain',''}
    return False

from __future__ import annotations
import json
import re
from defusedxml import ElementTree as ET
from html import unescape
from urllib.parse import urljoin


def _text(value):
    if value is None:
        return ''
    return re.sub(r'\s+', ' ', unescape(str(value))).strip()


def _item(title, url, description='', **extra):
    title, url = _text(title), _text(url)
    if not url.startswith(('http://', 'https://')) or not title:
        return None
    # Keep every adapter inside the Pipeline ingestion contract: titles are capped at
    # 240 chars and descriptions at 10,000 chars. Preserve the leading content rather
    # than emitting an item that will be rejected after acquisition has already succeeded.
    title = title[:240]
    description = _text(description)[:10_000]
    item = {'title': title, 'url': url, 'description': description}
    item.update({k: v for k, v in extra.items() if v not in (None, '')})
    return item


def parse_rss(body: bytes, base_url: str):
    
    if len(body) > 2_000_000: raise ValueError('RSS_TOO_LARGE')
    # ElementTree does not provide the application-level resource controls we need;
    # reject DTD/entity declarations before parsing to prevent entity-expansion abuse.
    head = body[:100_000].upper()
    if b'<!DOCTYPE' in head or b'<!ENTITY' in head:
        raise ValueError('RSS_UNSAFE_XML')
    root = ET.fromstring(body)
    out = []
    rss_nodes = root.findall('.//item')
    rss1_nodes = root.findall('.//{http://purl.org/rss/1.0/}item')
    atom_nodes = root.findall('.//{http://www.w3.org/2005/Atom}entry')
    seen = {id(n) for n in rss_nodes}
    rss_nodes.extend(n for n in rss1_nodes if id(n) not in seen)
    for node in (rss_nodes[:5000] + atom_nodes[:max(0, 5000 - len(rss_nodes))]):
        link = node.findtext('link') or node.findtext('{http://purl.org/rss/1.0/}link')
        if not link:
            link_node = node.find('{http://www.w3.org/2005/Atom}link')
            link = link_node.attrib.get('href') if link_node is not None else None
        title = node.findtext('title') or node.findtext('{http://purl.org/rss/1.0/}title') or node.findtext('{http://www.w3.org/2005/Atom}title')
        desc = (node.findtext('description') or
                node.findtext('{http://purl.org/rss/1.0/}description') or
                node.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or
                node.findtext('{http://www.w3.org/2005/Atom}summary') or
                node.findtext('{http://www.w3.org/2005/Atom}content'))
        item = _item(title, urljoin(base_url, link or ''), desc)
        if item:
            item['evidence'] = [{'kind': 'listing', 'url': item['url'], 'finding': 'public RSS/Atom listing', 'confidence': .95}]
            out.append(item)
    return out[:5000]


def parse_remoteok(body: bytes):
    data = json.loads(body.decode('utf-8'))
    if isinstance(data, dict):
        data = data.get('jobs', data.get('items', []))
    out=[]
    for x in data if isinstance(data, list) else []:
        if not isinstance(x, dict): continue
        item=_item(x.get('position') or x.get('title'), x.get('url') or x.get('apply_url',''), x.get('description',''),
                   budget=x.get('salary_min') or x.get('salary_max'), currency='USD' if x.get('salary_min') or x.get('salary_max') else None)
        if item:
            item['evidence']=[{'kind':'listing','url':item['url'],'finding':'Remote OK public JSON feed','confidence':.95}]
            out.append(item)
    return out[:5000]


def parse_jobicy(body: bytes):
    data=json.loads(body.decode('utf-8'))
    rows=data.get('jobs', data.get('items', [])) if isinstance(data,dict) else data
    out=[]
    for x in rows if isinstance(rows,list) else []:
        if not isinstance(x,dict): continue
        item=_item(x.get('jobTitle') or x.get('title'), x.get('url') or x.get('jobUrl',''), x.get('jobDescription') or x.get('description',''),
                   budget=x.get('salaryMin') or x.get('salaryMax'), currency=x.get('salaryCurrency') or x.get('currency'))
        if item:
            item['evidence']=[{'kind':'listing','url':item['url'],'finding':'Jobicy public remote jobs API','confidence':.95}]
            out.append(item)
    return out[:5000]


def parse_jobremotely(body: bytes, base_url='https://jobremotely.io'):
    data=json.loads(body.decode('utf-8'))
    rows=data.get('jobs', data.get('items', [])) if isinstance(data,dict) else data
    out=[]
    for x in rows if isinstance(rows,list) else []:
        if not isinstance(x,dict): continue
        slug=x.get('slug')
        url=x.get('url') or (urljoin(base_url, '/jobs/'+slug) if slug else '')
        item=_item(x.get('title') or x.get('name'), url, x.get('description',''), budget=x.get('salaryMin') or x.get('salaryMax') or x.get('salary'), currency=x.get('currency') or x.get('salaryCurrency'))
        if item:
            item['evidence']=[{'kind':'listing','url':item['url'],'finding':'JobRemotely public read API','confidence':.95}]
            out.append(item)
    return out[:5000]


class _JobHTMLParser(ET.XMLParser if False else object):
    pass

def parse_hh(body: bytes, base_url: str):
    data=json.loads(body.decode('utf-8'))
    rows=data.get('items',[]) if isinstance(data,dict) else []
    out=[]
    for x in rows:
        if not isinstance(x,dict): continue
        salary=x.get('salary') or {}
        item=_item(x.get('name'), x.get('alternate_url') or x.get('url',''), x.get('snippet',{}).get('requirement','') if isinstance(x.get('snippet'),dict) else '', budget=salary.get('from') or salary.get('to'), currency=salary.get('currency'))
        if item:
            item['country']=x.get('area',{}).get('name') if isinstance(x.get('area'),dict) else None
            item['location']=x.get('area',{}).get('name') if isinstance(x.get('area'),dict) else None
            item['evidence']=[{'kind':'listing','url':item['url'],'finding':'HeadHunter public vacancy API response','confidence':.92}]
            out.append(item)
    return out[:5000]

from html.parser import HTMLParser
class _SimpleHTMLJobs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.links=[]; self.current=None; self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=='a':
            d=dict(attrs); href=d.get('href')
            if href and href.startswith(('http://','https://','/')):
                self.current=href; self.text=[]
    def handle_data(self,data):
        if self.current is not None:self.text.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=='a' and self.current is not None:
            title=_text(' '.join(self.text)); href=self.current
            if title:self.links.append((href,title))
            self.current=None; self.text=[]

def parse_html_jobs(body: bytes, base_url: str):
    if len(body)>2_000_000: raise ValueError('HTML_TOO_LARGE')
    parser=_SimpleHTMLJobs(); parser.feed(body.decode('utf-8','replace'))
    out=[]; seen=set()
    for href,title in parser.links:
        url=urljoin(base_url,href)
        if url in seen: continue
        low=(title+' '+url).lower()
        if not any(k in low for k in ('job','vacancy','position','career','developer','engineer','python','software','automation')): continue
        if len(title)<3: continue
        seen.add(url); out.append(_item(title,url,'Public job listing discovered from HTML page.'))
        if len(out)>=1000: break
    return [x for x in out if x]

def parse_telegram_bot(body: bytes, base_url: str):
    data=json.loads(body.decode('utf-8'))
    if not isinstance(data,dict) or not data.get('ok'): raise ValueError('TELEGRAM_API_RESPONSE_INVALID')
    out=[]
    for result in data.get('result',[]):
        msg=result.get('channel_post') or result.get('message') or result.get('edited_channel_post')
        if not isinstance(msg,dict): continue
        text=_text(msg.get('text') or msg.get('caption') or '')
        if not text: continue
        chat=msg.get('chat') or {}; username=chat.get('username')
        mid=msg.get('message_id'); url=f"https://t.me/{username}/{mid}" if username and mid else base_url
        item=_item(text[:160],url,text)
        if item:item['evidence']=[{'kind':'telegram','url':url,'finding':'Authorized Telegram Bot API message','confidence':.9}]; out.append(item)
    return out[:5000]

from __future__ import annotations
import hashlib, ipaddress, json, random, socket, ssl, time, http.client
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urljoin

@dataclass(frozen=True)
class Source:
    name: str
    base_url: str
    adapter: str = "json"
    status: str = "active"
    allow_hosts: tuple = ()
    access_scope: str = "public"
    headers: tuple = ()

    def __post_init__(self):
        if self.access_scope not in {"public", "local", "authorized", "private"}:
            raise ValueError('ACCESS_SCOPE_INVALID')

def _is_public_ip(value: str) -> bool:
    try: ip = ipaddress.ip_address(value)
    except ValueError: return False
    return value != "0.0.0.0" and not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified)

class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host, port, pinned_ip, timeout, **kwargs):
        super().__init__(pinned_ip, port, timeout=timeout, **kwargs)
        self._pinned_ip = pinned_ip
        self._server_hostname = host
    def connect(self):
        self.sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)

class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, port, pinned_ip, timeout, context=None, **kwargs):
        super().__init__(pinned_ip, port, timeout=timeout, context=context or ssl.create_default_context(), **kwargs)
        self._pinned_ip = pinned_ip
        self._server_hostname = host
    def connect(self):
        self.sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self._server_hostname)

class Federation:
    def __init__(self, sources, timeout=5, max_workers=8, retries=2, max_bytes=2_000_000, max_redirects=5):
        self.sources={s.name:s for s in sources}; self.timeout=max(.1,float(timeout)); self.max_workers=max(1,min(int(max_workers),32)); self.retries=max(0,int(retries)); self.max_bytes=max(1024,int(max_bytes)); self.max_redirects=max(0,min(int(max_redirects),10))

    def _validate_target(self, source, target, require_public=None):
        if source.access_scope not in {'public','local','authorized','private'}: raise ValueError('ACCESS_SCOPE_INVALID')
        if not isinstance(target,str) or len(target)>4096: raise ValueError('URL_TOO_LONG')
        p=urlparse(target); allowed={h.lower().rstrip('.') for h in (source.allow_hosts or (urlparse(source.base_url).hostname,)) if h}; host=(p.hostname or '').lower().rstrip('.')
        if p.scheme not in ('http','https') or host not in allowed or not host or p.username or p.password: raise ValueError('HOST_BOUNDARY_BLOCK')
        if require_public is None: require_public=source.access_scope in {'public','authorized'}
        try: literal=ipaddress.ip_address(host)
        except ValueError: literal=None
        if literal is not None:
            if require_public and not _is_public_ip(host): raise ValueError('PRIVATE_IP_BLOCK')
            return p
        try:
            addresses={info[4][0] for info in socket.getaddrinfo(host,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM)}
        except OSError as exc: raise ValueError('DNS_RESOLUTION_FAILED') from exc
        if not addresses: raise ValueError('DNS_RESOLUTION_FAILED')
        if require_public and not all(_is_public_ip(a) for a in addresses): raise ValueError('PRIVATE_IP_BLOCK')
        return p

    def _resolve_pinned_ip(self, source, parsed):
        host=parsed.hostname
        try:
            literal=ipaddress.ip_address(host)
        except ValueError: literal=None
        if literal is not None:
            if source.access_scope in {'public','authorized'} and not _is_public_ip(host): raise ValueError('PRIVATE_IP_BLOCK')
            return host
        try:
            addresses=[info[4][0] for info in socket.getaddrinfo(host,parsed.port or (443 if parsed.scheme=='https' else 80),type=socket.SOCK_STREAM)]
        except OSError as exc: raise ValueError('DNS_RESOLUTION_FAILED') from exc
        if not addresses: raise ValueError('DNS_RESOLUTION_FAILED')
        if source.access_scope in {'public','authorized'} and not all(_is_public_ip(a) for a in addresses): raise ValueError('PRIVATE_IP_BLOCK')
        return addresses[0]

    @staticmethod
    def _host_header(parsed):
        host=parsed.hostname
        if ':' in host: host=f'[{host}]'
        default=(parsed.scheme=='http' and (parsed.port in (None,80))) or (parsed.scheme=='https' and (parsed.port in (None,443)))
        return host if default else f'{host}:{parsed.port}'

    def _open_once(self, source, target):
        parsed=self._validate_target(source,target)
        pinned=self._resolve_pinned_ip(source,parsed)
        port=parsed.port or (443 if parsed.scheme=='https' else 80)
        conn_cls=_PinnedHTTPSConnection if parsed.scheme=='https' else _PinnedHTTPConnection
        conn=conn_cls(parsed.hostname,port,pinned,self.timeout)
        path=(parsed.path or '/') + (('?' + parsed.query) if parsed.query else '')
        try:
            headers={'User-Agent':'SEPP-MarketRadar/16.1.1','Host':self._host_header(parsed),'Accept':'application/json, application/rss+xml, application/atom+xml, application/xml, application/xhtml+xml, text/html, text/xml, text/plain'}
            for k,v in source.headers:
                if isinstance(k,str) and isinstance(v,str) and k.lower() not in {'host','content-length'}: headers[k]=v
            conn.request('GET',path,headers=headers)
            response=conn.getresponse()
            if 300 <= response.status < 400:
                location=response.getheader('Location')
                response.read(4096); conn.close()
                if not location: raise ValueError('REDIRECT_WITHOUT_LOCATION')
                return response.status, None, None, urljoin(target,location)
            body=response.read(self.max_bytes+1)
            if len(body)>self.max_bytes: conn.close(); raise ValueError('RESPONSE_TOO_LARGE')
            ctype=(response.getheader('Content-Type') or '').lower()
            status=response.status; final=target
            if status < 200 or status >= 300:
                err=HTTPError(target,status,response.reason,response.headers,None)
                conn.close(); raise err
            return status,ctype,body,None
        except Exception:
            try: conn.close()
            except Exception: pass
            raise

    def fetch(self,name,url=None):
        if name not in self.sources: raise KeyError('SOURCE_NOT_REGISTERED')
        source=self.sources[name]; target=url or source.base_url; self._validate_target(source,target); last_error=None
        for attempt in range(self.retries+1):
            try:
                started=time.monotonic(); current=target; redirects=0
                while True:
                    self._validate_target(source,current)
                    status,ctype,body,next_url=self._open_once(source,current)
                    if next_url is None:
                        return {'source':name,'url':current,'status':status,'content_type':ctype,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'elapsed_ms':round((time.monotonic()-started)*1000,2),'body':body,'attempts':attempt+1}
                    redirects += 1
                    if redirects > self.max_redirects: raise ValueError('TOO_MANY_REDIRECTS')
                    current=next_url
            except (HTTPError,URLError,TimeoutError,OSError,ValueError) as exc:
                last_error=exc
                try: setattr(exc,'attempts',attempt+1)
                except Exception: pass
                retryable=(isinstance(exc,HTTPError) and exc.code in (408,425,429,500,502,503,504)) or (not isinstance(exc,HTTPError) and isinstance(exc,(URLError,TimeoutError,OSError)))
                if attempt < self.retries and retryable:
                    delay=min(.25*(2**attempt),2.0)+random.uniform(0,.1)
                    if isinstance(exc,HTTPError) and exc.code in (429,503):
                        try: delay=min(max(float(exc.headers.get('Retry-After','0')),delay),10.0)
                        except (TypeError,ValueError): pass
                    time.sleep(delay)
                else: break
        raise last_error

    def verify_many(self,names=None,progress_callback=None,stop_event=None,validation_callback=None):
        selected=list(names) if names is not None else list(self.sources); results=[]
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures={pool.submit(self.fetch,name):name for name in selected if name in self.sources}
            for future in as_completed(futures):
                name=futures[future]
                if future.cancelled(): continue
                try:
                    obs=future.result(); result={'source':name,'status':'OK','http_status':obs['status'],'elapsed_ms':obs['elapsed_ms'],'bytes':obs['bytes'],'sha256':obs['sha256'],'attempts':obs['attempts'],'error':None,'parse_ok':None,'parsed_count':0,'parse_error':None}
                    if validation_callback:
                        try: result.update(validation_callback(name,obs) or {})
                        except Exception as exc: result.update(parse_ok=False,parse_error=type(exc).__name__+': '+str(exc))
                except Exception as exc:
                    result={'source':name,'status':'ERROR','http_status':getattr(exc,'code',None),'elapsed_ms':None,'bytes':0,'sha256':None,'attempts':getattr(exc,'attempts',1),'error':type(exc).__name__+': '+str(exc),'parse_ok':False,'parsed_count':0,'parse_error':None}
                results.append(result)
                if progress_callback: progress_callback(result)
                if stop_event and stop_event.is_set():
                    for pending in futures:
                        if not pending.done(): pending.cancel()
        return sorted(results,key=lambda x:x['source'])

    @staticmethod
    def parse_json(obs):
        data=json.loads(obs['body'].decode('utf-8')); items=data if isinstance(data,list) else data.get('items') if isinstance(data,dict) else None
        if not isinstance(items,list): raise ValueError('JSON_SCHEMA_UNSUPPORTED')
        return [i for i in items if isinstance(i,dict) and isinstance(i.get('url'),str) and i['url'].startswith(('http://','https://'))][:5000]

import hashlib, hmac, json, time, secrets

class AndroidBridge:
    def __init__(self, secret=None, connection=None):
        self.secret = secret.encode() if secret else None
        self.c = connection
        if self.c is not None:
            self.c.executescript('''CREATE TABLE IF NOT EXISTS android_devices(device_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, bound_at TEXT NOT NULL, last_seen_at TEXT, enabled INTEGER NOT NULL DEFAULT 1);''')
            self.c.commit()
    def bind_device(self, device_id: str, token: str):
        if not device_id or not token: raise ValueError('ANDROID_DEVICE_BINDING_INVALID')
        digest=hashlib.sha256(token.encode()).hexdigest(); now=int(time.time())
        self.c.execute('INSERT INTO android_devices(device_id,token_hash,bound_at,last_seen_at,enabled) VALUES(?,?,?,?,1) ON CONFLICT(device_id) DO UPDATE SET token_hash=excluded.token_hash,last_seen_at=excluded.last_seen_at,enabled=1',(device_id,digest,now,now)); self.c.commit(); return {'device_id':device_id,'bound_at':now}

    def authorize_device(self, device_id: str, token: str) -> bool:
        if self.c is None: return False
        row=self.c.execute('SELECT token_hash,enabled FROM android_devices WHERE device_id=?',(device_id,)).fetchone()
        ok=bool(row and row['enabled'] and hmac.compare_digest(row['token_hash'],hashlib.sha256(token.encode()).hexdigest()))
        if ok: self.c.execute('UPDATE android_devices SET last_seen_at=? WHERE device_id=?',(int(time.time()),device_id)); self.c.commit()
        return ok

    @property
    def enabled(self): return bool(self.secret)
    def sign(self, payload):
        if not self.secret: raise RuntimeError('ANDROID_BRIDGE_DISABLED')
        raw=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
        return hmac.new(self.secret,raw,hashlib.sha256).hexdigest()
    def envelope(self,kind,payload,ttl=60):
        if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0 or ttl > 3600: raise ValueError('INVALID_TTL')
        if not isinstance(kind,str) or not kind.strip() or len(kind)>64: raise ValueError('INVALID_MESSAGE_KIND')
        now=int(time.time()); msg={'message_id':secrets.token_hex(16),'kind':kind,'payload':payload,'issued_at':now,'expires_at':now+ttl}; msg['signature']=self.sign(msg)
        if self.c is not None:
            self.c.execute('INSERT INTO android_messages(message_id,kind,issued_at,expires_at,consumed_at) VALUES(?,?,?,?,NULL)',(msg['message_id'],kind,now,now+ttl))
        return msg
    def verify(self,msg,consume=False):
        if not self.enabled or not isinstance(msg,dict): return False
        try:
            now=int(time.time()); issued_value=msg.get('issued_at'); expires_value=msg.get('expires_at')
            if isinstance(issued_value,bool) or not isinstance(issued_value,int) or isinstance(expires_value,bool) or not isinstance(expires_value,int): return False
            issued=issued_value; expires=expires_value; mid=msg.get('message_id')
            if not isinstance(mid,str) or len(mid)!=32: return False
            if issued > now + 30 or expires < now or expires <= issued or expires-issued > 3600: return False
            sig=msg.get('signature'); body={k:v for k,v in msg.items() if k!='signature'}
            if not isinstance(sig,str) or not hmac.compare_digest(sig,self.sign(body)): return False
            if self.c is None: return True
            row=self.c.execute('SELECT consumed_at,issued_at,expires_at,kind FROM android_messages WHERE message_id=?',(mid,)).fetchone()
            if row is None or row['issued_at'] != issued or row['expires_at'] != expires or row['kind'] != msg.get('kind') or row['consumed_at'] is not None: return False
            if consume:
                self.c.execute('UPDATE android_messages SET consumed_at=? WHERE message_id=? AND consumed_at IS NULL',(now,mid))
                return self.c.execute('SELECT changes()').fetchone()[0] == 1
            return True
        except (TypeError,ValueError): return False

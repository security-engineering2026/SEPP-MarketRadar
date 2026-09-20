from __future__ import annotations
import os, smtplib, ssl, imaplib, email as email_lib, re
from email.message import EmailMessage
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def ensure_schema(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS email_accounts(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, address TEXT NOT NULL, provider TEXT,
      smtp_host TEXT, smtp_port INTEGER DEFAULT 465, imap_host TEXT, imap_port INTEGER DEFAULT 993,
      username TEXT, password_env TEXT, active INTEGER DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS email_drafts(
      id INTEGER PRIMARY KEY, opportunity_id INTEGER, account_id INTEGER, recipient TEXT NOT NULL, cc TEXT, bcc TEXT,
      subject TEXT NOT NULL, body TEXT NOT NULL, message_id TEXT, status TEXT NOT NULL DEFAULT 'DRAFT', requires_approval INTEGER DEFAULT 1,
      created_at TEXT NOT NULL, approved_at TEXT, sent_at TEXT, result TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_email_drafts_status ON email_drafts(status,created_at);
    CREATE TABLE IF NOT EXISTS email_messages(
      id INTEGER PRIMARY KEY, account_id INTEGER, opportunity_id INTEGER, message_id TEXT, in_reply_to TEXT,
      thread_refs TEXT, sender TEXT, subject TEXT, body TEXT, received_at TEXT NOT NULL, status_intent TEXT,
      confidence REAL DEFAULT 0, processed INTEGER DEFAULT 0, created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_email_messages_opp ON email_messages(opportunity_id,received_at);
    ''')
    cols={r[1] for r in c.execute('PRAGMA table_info(email_drafts)').fetchall()}
    if 'message_id' not in cols:
        c.execute('ALTER TABLE email_drafts ADD COLUMN message_id TEXT')
    c.commit()


def add_account(c, name,address,provider=None,smtp_host=None,smtp_port=465,imap_host=None,imap_port=993,username=None,password_env=None):
    ts=now()
    c.execute('''INSERT INTO email_accounts(name,address,provider,smtp_host,smtp_port,imap_host,imap_port,username,password_env,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET address=excluded.address,provider=excluded.provider,smtp_host=excluded.smtp_host,smtp_port=excluded.smtp_port,imap_host=excluded.imap_host,imap_port=excluded.imap_port,username=excluded.username,password_env=excluded.password_env,updated_at=excluded.updated_at''',
      (name,address,provider,smtp_host,int(smtp_port),imap_host,int(imap_port),username,password_env,ts,ts))
    c.commit()


def create_draft(c,recipient,subject,body,opportunity_id=None,account_id=None,cc=None,bcc=None):
    c.execute('INSERT INTO email_drafts(opportunity_id,account_id,recipient,cc,bcc,subject,body,created_at) VALUES(?,?,?,?,?,?,?,?)',(opportunity_id,account_id,recipient,cc,bcc,subject,body,now()))
    c.commit(); return c.execute('SELECT last_insert_rowid()').fetchone()[0]


def approve(c,draft_id):
    c.execute('UPDATE email_drafts SET status="APPROVED",approved_at=? WHERE id=? AND status="DRAFT"',(now(),draft_id)); c.commit()


def send(c,draft_id):
    row=c.execute('SELECT d.*,a.smtp_host,a.smtp_port,a.username,a.password_env,a.address FROM email_drafts d LEFT JOIN email_accounts a ON a.id=d.account_id WHERE d.id=?',(draft_id,)).fetchone()
    if not row: raise ValueError('EMAIL_DRAFT_NOT_FOUND')
    if row['status']!='APPROVED': raise PermissionError('EMAIL_APPROVAL_REQUIRED')
    if not row['smtp_host'] or not row['password_env']: raise ValueError('SMTP_NOT_CONFIGURED')
    password=os.getenv(row['password_env'])
    if not password: raise ValueError('SMTP_SECRET_MISSING')
    msg=EmailMessage()
    msg_id=f'<mr-{draft_id}-{int(datetime.now(timezone.utc).timestamp()*1000)}@marketradar.local>'
    msg['Message-ID']=msg_id; msg['From']=row['address']; msg['To']=row['recipient']
    if row['cc']: msg['Cc']=row['cc']
    if row['bcc']: msg['Bcc']=row['bcc']
    msg['Subject']=row['subject']; msg.set_content(row['body'])
    with smtplib.SMTP_SSL(row['smtp_host'],row['smtp_port'],context=ssl.create_default_context(),timeout=20) as s:
        if row['username']: s.login(row['username'],password)
        s.send_message(msg)
    c.execute('UPDATE email_drafts SET status="SENT",sent_at=?,result=?,message_id=? WHERE id=?',(now(),'SMTP_OK',msg_id,draft_id)); c.commit()


def _norm_subject(value):
    return re.sub(r'^\s*((re|fw|fwd)\s*:\s*)+', '', str(value or ''), flags=re.I).strip().lower()


def _status_intent(subject, body):
    text=(str(subject or '')+' '+str(body or '')).lower()
    if any(x in text for x in ('not selected','rejected','declined','unsuccessful','رد شد','رد درخواست','پذیرفته نشد')):
        return 'REJECTED',0.96
    if any(x in text for x in ('accepted','congratulations','you are selected','awarded','offer','پذیرفته شدید','قبول شد','برنده شدید')):
        return 'ACCEPTED',0.96
    if any(x in text for x in ('interview','meeting','clarification','negotiation','مصاحبه','جلسه','مذاکره')):
        return 'NEGOTIATION',0.90
    return 'MESSAGE_RECEIVED',0.82


def _match_opportunity(c, in_reply_to, refs, subject):
    if in_reply_to:
        q=c.execute('SELECT opportunity_id FROM email_drafts WHERE message_id=? AND opportunity_id IS NOT NULL ORDER BY id DESC LIMIT 1',(in_reply_to,)).fetchone()
        if q: return int(q['opportunity_id'])
    for ref in re.findall(r'<[^>]+>', str(refs or '')):
        q=c.execute('SELECT opportunity_id FROM email_drafts WHERE message_id=? AND opportunity_id IS NOT NULL ORDER BY id DESC LIMIT 1',(ref,)).fetchone()
        if q: return int(q['opportunity_id'])
    ns=_norm_subject(subject)
    if ns:
        q=c.execute('SELECT opportunity_id FROM email_drafts WHERE lower(subject)=? AND opportunity_id IS NOT NULL ORDER BY id DESC LIMIT 1',(ns,)).fetchone()
        if q: return int(q['opportunity_id'])
    return None


def process_inbox_messages(c, account_id, messages):
    from .economic_loop import add_communication, record_status_observation
    results=[]
    for m in messages:
        oid=_match_opportunity(c,m.get('in_reply_to'),m.get('references'),m.get('subject'))
        intent,confidence=_status_intent(m.get('subject'),m.get('body'))
        c.execute('''INSERT INTO email_messages(account_id,opportunity_id,message_id,in_reply_to,thread_refs,sender,subject,body,received_at,status_intent,confidence,processed,created_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (account_id,oid,m.get('message_id'),m.get('in_reply_to'),m.get('references'),m.get('from'),m.get('subject'),m.get('body'),m.get('date') or now(),intent,confidence,0,now()))
        mid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
        transitioned=False
        if oid is not None:
            add_communication(c,oid,'EMAIL','INBOUND',m.get('subject'),m.get('body'),m.get('message_id'),'email_message:'+str(mid),m.get('date') or now())
            result=record_status_observation(c,oid,'EMAIL',intent,confidence,evidence_url=None,evidence_text=m.get('subject') or '',external_ref=m.get('message_id'),actor='email_monitor')
            transitioned=bool(result.get('accepted'))
        c.execute('UPDATE email_messages SET processed=1 WHERE id=?',(mid,)); c.commit()
        results.append({'message_id':m.get('message_id'),'opportunity_id':oid,'intent':intent,'confidence':confidence,'transitioned':transitioned})
    return results


def poll_inbox(c, account_id, limit=20, process=True):
    row=c.execute('SELECT * FROM email_accounts WHERE id=?',(account_id,)).fetchone()
    if not row or not row['imap_host'] or not row['password_env']: raise ValueError('IMAP_NOT_CONFIGURED')
    pw=os.getenv(row['password_env'])
    if not pw: raise ValueError('IMAP_SECRET_MISSING')
    out=[]
    with imaplib.IMAP4_SSL(row['imap_host'],row['imap_port']) as im:
        im.login(row['username'] or row['address'],pw); im.select('INBOX'); typ,data=im.search(None,'UNSEEN'); ids=data[0].split()[-int(limit):]
        for mid in ids:
            typ,msgdata=im.fetch(mid,'(RFC822)'); raw=msgdata[0][1]; msg=email_lib.message_from_bytes(raw)
            body=''
            if msg.is_multipart():
                parts=[p for p in msg.walk() if p.get_content_type()=='text/plain' and not p.get('Content-Disposition')]
                if parts:
                    payload=parts[0].get_payload(decode=True)
                    body=payload.decode(parts[0].get_content_charset() or 'utf-8',errors='replace') if isinstance(payload,bytes) else str(payload or '')
            else:
                payload=msg.get_payload(decode=True)
                body=payload.decode(msg.get_content_charset() or 'utf-8',errors='replace') if isinstance(payload,bytes) else str(payload or '')
            out.append({'message_id':msg.get('Message-ID') or mid.decode(errors='ignore'),'in_reply_to':msg.get('In-Reply-To'),'references':msg.get('References'),'from':msg.get('From'),'subject':msg.get('Subject'),'date':msg.get('Date'),'body':body[:20000]})
    return process_inbox_messages(c,account_id,out) if process else out

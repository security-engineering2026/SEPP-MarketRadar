from __future__ import annotations
from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat()

def ensure_schema(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS notifications(
      id INTEGER PRIMARY KEY, channel TEXT NOT NULL DEFAULT 'APP', kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
      opportunity_id INTEGER, priority TEXT NOT NULL DEFAULT 'INFO', due_at TEXT, status TEXT NOT NULL DEFAULT 'UNREAD',
      created_at TEXT NOT NULL, read_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status,created_at);
    '''); c.commit()

def create(c, kind, title, body, opportunity_id=None, priority='INFO', due_at=None, channel='APP'):
    c.execute('INSERT INTO notifications(channel,kind,title,body,opportunity_id,priority,due_at,status,created_at) VALUES(?,?,?,?,?,?,?,"UNREAD",?)',(channel,kind,title,body,opportunity_id,priority,due_at,now())); c.commit(); return c.execute('SELECT last_insert_rowid()').fetchone()[0]

def unread(c, limit=100): return c.execute('SELECT * FROM notifications WHERE status="UNREAD" ORDER BY CASE priority WHEN "CRITICAL" THEN 0 WHEN "HIGH" THEN 1 WHEN "WARN" THEN 2 ELSE 3 END,created_at DESC LIMIT ?',(int(limit),)).fetchall()

def mark_read(c, notification_id): c.execute('UPDATE notifications SET status="READ",read_at=? WHERE id=?',(now(),notification_id)); c.commit()

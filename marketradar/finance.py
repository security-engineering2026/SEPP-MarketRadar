from __future__ import annotations
import csv, io, json, re, zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.sax.saxutils import escape


def now(): return datetime.now(timezone.utc).isoformat()

SCHEMA = '''
CREATE TABLE IF NOT EXISTS financial_accounts(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, account_type TEXT NOT NULL DEFAULT 'BANK',
  institution TEXT, account_number TEXT, iban TEXT, wallet TEXT, currency TEXT NOT NULL, holder_name TEXT,
  preferred_for_sources TEXT, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_account_routes(
  source TEXT PRIMARY KEY, account_id INTEGER NOT NULL, preferred INTEGER NOT NULL DEFAULT 1,
  reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS finance_ledger(
  id INTEGER PRIMARY KEY, opportunity_id INTEGER, account_id INTEGER, entry_type TEXT NOT NULL,
  amount REAL NOT NULL, currency TEXT NOT NULL, gross_amount REAL, platform_fee REAL DEFAULT 0,
  network_fee REAL DEFAULT 0, other_cost REAL DEFAULT 0, client TEXT, project TEXT, source TEXT,
  network TEXT, wallet TEXT, tx_hash TEXT, payment_ref TEXT, occurred_at TEXT NOT NULL,
  notes TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_finance_ledger_period ON finance_ledger(occurred_at,currency,entry_type);
CREATE TABLE IF NOT EXISTS finance_reports(
  id INTEGER PRIMARY KEY, period_type TEXT NOT NULL, period_key TEXT NOT NULL, account_id INTEGER,
  generated_at TEXT NOT NULL, report_json TEXT NOT NULL, html_path TEXT, pdf_path TEXT, csv_path TEXT,
  xlsx_path TEXT, markdown_path TEXT, UNIQUE(period_type,period_key,account_id)
);
'''


def ensure_schema(c):
    c.executescript(SCHEMA)
    cols={r[1] for r in c.execute('PRAGMA table_info(financial_accounts)')}
    if 'wallet' not in cols: c.execute('ALTER TABLE financial_accounts ADD COLUMN wallet TEXT')
    c.commit()


def add_account(c, name, currency, account_type='BANK', institution=None, account_number=None, iban=None, wallet=None, holder_name=None, preferred_for_sources=None):
    ts=now()
    c.execute('''INSERT INTO financial_accounts(name,account_type,institution,account_number,iban,wallet,currency,holder_name,preferred_for_sources,created_at,updated_at)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(name) DO UPDATE SET account_type=excluded.account_type,institution=excluded.institution,
                 account_number=excluded.account_number,iban=excluded.iban,wallet=excluded.wallet,currency=excluded.currency,holder_name=excluded.holder_name,
                 preferred_for_sources=excluded.preferred_for_sources,updated_at=excluded.updated_at''',
              (name,account_type,institution,account_number,iban,wallet,currency,holder_name,json.dumps(preferred_for_sources or [],ensure_ascii=False),ts,ts))
    c.commit(); return c.execute('SELECT * FROM financial_accounts WHERE name=?',(name,)).fetchone()


def route_source_account(c, source, account_id, reason=None):
    if not c.execute('SELECT 1 FROM financial_accounts WHERE id=? AND active=1',(account_id,)).fetchone(): raise ValueError('ACCOUNT_NOT_ACTIVE')
    ts=now(); c.execute('''INSERT INTO source_account_routes(source,account_id,reason,created_at,updated_at) VALUES(?,?,?,?,?)
      ON CONFLICT(source) DO UPDATE SET account_id=excluded.account_id,reason=excluded.reason,updated_at=excluded.updated_at''',(source,account_id,reason,ts,ts)); c.commit()


def account_for_source(c, source):
    row=c.execute('SELECT account_id FROM source_account_routes WHERE source=? AND preferred=1',(source,)).fetchone()
    if row: return c.execute('SELECT * FROM financial_accounts WHERE id=?',(row['account_id'],)).fetchone()
    return None


def record_entry(c, entry_type, amount, currency, opportunity_id=None, account_id=None, gross_amount=None, platform_fee=0, network_fee=0, other_cost=0, client=None, project=None, source=None, network=None, wallet=None, tx_hash=None, payment_ref=None, occurred_at=None, notes=None):
    if float(amount) == 0: raise ValueError('ZERO_FINANCE_ENTRY')
    if account_id is not None and not c.execute('SELECT 1 FROM financial_accounts WHERE id=?',(account_id,)).fetchone(): raise ValueError('ACCOUNT_NOT_FOUND')
    ts=occurred_at or now()
    c.execute('''INSERT INTO finance_ledger(opportunity_id,account_id,entry_type,amount,currency,gross_amount,platform_fee,network_fee,other_cost,client,project,source,network,wallet,tx_hash,payment_ref,occurred_at,notes,created_at)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (opportunity_id,account_id,entry_type,float(amount),currency,gross_amount,platform_fee,network_fee,other_cost,client,project,source,network,wallet,tx_hash,payment_ref,ts,notes,now())); c.commit()
    return c.execute('SELECT * FROM finance_ledger WHERE id=last_insert_rowid()').fetchone()


def record_payment_to_account(c, opportunity_id, amount, currency, payment_ref, account_id=None, network=None, wallet=None, tx_hash=None, client=None, project=None, source=None, received_at=None, verification='VERIFIED', notes=None):
    if account_id is None:
        row=c.execute('SELECT source FROM opportunities WHERE id=?',(opportunity_id,)).fetchone(); account=account_for_source(c,row['source']) if row else None; account_id=account['id'] if account else None
    return record_entry(c,'INCOME',amount,currency,opportunity_id,account_id,gross_amount=amount,client=client,project=project,source=source,network=network,wallet=wallet,tx_hash=tx_hash,payment_ref=payment_ref,occurred_at=received_at,notes=json.dumps({'verification':verification,'notes':notes},ensure_ascii=False))


def _period(period_type, when=None):
    d=(when or datetime.now(timezone.utc)).date()
    if period_type=='weekly':
        start=d-timedelta(days=d.weekday()); end=start+timedelta(days=7)
    elif period_type=='monthly':
        start=d.replace(day=1); end=(start.replace(day=28)+timedelta(days=4)).replace(day=1)
    elif period_type=='quarterly':
        month=((d.month-1)//3)*3+1; start=d.replace(month=month,day=1); end=(start.replace(month=month+2 if month<=10 else 12,day=28)+timedelta(days=4)).replace(day=1)
    elif period_type=='annual':
        start=d.replace(month=1,day=1); end=d.replace(year=d.year+1,month=1,day=1)
    else: raise ValueError('INVALID_PERIOD_TYPE')
    return start.isoformat(), end.isoformat(), f'{start.isoformat()}__{end.isoformat()}'


def period_report(c, period_type='monthly', when=None, account_id=None):
    start,end,key=_period(period_type,when)
    params=[start,end]; account_clause=''
    if account_id is not None: account_clause=' AND account_id=?'; params.append(account_id)
    rows=c.execute(f'''SELECT entry_type,currency,COUNT(*) count_entries,SUM(amount) amount,SUM(COALESCE(platform_fee,0)+COALESCE(network_fee,0)+COALESCE(other_cost,0)) costs
                       FROM finance_ledger WHERE occurred_at>=? AND occurred_at<?{account_clause} GROUP BY entry_type,currency ORDER BY currency,entry_type''',params).fetchall()
    revenue_rows=c.execute(f'''SELECT COUNT(*) n,SUM(amount) total,currency FROM finance_ledger WHERE occurred_at>=? AND occurred_at<? AND entry_type='INCOME'{account_clause} GROUP BY currency''',params).fetchall()
    application_stats=c.execute('''SELECT COUNT(*) total,
      SUM(CASE WHEN state='SUBMITTED' THEN 1 ELSE 0 END) submitted,
      SUM(CASE WHEN state='ACCEPTED' THEN 1 ELSE 0 END) accepted,
      SUM(CASE WHEN state='REJECTED' THEN 1 ELSE 0 END) rejected,
      SUM(CASE WHEN state='DELIVERED' THEN 1 ELSE 0 END) delivered,
      SUM(CASE WHEN state='PAID' THEN 1 ELSE 0 END) paid
      FROM opportunities WHERE COALESCE(last_seen,first_seen)>=? AND COALESCE(last_seen,first_seen)<?''',(start,end)).fetchone()
    accounts=[dict(r) for r in c.execute('SELECT * FROM financial_accounts WHERE active=1 ORDER BY name').fetchall()]
    balances=[]
    for a in accounts:
        bal=c.execute('SELECT COALESCE(SUM(amount),0) v FROM finance_ledger WHERE account_id=? AND currency=?',(a['id'],a['currency'])).fetchone()['v']
        balances.append({'account_id':a['id'],'account':a['name'],'currency':a['currency'],'balance':float(bal),'iban':a.get('iban'),'account_number':a.get('account_number'),'institution':a.get('institution'),'wallet':a.get('wallet')})
    applications=c.execute('SELECT id,source,title,url,budget,currency,state,rejection_reason,first_seen,last_seen FROM opportunities WHERE COALESCE(last_seen,first_seen)>=? AND COALESCE(last_seen,first_seen)< ? ORDER BY COALESCE(last_seen,first_seen) DESC',(start,end)).fetchall()
    routes=c.execute('SELECT sar.source,fa.name account,fa.currency,fa.iban,fa.account_number,fa.institution,fa.wallet,sar.reason FROM source_account_routes sar JOIN financial_accounts fa ON fa.id=sar.account_id ORDER BY sar.source').fetchall()
    return {'period_type':period_type,'period_key':key,'start':start,'end':end,'generated_at':now(),'application_stats':dict(application_stats),'applications':[dict(x) for x in applications],'ledger':[dict(r) for r in rows],'revenue':[dict(r) for r in revenue_rows],'account_balances':balances,'source_account_routes':[dict(x) for x in routes]}


def _report_text(report):
    lines=[f"MarketRadar Financial Report — {report['period_type']} — {report['start']} → {report['end']}","", "APPLICATIONS"]
    lines += [f"{k}: {v}" for k,v in report['application_stats'].items()]
    lines += ["", "LEDGER"]
    for r in report['ledger']: lines.append(f"{r['currency']} | {r['entry_type']} | entries={r['count_entries']} | amount={r['amount']} | costs={r['costs']}")
    lines += ["", "ACCOUNT BALANCES"]
    for a in report['account_balances']: lines.append(f"{a['account']} | {a['currency']} | {a['balance']}")
    return lines


def export_report(c, report, out_dir: Path):
    out_dir.mkdir(parents=True,exist_ok=True); stem=f"finance-{report['period_type']}-{report['start']}"
    payload=json.dumps(report,ensure_ascii=False,indent=2,default=str)
    (out_dir/(stem+'.json')).write_text(payload,encoding='utf-8')
    md='\n'.join(['# '+_report_text(report)[0],'','## Applications']+[f"- **{k}**: {v}" for k,v in report['application_stats'].items()]+['','## Ledger']+[f"- {r['currency']} / {r['entry_type']}: {r['amount']} (costs {r['costs']})" for r in report['ledger']]+['','## Accounts']+[f"- {a['account']}: {a['balance']} {a['currency']}" for a in report['account_balances']])
    md_path=out_dir/(stem+'.md'); md_path.write_text(md,encoding='utf-8')
    csv_path=out_dir/(stem+'.csv')
    with csv_path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(['entry_type','currency','count_entries','amount','costs']); w.writerows([[r['entry_type'],r['currency'],r['count_entries'],r['amount'],r['costs']] for r in report['ledger']]); w.writerow([]); w.writerow(['account','currency','balance']); w.writerows([[a['account'],a['currency'],a['balance']] for a in report['account_balances']])
    xlsx_path=out_dir/(stem+'.xlsx'); _write_xlsx(xlsx_path, report)
    html_path=out_dir/(stem+'.html'); _write_html(html_path, report)
    pdf_path=out_dir/(stem+'.pdf'); _write_pdf(pdf_path, report)
    return {'json':str(out_dir/(stem+'.json')),'md':str(md_path),'markdown':str(md_path),'csv':str(csv_path),'xlsx':str(xlsx_path),'html':str(html_path),'pdf':str(pdf_path)}


def _write_html(path, r):
    rows=''.join(f"<tr><td>{escape(str(x['entry_type']))}</td><td>{escape(str(x['currency']))}</td><td>{x['count_entries']}</td><td>{x['amount']}</td><td>{x['costs']}</td></tr>" for x in r['ledger'])
    accounts=''.join(f"<tr><td>{escape(str(a['account']))}</td><td>{escape(str(a['currency']))}</td><td>{escape(str(a.get('institution') or ''))}</td><td>{escape(str(a.get('account_number') or ''))}</td><td>{escape(str(a.get('iban') or ''))}</td><td>{escape(str(a.get('wallet') or ''))}</td><td>{a['balance']}</td></tr>" for a in r['account_balances'])
    routes=''.join(f"<tr><td>{escape(str(x['source']))}</td><td>{escape(str(x['account']))}</td><td>{escape(str(x['currency']))}</td><td>{escape(str(x.get('iban') or ''))}</td><td>{escape(str(x.get('account_number') or ''))}</td></tr>" for x in r.get('source_account_routes',[]))
    apps=''.join(f"<tr><td>{x['id']}</td><td>{escape(str(x['source']))}</td><td>{escape(str(x['title']))}</td><td>{escape(str(x.get('budget') or ''))}</td><td>{escape(str(x.get('currency') or ''))}</td><td>{escape(str(x.get('state') or ''))}</td><td>{escape(str(x.get('last_seen') or ''))}</td></tr>" for x in r.get('applications',[]))
    kpis=''.join(f'<span class="kpi"><b>{escape(str(k))}</b>: {v}</span>' for k,v in r['application_stats'].items())
    html=f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>MarketRadar Financial Report</title><style>@page{{size:A4;margin:14mm}}body{{font-family:"Segoe UI",Arial,sans-serif;color:#182033;line-height:1.45;background:#fff}}h1,h2,h3{{page-break-after:avoid}}table{{border-collapse:collapse;width:100%;margin:8px 0 18px;direction:ltr}}th,td{{border:1px solid #cfd5df;padding:6px;text-align:left;vertical-align:top;font-size:11px}}th{{background:#eef2f7}}.kpi{{display:inline-block;border:1px solid #d6dbe5;border-radius:8px;padding:8px 12px;margin:4px;direction:ltr}}.muted{{color:#667085;font-size:11px;direction:ltr}}.section{{page-break-inside:avoid}}</style></head><body><h1>MarketRadar — گزارش مالی / Financial Report</h1><p class="muted">{r['period_type']} | {r['start']} → {r['end']} | Generated {r['generated_at']}</p><div>{kpis}</div><div class="section"><h2>Applications / درخواست‌ها</h2><table><tr><th>ID</th><th>Source</th><th>Project</th><th>Amount</th><th>Currency</th><th>Status</th><th>Last Seen</th></tr>{apps or '<tr><td colspan="7">No application records in this period.</td></tr>'}</table></div><div class="section"><h2>Ledger / دفتر مالی</h2><table><tr><th>Type</th><th>Currency</th><th>Entries</th><th>Amount</th><th>Costs</th></tr>{rows}</table></div><div class="section"><h2>Receiving Accounts / حساب‌های دریافت</h2><table><tr><th>Account</th><th>Currency</th><th>Institution</th><th>Account No.</th><th>IBAN / Shaba</th><th>Wallet</th><th>Balance</th></tr>{accounts}</table></div><div class="section"><h2>Source Routing / مسیر واریز بر اساس سایت</h2><table><tr><th>Source</th><th>Account</th><th>Currency</th><th>IBAN</th><th>Account No.</th></tr>{routes or '<tr><td colspan="5">No source routes configured.</td></tr>'}</table></div></body></html>"""
    path.write_text(html,encoding='utf-8')


def _write_xlsx(path, r):
    rows=[['MarketRadar Financial Report'],['Period',r['period_type'],r['start'],r['end']],[],['Entry Type','Currency','Entries','Amount','Costs']]
    rows += [[x['entry_type'],x['currency'],x['count_entries'],x['amount'],x['costs']] for x in r['ledger']]
    rows += [[],['Account','Currency','Balance']]
    rows += [[a['account'],a['currency'],a['balance']] for a in r['account_balances']]
    def cell(v):
        s=escape(str(v)); return f'<c t="inlineStr"><is><t>{s}</t></is></c>'
    sheet_rows=[]
    for i,row in enumerate(rows,1): sheet_rows.append(f'<row r="{i}">'+''.join(cell(v) for v in row)+f'</row>')
    files={
      '[Content_Types].xml':'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
      '_rels/.rels':'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
      'xl/workbook.xml':'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets></workbook>',
      'xl/_rels/workbook.xml.rels':'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
      'xl/worksheets/sheet1.xml':'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(sheet_rows)+'</sheetData></worksheet>'
    }
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for n,v in files.items(): z.writestr(n,v)


def _write_pdf(path, r):
    lines=_report_text(r); page_w,page_h=595,842; text=[]
    y=800
    for line in lines:
        safe=str(line).encode('ascii','replace').decode('ascii')[:105]
        text.append(f'BT /F1 9 Tf 40 {y} Td ({safe.replace(chr(92),"/").replace("(","[").replace(")","]")}) Tj ET'); y-=14
        if y<55: break
    stream='\n'.join(text).encode('latin-1','replace')
    objs=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',f'<< /Length {len(stream)} >>\nstream\n'.encode()+stream+b'\nendstream',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    out=b'%PDF-1.4\n'; offsets=[0]
    for i,o in enumerate(objs,1): offsets.append(len(out)); out+=f'{i} 0 obj\n'.encode()+o+b'\nendobj\n'
    xref=len(out); out+=f'xref\n0 {len(objs)+1}\n0000000000 65535 f \n'.encode(); out+=''.join(f'{x:010d} 00000 n \n' for x in offsets[1:]).encode(); out+=f'trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode(); path.write_bytes(out)

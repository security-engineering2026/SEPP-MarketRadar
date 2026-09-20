from datetime import datetime, timezone, timedelta

def health_score(result):
    if result.get('status') != 'OK': return 0.0
    status=result.get('http_status') or 0
    if 200 <= status < 300:
        if result.get('parse_ok') is False: return 40.0
        if result.get('parsed_count',0) == 0: return 70.0
        return 100.0
    if 400 <= status < 500: return 35.0
    if 500 <= status < 600: return 20.0
    return 50.0

def persist_health(connection, source, result):
    now=datetime.now(timezone.utc); stamp=now.isoformat(); score=health_score(result)
    previous=connection.execute('SELECT failure_count,iran_status,kyc_status,payment_status,execution_mode,proposal_limit FROM sources WHERE name=?',(source['name'],)).fetchone()
    failures=(int(previous['failure_count']) if previous else 0)
    failures=0 if result.get('status')=='OK' and result.get('parse_ok') is not False else failures+1
    if result.get('status')=='OK' and result.get('parse_ok') is True and result.get('parsed_count',0)>0: verification='verified'
    elif result.get('http_status') in (401,403): verification='blocked'
    else: verification='degraded'
    retry=(now+timedelta(minutes=min(60,2**min(failures,6)))).isoformat() if failures else None
    connection.execute('''INSERT INTO sources(name,base_url,adapter,type,status,iran_status,kyc_status,payment_status,execution_mode,proposal_limit,last_checked,health,source_kind,acquisition,verification_state,access_scope,terms_status,failure_count,last_error,next_retry_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(name) DO UPDATE SET base_url=excluded.base_url,adapter=excluded.adapter,type=excluded.type,status=excluded.status,iran_status=excluded.iran_status,kyc_status=excluded.kyc_status,payment_status=excluded.payment_status,execution_mode=excluded.execution_mode,proposal_limit=excluded.proposal_limit,last_checked=excluded.last_checked,health=excluded.health,source_kind=excluded.source_kind,acquisition=excluded.acquisition,verification_state=excluded.verification_state,access_scope=excluded.access_scope,terms_status=excluded.terms_status,failure_count=excluded.failure_count,last_error=excluded.last_error,next_retry_at=excluded.next_retry_at''',
      (source['name'],source['base_url'],source.get('adapter','json'),source.get('type','marketplace'),source.get('status','candidate'),source.get('iran_status') if source.get('iran_status') is not None else (previous['iran_status'] if previous else 'UNKNOWN'),source.get('kyc_status') if source.get('kyc_status') is not None else (previous['kyc_status'] if previous else 'UNKNOWN'),source.get('payment_status') if source.get('payment_status') is not None else (previous['payment_status'] if previous else 'UNKNOWN'),source.get('execution_mode') if source.get('execution_mode') is not None else (previous['execution_mode'] if previous else 'MANUAL'),source.get('proposal_limit') if source.get('proposal_limit') is not None else (previous['proposal_limit'] if previous else None),stamp,score,source.get('source_kind','website'),source.get('acquisition','http'),verification,source.get('access_scope','public'),source.get('terms_status','not_reviewed'),failures,result.get('error') or result.get('parse_error'),retry))
    connection.execute('''INSERT INTO source_contracts(source,source_kind,acquisition,adapter,access_scope,verification_state,terms_status,verification_basis,updated_at,runtime_verification_state) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET runtime_verification_state=excluded.runtime_verification_state,updated_at=excluded.updated_at''',(source['name'],source.get('source_kind','website'),source.get('acquisition','http'),source.get('adapter','json'),source.get('access_scope','public'),verification,source.get('terms_status','not_reviewed'),source.get('verification_basis'),stamp,verification))
    connection.execute('''INSERT INTO federation_runs(source,started_at,status,http_status,observation_count,error,snapshot_sha256) VALUES(?,?,?,?,?,?,?)''',(source['name'],stamp,result.get('status'),result.get('http_status'),result.get('parsed_count',0),result.get('error') or result.get('parse_error'),result.get('sha256')))
    connection.execute('''INSERT INTO source_health_history(source,checked_at,status,http_status,health,verification_state,parse_ok,parsed_count,error,snapshot_sha256,failure_count) VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(source['name'],stamp,result.get('status'),result.get('http_status'),score,verification,None if result.get('parse_ok') is None else int(bool(result.get('parse_ok'))),result.get('parsed_count',0),result.get('error') or result.get('parse_error'),result.get('sha256'),failures))
    return score

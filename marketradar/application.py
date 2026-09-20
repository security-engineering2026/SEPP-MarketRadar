import hashlib,json,math,sqlite3
from datetime import datetime
from .payment import validate_crypto_payment
TRANSITIONS={'DISCOVERED':{'ELIGIBILITY_CHECK','REJECTED','EXPIRED'},'ELIGIBILITY_CHECK':{'RECOMMENDED','REJECTED'},'RECOMMENDED':{'APPROVAL_PENDING','REJECTED'},'APPROVAL_PENDING':{'SUBMITTED','CANCELLED'},'SUBMITTED':{'VIEWED','MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','REJECTED','EXPIRED'},'VIEWED':{'MESSAGE_RECEIVED','NEGOTIATION','ACCEPTED','REJECTED'},'MESSAGE_RECEIVED':{'NEGOTIATION','ACCEPTED','REJECTED'},'NEGOTIATION':{'ACCEPTED','REJECTED','CANCELLED'},'ACCEPTED':{'IN_PROGRESS','CANCELLED'},'IN_PROGRESS':{'DELIVERED','CANCELLED'},'DELIVERED':{'PAID'},'PAID':set()}

def transition(c,oid,new_state,actor='system',commit=True):
    initial=c.execute('select state from opportunities where id=?',(oid,)).fetchone()
    if not initial: raise ValueError('INVALID_TRANSITION')
    if new_state not in TRANSITIONS.get(initial[0],set()):
        raced=c.execute('select 1 from application_events where opportunity_id=? and to_state=? limit 1',(oid,new_state)).fetchone()
        raise ValueError('STATE_RACE' if raced else 'INVALID_TRANSITION')
    expected_state=initial[0]
    owns_tx=not c.in_transaction
    if owns_tx: c.execute('BEGIN IMMEDIATE')
    try:
        row=c.execute('select state from opportunities where id=?',(oid,)).fetchone()
        if not row: raise ValueError('INVALID_TRANSITION')
        if row[0] != expected_state: raise ValueError('STATE_RACE')
        c.execute('insert into application_events(opportunity_id,from_state,to_state,actor) values(?,?,?,?)',(oid,row[0],new_state,actor))
        if commit: c.commit()
    except Exception:
        if owns_tx: c.rollback()
        raise

def record_revenue(c,oid,amount,currency,received_at,payment_ref,network=None,txid=None,verification_state=None,commit=True):
    if not isinstance(amount,(int,float)) or isinstance(amount,bool) or not math.isfinite(amount) or amount<=0: raise ValueError('INVALID_PAYMENT_AMOUNT')
    if not isinstance(currency,str) or not currency.strip() or len(currency.strip())>16: raise ValueError('INVALID_PAYMENT_CURRENCY')
    if not isinstance(payment_ref,str) or not payment_ref.strip() or len(payment_ref)>256: raise ValueError('INVALID_PAYMENT_REFERENCE')
    if not isinstance(received_at,str) or not received_at.strip() or len(received_at)>64: raise ValueError('INVALID_PAYMENT_TIMESTAMP')
    try:
        parsed_time=datetime.fromisoformat(received_at.replace('Z','+00:00'))
        if parsed_time.tzinfo is None or parsed_time.utcoffset() is None: raise ValueError
    except ValueError as exc: raise ValueError('INVALID_PAYMENT_TIMESTAMP') from exc
    currency_norm=currency.strip().upper()
    if currency_norm in {'USDT','USDC','BTC','ETH','TRX','DAI'}:
        ok,reason=validate_crypto_payment(currency_norm,network,txid,amount)
        if not ok: raise ValueError(reason)
        verification_state=verification_state or 'RECORDED_UNVERIFIED'
    else: verification_state=verification_state or 'RECORDED_UNVERIFIED'
    row=c.execute('select state from opportunities where id=?',(oid,)).fetchone()
    if not row or row[0] != 'DELIVERED': raise ValueError('REVENUE_REQUIRES_DELIVERED')
    digest=hashlib.sha256(json.dumps([oid,amount,currency_norm,received_at,payment_ref.strip(),network,verification_state],sort_keys=True).encode()).hexdigest()
    c.execute('insert into revenue(opportunity_id,amount,currency,received_at,payment_ref,digest,payment_network,verification_state) values(?,?,?,?,?,?,?,?)',(oid,amount,currency_norm,received_at,payment_ref.strip(),digest,network,verification_state))
    # Recording a payment claim is not proof of settlement. PAID is reached only
    # after an explicit payment verification record exists.
    if commit: c.commit()
    return digest

def verify_payment(c, oid, payment_ref, status='VERIFIED', network=None, txid=None, actor='human', commit=True):
    row=c.execute('select state from opportunities where id=?',(oid,)).fetchone()
    if not row or row[0] != 'DELIVERED': raise ValueError('PAYMENT_VERIFY_REQUIRES_DELIVERED')
    payment=c.execute('select amount,currency from revenue where opportunity_id=? and payment_ref=?',(oid,payment_ref)).fetchone()
    if not payment: raise ValueError('PAYMENT_RECORD_NOT_FOUND')
    if status not in {'VERIFIED','NOT_VERIFIED','PENDING','FAILED'}: raise ValueError('INVALID_PAYMENT_VERIFICATION_STATUS')
    c.execute('insert into payment_verification(opportunity_id,payment_ref,status,network,txid,checked_at,actor) values(?,?,?,?,?,?,?)',(oid,payment_ref,status,network,txid,datetime.now().astimezone().isoformat(),actor))
    if status == 'VERIFIED':
        transition(c,oid,'PAID','payment_verification',commit=False)
    if commit: c.commit()
    return {'opportunity_id':oid,'payment_ref':payment_ref,'status':status,'amount':payment[0],'currency':payment[1]}

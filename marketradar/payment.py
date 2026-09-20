from __future__ import annotations
import re

CRYPTO = {'USDT':'stablecoin','USDC':'stablecoin','BTC':'bitcoin','ETH':'ethereum','TRX':'tron','DAI':'stablecoin'}
NETWORKS = {'TRC20':'USDT','ERC20':'USDT','ERC-20':'USDT','TRON':'USDT','ETH':'ETH','BEP20':'USDT','BEP-20':'USDT','SOLANA':'USDC','SPL':'USDC','POLYGON':'USDC'}

def detect_payment(text, currency=None):
    t=str(text or '')
    upper=t.upper()
    for token in sorted(CRYPTO, key=len, reverse=True):
        if re.search(r'(?<![A-Z0-9])'+re.escape(token)+r'(?![A-Z0-9])', upper):
            network=None
            for n in NETWORKS:
                if n in upper: network=n
            return {'method':'CRYPTO','asset':token,'network':network,'verified':False,'hint':token}
    c=str(currency or '').upper()
    if c in {'USD','EUR','GBP','INR','IRR','RUB','AED','SAR','QAR','TRY','JPY','KRW','CNY'}:
        return {'method':'FIAT','asset':c,'network':None,'verified':False,'hint':c}
    return {'method':'UNKNOWN','asset':None,'network':None,'verified':False,'hint':'UNKNOWN'}

def validate_crypto_payment(asset, network=None, txid=None, amount=None):
    if asset not in CRYPTO: return False, 'CRYPTO_ASSET_UNSUPPORTED'
    if network and len(str(network))>24: return False, 'CRYPTO_NETWORK_INVALID'
    if txid is not None and (not isinstance(txid,str) or not (12 <= len(txid) <= 160)): return False, 'CRYPTO_TXID_INVALID'
    if amount is not None and (not isinstance(amount,(int,float)) or amount <= 0): return False, 'CRYPTO_AMOUNT_INVALID'
    return True, 'OK'

class PaymentVerifier:
    """Adapter boundary for real settlement verification.

    The core never labels a crypto receipt VERIFIED merely because a reference
    string exists. A chain/explorer adapter must return a positive verification
    result and the caller must persist that state explicitly.
    """
    def verify(self, *, asset, network, txid, expected_amount=None, expected_address=None, token_contract=None):
        raise NotImplementedError('CHAIN_VERIFIER_REQUIRED')

class EvidenceBackedPaymentVerifier(PaymentVerifier):
    def verify(self, *, asset, network, txid, expected_amount=None, expected_address=None, token_contract=None):
        ok, reason=validate_crypto_payment(asset,network,txid,expected_amount)
        if not ok: return {'verified':False,'state':'REJECTED','reason':reason}
        if not expected_address or not token_contract:
            return {'verified':False,'state':'RECORDED_UNVERIFIED','reason':'CHAIN_COUNTERPARTY_BINDING_REQUIRED'}
        return {'verified':False,'state':'VERIFIER_NOT_CONFIGURED','reason':'A chain-specific verifier must prove settlement'}


def detect_kyc(text):
    t=str(text or '').lower()
    positive=('no kyc','without kyc','no identity verification','without identity verification','kyc not required','identity verification not required')
    negative=('kyc required','identity verification required','verify identity','government id required','passport required')
    if any(x in t for x in positive): return 'NOT_REQUIRED'
    if any(x in t for x in negative): return 'REQUIRED'
    return 'UNKNOWN'

from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class ConnectorContract:
    family: str
    base_url: str
    authorization_required: bool
    public_discovery: bool
    notes: str

CONTRACTS={
 'telegram':ConnectorContract('telegram','https://api.telegram.org',True,True,'Official Bot/API access only; no bulk scraping of public channels.'),
 'instagram':ConnectorContract('instagram','https://graph.instagram.com',True,False,'Official Meta/Instagram Graph API permissions only.'),
 'x':ConnectorContract('x','https://api.x.com',True,True,'Official X API application and permissions only.'),
 'linkedin':ConnectorContract('linkedin','https://api.linkedin.com',True,False,'Official LinkedIn OAuth/approved permissions only.'),
 'reddit':ConnectorContract('reddit','https://oauth.reddit.com',True,True,'Official Reddit OAuth/API access only.'),
 'bale':ConnectorContract('bale','https://bale.ai',True,True,'Authorized bot/business integration only.'),
 'eitaa':ConnectorContract('eitaa','https://eitaa.com',True,True,'Authorized bot/business integration only.'),
 'soroush':ConnectorContract('soroush','https://splus.ir',True,True,'Authorized bot/business integration only.'),
}

def get_connector_contract(family: str) -> ConnectorContract:
    try:return CONTRACTS[str(family).lower()]
    except KeyError as exc: raise ValueError('SOCIAL_CONNECTOR_UNSUPPORTED') from exc

def build_request(family: str, credential_env: str, endpoint: str, params: Mapping[str,str]|None=None):
    c=get_connector_contract(family)
    if not credential_env or not isinstance(credential_env,str): raise ValueError('SOCIAL_CREDENTIAL_REFERENCE_REQUIRED')
    import re
    if credential_env.startswith(('sk-','xox','Bearer ','http')) or re.fullmatch(r'\d{5,}:[A-Za-z0-9_-]{6,}',credential_env): raise ValueError('SOCIAL_CREDENTIAL_MUST_BE_ENV_REFERENCE')
    if not endpoint.startswith(('https://','http://')): raise ValueError('SOCIAL_ENDPOINT_INVALID')
    return {'family':c.family,'endpoint':endpoint,'credential_env':credential_env,'params':dict(params or {}),'authorization_required':c.authorization_required,'public_discovery':c.public_discovery}

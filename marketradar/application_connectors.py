from __future__ import annotations
from dataclasses import dataclass
import webbrowser
from datetime import datetime, timezone

@dataclass(frozen=True)
class SubmissionPlan:
    opportunity_id: int
    mode: str
    url: str
    fields: dict
    authorization_required: bool = True

class ApplicationConnector:
    family='manual'
    def plan(self, opportunity, profile, proposal):
        return SubmissionPlan(int(opportunity['id']), 'MANUAL', opportunity['url'], {'proposal':proposal}, True)
    def execute(self, plan):
        if plan.mode != 'MANUAL': raise ValueError('CONNECTOR_MODE_UNSUPPORTED')
        webbrowser.open(plan.url)
        return {'status':'OPENED_FOR_REVIEW','automated':False}

class AuthorizedApiConnector(ApplicationConnector):
    family='authorized_api'
    def __init__(self, sender): self.sender=sender
    def plan(self, opportunity, profile, proposal):
        return SubmissionPlan(int(opportunity['id']), 'AUTHORIZED_API', opportunity['url'], {'proposal':proposal}, True)
    def execute(self, plan):
        if not self.sender: raise ValueError('AUTHORIZED_CONNECTOR_NOT_CONFIGURED')
        return self.sender(plan.fields)


class AuthorizedJsonSubmissionConnector(AuthorizedApiConnector):
    family='authorized_json_api'
    def __init__(self, sender): super().__init__(sender)


class GuidedBrowserConnector(ApplicationConnector):
    """Fast, user-steered browser path. It prepares and opens; it never bypasses CAPTCHA/2FA or silently submits."""
    family='guided_browser'
    def plan(self, opportunity, profile, proposal):
        fields={'proposal':proposal,'profile':profile,'prepared_at':datetime.now(timezone.utc).isoformat()}
        return SubmissionPlan(int(opportunity['id']), 'GUIDED_BROWSER', opportunity['url'], fields, True)
    def execute(self, plan):
        webbrowser.open(plan.url)
        return {'status':'OPENED_FOR_REVIEW','automated':False,'requires_user_submit':True,'path':'GUIDED_BROWSER'}

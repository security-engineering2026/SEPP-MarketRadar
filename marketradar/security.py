from __future__ import annotations
import hashlib, hmac, json, secrets
from dataclasses import dataclass


def canonical_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(obj):
    return hashlib.sha256(canonical_json(obj).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Approval:
    approval_id: str
    action: str
    target: str
    parameters_digest: str
    evidence_digest: str
    policy_version: str
    expires_at: int


class ApprovalBroker:
    """Persistent approval broker. Replay state lives in SQLite, not process memory."""
    def __init__(self, connection=None):
        self.c = connection
        self._used = set()

    def issue(self, action, target, parameters, evidence, policy, now, ttl=300):
        if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0 or ttl > 3600:
            raise ValueError('INVALID_APPROVAL_TTL')
        approval = Approval(secrets.token_hex(24), action, target, digest(parameters), digest(evidence), policy, now + ttl)
        if self.c is not None:
            self.c.execute('''INSERT INTO approvals(approval_id,action,target,parameters_digest,evidence_digest,policy_version,issued_at,expires_at,used_at)
                              VALUES(?,?,?,?,?,?,?,?,NULL)''',
                           (approval.approval_id, approval.action, approval.target, approval.parameters_digest,
                            approval.evidence_digest, approval.policy_version, now, approval.expires_at))
            self.c.commit()
        return approval

    def authorize(self, a, action, target, parameters, evidence, policy, now, commit=True):
        if not isinstance(a, Approval):
            return False, 'MISSING_APPROVAL'
        if now >= a.expires_at:
            return False, 'EXPIRED'
        expected = (a.action, a.target, a.parameters_digest, a.evidence_digest, a.policy_version)
        actual = (action, target, digest(parameters), digest(evidence), policy)
        if expected != actual:
            return False, 'BINDING_MISMATCH'
        if self.c is None:
            if a.approval_id in self._used:
                return False, 'REPLAY'
            self._used.add(a.approval_id)
            return True, 'OK'
        row = self.c.execute('SELECT action,target,parameters_digest,evidence_digest,policy_version,used_at,expires_at FROM approvals WHERE approval_id=?', (a.approval_id,)).fetchone()
        if row is None:
            return False, 'UNKNOWN_APPROVAL'
        stored = (row['action'], row['target'], row['parameters_digest'], row['evidence_digest'], row['policy_version'])
        supplied = (a.action, a.target, a.parameters_digest, a.evidence_digest, a.policy_version)
        if stored != supplied:
            return False, 'APPROVAL_RECORD_MISMATCH'
        if row['used_at'] is not None:
            return False, 'REPLAY'
        if now >= row['expires_at']:
            return False, 'EXPIRED'
        updated = self.c.execute('UPDATE approvals SET used_at=? WHERE approval_id=? AND used_at IS NULL', (now, a.approval_id)).rowcount
        if updated != 1:
            return False, 'REPLAY'
        
        if commit: self.c.commit()
        return True, 'OK'


def verify_hmac(secret, payload, signature):
    if not secret or not isinstance(signature, str):
        return False
    return hmac.compare_digest(hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest(), signature)

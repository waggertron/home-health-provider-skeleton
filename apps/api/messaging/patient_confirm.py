"""HMAC-signed link helpers for patient SMS confirmation (post-v1 #2).

Tokens are produced via Django's TimestampSigner under SECRET_KEY with a
per-purpose salt. Verification raises SignatureExpired (410) for stale
links and BadSignature (400) for tampered or malformed input. Replay
protection lives at the storage layer — once `Visit.patient_confirmed_at`
is set, the confirmation endpoint refuses further writes.
"""

from __future__ import annotations

from django.core.signing import TimestampSigner

# 72 hours mirrors the architecture doc's design.
MAX_AGE_SECONDS = 72 * 3600
_SALT = "patient-confirm"


def _signer() -> TimestampSigner:
    return TimestampSigner(salt=_SALT)


def sign_visit_token(visit_id: int) -> str:
    return _signer().sign(str(visit_id))


def unsign_visit_token(token: str) -> int:
    raw = _signer().unsign(token, max_age=MAX_AGE_SECONDS)
    return int(raw)

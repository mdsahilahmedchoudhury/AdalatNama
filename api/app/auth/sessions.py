"""Signed session tokens (JWT, HS256) carried in an HttpOnly cookie.

The token says *who* and *which chamber*. Role and active status are re-read
from the database on every request, so a role change or removal takes effect
immediately. Expiry is checked against the injected Clock (testable).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt

ALGORITHM = "HS256"
AUDIENCE = "adalatnama-web"
# A token "issued in the future" by more than this is rejected.
MAX_CLOCK_SKEW_SECONDS = 60


@dataclass(frozen=True)
class SessionClaims:
    """The verified contents of a session token."""

    user_id: uuid.UUID
    chamber_id: uuid.UUID
    issued_at: int


def encode_session(
    *, user_id: uuid.UUID, chamber_id: uuid.UUID, now: datetime, ttl: timedelta, secret: str
) -> str:
    """Create a signed session token valid for `ttl` from `now`."""
    issued = int(now.timestamp())
    claims = {
        "sub": str(user_id),
        "cid": str(chamber_id),
        "iat": issued,
        "exp": issued + int(ttl.total_seconds()),
        "aud": AUDIENCE,
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def decode_session(token: str, *, now: datetime, secret: str) -> SessionClaims | None:
    """Verify signature, audience and expiry; return the claims or None."""
    try:
        data = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
            # Time checks happen below against the injected clock, not the wall clock.
            options={
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
                "require": ["sub", "cid", "iat", "exp", "aud"],
            },
        )
        moment = int(now.timestamp())
        if int(data["exp"]) <= moment or int(data["iat"]) > moment + MAX_CLOCK_SKEW_SECONDS:
            return None
        return SessionClaims(
            user_id=uuid.UUID(data["sub"]),
            chamber_id=uuid.UUID(data["cid"]),
            issued_at=int(data["iat"]),
        )
    except (jwt.PyJWTError, ValueError, KeyError):
        return None

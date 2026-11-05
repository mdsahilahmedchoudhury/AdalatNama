"""One-time email sign-in links, stored in Redis.

A link carries a random token. Only its SHA-256 hash is stored, with a TTL, so
a Redis dump never contains a usable link. Consuming a token deletes it
atomically (GETDEL), so each link works exactly once.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass

from redis.asyncio import Redis

TOKEN_KEY = "an:magic:{digest}"  # noqa: S105  (a Redis key pattern, not a secret)
RATE_KEY = "an:magic-rate:{digest}"


@dataclass(frozen=True)
class MagicLinkGrant:
    """Who a consumed magic link signs in."""

    user_id: uuid.UUID
    chamber_id: uuid.UUID


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def issue_token(
    redis: Redis, *, user_id: uuid.UUID, chamber_id: uuid.UUID, ttl_seconds: int
) -> str:
    """Create a single-use token for this user and return it (to be emailed)."""
    token = secrets.token_urlsafe(32)
    payload = json.dumps({"user_id": str(user_id), "chamber_id": str(chamber_id)})
    await redis.set(TOKEN_KEY.format(digest=_digest(token)), payload, ex=ttl_seconds, nx=True)
    return token


async def consume_token(redis: Redis, token: str) -> MagicLinkGrant | None:
    """Return the grant for `token` and delete it, or None if unknown/expired/used."""
    if not token or len(token) > 256:
        return None
    raw = await redis.getdel(TOKEN_KEY.format(digest=_digest(token)))
    if raw is None:
        return None
    data = json.loads(raw)
    return MagicLinkGrant(
        user_id=uuid.UUID(data["user_id"]), chamber_id=uuid.UUID(data["chamber_id"])
    )


async def allow_request(redis: Redis, *, email: str, limit: int, window_seconds: int) -> bool:
    """Count a sign-in-link request for `email`; False once `limit` is exceeded in the window.

    Counted per email whether or not the email exists, so the limit reveals nothing.
    """
    key = RATE_KEY.format(digest=_digest(email.lower()))
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window_seconds)
    return int(count) <= limit

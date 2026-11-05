"""Worker heartbeat: proves the background worker (and its scheduler) is alive."""

from __future__ import annotations

from datetime import datetime

from redis.asyncio import Redis

HEARTBEAT_KEY = "an:worker:heartbeat"
HEARTBEAT_TTL_SECONDS = 600


async def write_heartbeat(redis: Redis, now: datetime) -> None:
    """Record `now` as the worker's latest sign of life."""
    await redis.set(HEARTBEAT_KEY, now.isoformat(), ex=HEARTBEAT_TTL_SECONDS)


async def read_heartbeat(redis: Redis) -> datetime | None:
    """The worker's latest heartbeat, or None if it has not reported recently."""
    raw = await redis.get(HEARTBEAT_KEY)
    if raw is None:
        return None
    value = raw.decode() if isinstance(raw, bytes) else str(raw)
    return datetime.fromisoformat(value)

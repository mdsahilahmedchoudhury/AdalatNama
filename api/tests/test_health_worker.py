"""Health endpoint and the worker heartbeat."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from redis.asyncio import Redis

from app.clock import FixedClock
from app.worker.heartbeat import HEARTBEAT_KEY, read_heartbeat, write_heartbeat
from app.worker.settings import WorkerSettings, heartbeat


async def test_health_reports_dependencies_and_stale_worker(client: AsyncClient) -> None:
    reply = await client.get("/api/health")
    assert reply.status_code == 200
    body = reply.json()
    assert body["database"]["ok"] is True
    assert body["redis"]["ok"] is True
    assert body["schema_revision"] == "0001_foundations"
    assert body["worker"] == {"last_heartbeat_at": None, "stale": True}
    assert body["status"] == "degraded"


async def test_health_is_ok_with_fresh_heartbeat(
    client: AsyncClient, redis: Redis, clock: FixedClock
) -> None:
    await write_heartbeat(redis, clock.now() - timedelta(seconds=30))
    body = (await client.get("/api/health")).json()
    assert body["worker"]["stale"] is False
    assert body["status"] == "ok"

    clock.advance(timedelta(minutes=5))
    assert (await client.get("/api/health")).json()["worker"]["stale"] is True


async def test_heartbeat_job_writes_to_redis(redis: Redis) -> None:
    returned = await heartbeat({"redis": redis})
    stored = await read_heartbeat(redis)
    assert stored is not None
    assert stored.isoformat() == returned
    assert abs((datetime.now(UTC) - stored).total_seconds()) < 5
    assert 0 < await redis.ttl(HEARTBEAT_KEY) <= 600


def test_worker_schedules_the_heartbeat() -> None:
    names = [job.name for job in WorkerSettings.cron_jobs]
    assert "cron:heartbeat" in names
    assert str(WorkerSettings.timezone) == "Asia/Kolkata"

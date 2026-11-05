"""GET /api/health: database, Redis, worker heartbeat and schema revision."""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.auth.deps import ServicesDep
from app.logging import get_logger
from app.schemas.health import ComponentHealth, HealthOut, WorkerHealth
from app.worker.heartbeat import read_heartbeat

router = APIRouter(tags=["health"])
log = get_logger(__name__)


@router.get("/api/health", response_model=HealthOut)
async def health(services: ServicesDep, response: Response) -> HealthOut:
    """Report whether the API can reach its dependencies. Contains no chamber data."""
    revision: str | None = None
    try:
        async with services.db.anonymous_session() as session:
            revision = (
                await session.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar_one_or_none()
        database = ComponentHealth(ok=True)
    except Exception as exc:
        log.error("health_database_failed", error=str(exc))
        database = ComponentHealth(ok=False, detail="database unreachable")

    heartbeat = None
    try:
        await services.redis.ping()
        heartbeat = await read_heartbeat(services.redis)
        redis = ComponentHealth(ok=True)
    except Exception as exc:
        log.error("health_redis_failed", error=str(exc))
        redis = ComponentHealth(ok=False, detail="redis unreachable")

    stale_after = services.settings.worker_heartbeat_stale_after_seconds
    stale = heartbeat is None or (services.clock.now() - heartbeat).total_seconds() > stale_after
    ok = database.ok and redis.ok
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthOut(
        status="ok" if ok and not stale else "degraded",
        database=database,
        redis=redis,
        worker=WorkerHealth(last_heartbeat_at=heartbeat, stale=stale),
        schema_revision=revision,
    )

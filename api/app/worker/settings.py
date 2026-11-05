"""ARQ worker: background jobs and their schedules (ARQ's built-in cron).

Run:  uv run arq app.worker.settings.WorkerSettings

Phase 0 schedules only the heartbeat. Later phases add the morning cause-list
run, the 6 PM digest, display-board polling and nightly order checks here, so
there is one scheduler and one place to read every schedule.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings
from app.logging import configure_logging, get_logger
from app.worker.heartbeat import write_heartbeat

log = get_logger(__name__)


async def heartbeat(ctx: dict[str, Any]) -> str:
    """Write the worker's heartbeat to Redis (read by GET /api/health)."""
    now = datetime.now(UTC)
    await write_heartbeat(ctx["redis"], now)
    return now.isoformat()


async def startup(ctx: dict[str, Any]) -> None:
    """Log the worker start and report in immediately."""
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.environment == "production")
    log.info("worker_started", environment=settings.environment)
    await heartbeat(ctx)


class WorkerSettings:
    """ARQ reads this class to configure the worker process."""

    functions: ClassVar[list[Any]] = [heartbeat]
    cron_jobs: ClassVar[list[Any]] = [
        # Every minute at second 0.
        cron(heartbeat, second=0, unique=True),
    ]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    # Court schedules are Indian Standard Time; cron fields are read in this zone.
    timezone = ZoneInfo(get_settings().default_timezone)
    max_tries = 3

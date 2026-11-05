"""Health check reply."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    """One dependency's state."""

    ok: bool
    detail: str | None = None


class WorkerHealth(BaseModel):
    """When the background worker last reported in."""

    last_heartbeat_at: datetime | None
    stale: bool


class HealthOut(BaseModel):
    """Overall status. 503 when the database or Redis is unreachable."""

    status: Literal["ok", "degraded"]
    database: ComponentHealth
    redis: ComponentHealth
    worker: WorkerHealth
    schema_revision: str | None

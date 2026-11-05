"""Process-wide services shared by request handlers (one instance per app)."""

from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis

from app.auth.mailer import Mailer
from app.clock import Clock
from app.config import Settings
from app.db.session import Database


@dataclass
class Services:
    """Everything a request handler may need besides the request itself."""

    settings: Settings
    db: Database
    redis: Redis
    mailer: Mailer
    clock: Clock

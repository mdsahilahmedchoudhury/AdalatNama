"""Shared fixtures. Tests run against a real Postgres 16 and Redis.

Defaults match the local setup in README.md; CI overrides them with
TEST_DATABASE_URL, TEST_MIGRATION_DATABASE_URL and TEST_REDIS_URL.
The test database is migrated from scratch once per run, and every test
starts with empty tables and an empty Redis database.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.clock import FixedClock
from app.config import Settings
from app.db.session import Database
from app.main import create_app
from app.models import UserRole
from tests.support import RecordingMailer

API_DIR = Path(__file__).resolve().parent.parent
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://adalatnama_app:app_dev_pw@localhost:5432/adalatnama_test",
)
TEST_MIGRATION_DATABASE_URL = os.environ.get(
    "TEST_MIGRATION_DATABASE_URL",
    "postgresql+asyncpg://adalatnama_owner:owner_dev_pw@localhost:5432/adalatnama_test",
)
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Settings pointing at the test database and Redis db 15."""
    return Settings(
        _env_file=None,
        environment="test",
        database_url=TEST_DATABASE_URL,
        migration_database_url=TEST_MIGRATION_DATABASE_URL,
        redis_url=TEST_REDIS_URL,
        web_base_url="http://localhost:3000",
    )


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Rebuild the test schema from migrations (in a subprocess, like production)."""
    env = {**os.environ, "MIGRATION_DATABASE_URL": TEST_MIGRATION_DATABASE_URL}
    for args in (["downgrade", "base"], ["upgrade", "head"]):
        subprocess.run(  # noqa: S603  (fixed argv, no user input)
            [sys.executable, "-m", "alembic", *args],
            cwd=API_DIR,
            env=env,
            check=True,
            capture_output=True,
        )


@pytest.fixture(scope="session")
async def owner_engine() -> AsyncIterator[AsyncEngine]:
    """Privileged connection (bypasses RLS) for arranging and inspecting test data."""
    engine = create_async_engine(TEST_MIGRATION_DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def app_db() -> AsyncIterator[Database]:
    """The restricted app-role database, exactly as the API uses it."""
    db = Database(TEST_DATABASE_URL)
    yield db
    await db.dispose()


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    client = Redis.from_url(TEST_REDIS_URL)
    yield client
    await client.aclose()


@pytest.fixture(autouse=True)
async def clean_state(owner_engine: AsyncEngine, redis: Redis) -> None:
    """Every test starts with empty tables and an empty Redis database."""
    async with owner_engine.begin() as conn:
        await conn.execute(text("TRUNCATE audit_log, users, chambers CASCADE"))
    await redis.flushdb()


@dataclass(frozen=True)
class Member:
    """A user created for a test."""

    id: uuid.UUID
    chamber_id: uuid.UUID
    email: str
    role: UserRole


MakeChamber = Callable[[str], Awaitable[uuid.UUID]]
MakeUser = Callable[..., Awaitable[Member]]


@pytest.fixture
def make_chamber(owner_engine: AsyncEngine) -> MakeChamber:
    async def make(name: str) -> uuid.UUID:
        async with owner_engine.begin() as conn:
            chamber_id: uuid.UUID = (
                await conn.execute(
                    text("INSERT INTO chambers (name, city) VALUES (:n, 'Testpur') RETURNING id"),
                    {"n": name},
                )
            ).scalar_one()
        return chamber_id

    return make


@pytest.fixture
def make_user(owner_engine: AsyncEngine) -> MakeUser:
    async def make(
        chamber_id: uuid.UUID, role: UserRole = UserRole.ASSOCIATE, email: str | None = None
    ) -> Member:
        email = email or f"{role.value}-{uuid.uuid4().hex[:8]}@example.com"
        async with owner_engine.begin() as conn:
            user_id: uuid.UUID = (
                await conn.execute(
                    text(
                        "INSERT INTO users (chamber_id, name, role, email) "
                        "VALUES (:c, :n, :r, :e) RETURNING id"
                    ),
                    {"c": chamber_id, "n": f"Test {role.value}", "r": role.value, "e": email},
                )
            ).scalar_one()
        return Member(id=user_id, chamber_id=chamber_id, email=email, role=role)

    return make


@pytest.fixture
def clock() -> FixedClock:
    # Slightly ahead of real time, because users.sessions_valid_after defaults
    # to the database's now() and sessions must be issued after it.
    return FixedClock(datetime.now(UTC) + timedelta(seconds=2))


@pytest.fixture
def mailer() -> RecordingMailer:
    return RecordingMailer()


@pytest.fixture
async def app(
    settings: Settings, mailer: RecordingMailer, clock: FixedClock
) -> AsyncIterator[FastAPI]:
    application = create_app(settings, mailer=mailer, clock=clock)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """An HTTP client that behaves like the web app (sends the CSRF header, keeps cookies)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Requested-With": "adalatnama"},
    ) as c:
        yield c

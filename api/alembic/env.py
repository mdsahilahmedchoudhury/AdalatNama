"""Alembic environment: runs migrations as the owner role over asyncpg."""

from __future__ import annotations

import asyncio

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.config import get_settings
from app.db.base import Base
from app.models import *  # noqa: F403  (registers every model on Base.metadata)

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    # Tests (and tools) may pass a URL explicitly; otherwise use the owner role.
    override = config.attributes.get("database_url")
    return str(override) if override else get_settings().migration_database_url


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of connecting (`alembic upgrade head --sql`)."""
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Connect as the owner role and apply migrations in one transaction."""
    engine = create_async_engine(_url())
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

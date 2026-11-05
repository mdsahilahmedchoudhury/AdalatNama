"""Engine, sessions and per-chamber tenant isolation.

How isolation works
-------------------
Every chamber-owned table has a Postgres row-level-security (RLS) policy that
only exposes rows whose `chamber_id` equals the session setting
`app.chamber_id`. This module sets that value at the start of **every**
transaction (via the `after_begin` event), using `set_config(..., true)` so it
is transaction-local and can never leak to the next user of a pooled
connection. If no chamber is set, the policies match nothing: isolation fails
closed.

The API and worker connect as a role that is not a superuser, does not own the
tables and has no BYPASSRLS, so the database itself enforces the boundary even
if application code forgets a filter. `verify_app_role_is_restricted` checks
this at startup and refuses to run otherwise.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, SessionTransaction

TENANT_SETTING = "app.chamber_id"
TENANT_INFO_KEY = "chamber_id"


class TenantSession(Session):
    """Sync session class behind AsyncSession; carries the chamber in `session.info`."""


@event.listens_for(TenantSession, "after_begin")
def _apply_tenant_setting(
    session: Session, transaction: SessionTransaction, connection: Connection
) -> None:
    """Set `app.chamber_id` for the transaction that just started (if a chamber is bound)."""
    chamber_id = session.info.get(TENANT_INFO_KEY)
    if chamber_id is not None:
        connection.execute(
            text("SELECT set_config(:name, :value, true)"),
            {"name": TENANT_SETTING, "value": str(chamber_id)},
        )


class AppRoleError(RuntimeError):
    """Raised when the API is connected with a role that would bypass tenant isolation."""


class Database:
    """Owns the engine and hands out sessions, tenant-scoped or anonymous."""

    def __init__(self, url: str, *, echo: bool = False, **engine_kwargs: Any) -> None:
        self.engine: AsyncEngine = create_async_engine(
            url, echo=echo, pool_pre_ping=True, **engine_kwargs
        )
        self._sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, sync_session_class=TenantSession
        )

    @asynccontextmanager
    async def tenant_session(self, chamber_id: uuid.UUID) -> AsyncIterator[AsyncSession]:
        """A session whose every transaction is restricted to one chamber.

        Callers commit explicitly (`await session.commit()`); anything not
        committed is rolled back when the block exits.
        """
        async with self._sessions() as session:
            session.info[TENANT_INFO_KEY] = chamber_id
            yield session

    @asynccontextmanager
    async def anonymous_session(self) -> AsyncIterator[AsyncSession]:
        """A session with no chamber bound: chamber-owned tables appear empty.

        Used only for global reference data and the sign-in lookup function.
        """
        async with self._sessions() as session:
            yield session

    async def verify_app_role_is_restricted(self) -> None:
        """Fail fast if the connected role could bypass row-level security."""
        async with self.engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT current_user AS role, r.rolsuper, r.rolbypassrls, "
                        "EXISTS (SELECT 1 FROM pg_tables t WHERE t.schemaname = 'public' "
                        "        AND t.tableowner = current_user) AS owns_tables "
                        "FROM pg_roles r WHERE r.rolname = current_user"
                    )
                )
            ).one()
        if row.rolsuper or row.rolbypassrls or row.owns_tables:
            raise AppRoleError(
                f"Refusing to start: database role {row.role!r} can bypass row-level "
                "security (superuser, BYPASSRLS or table owner). Point DATABASE_URL at "
                "the restricted app role; migrations use MIGRATION_DATABASE_URL."
            )

    async def dispose(self) -> None:
        """Close all pooled connections."""
        await self.engine.dispose()

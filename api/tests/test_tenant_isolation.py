"""Cross-tenant leakage suite: the database itself keeps chambers apart.

These tests talk to Postgres as the restricted app role (exactly what the
API uses), so they prove isolation even if application code forgot a filter.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.session import AppRoleError, Database
from app.models import AuditLog, User, UserRole
from tests.conftest import (
    TEST_DATABASE_URL,
    TEST_MIGRATION_DATABASE_URL,
    MakeChamber,
    MakeUser,
    Member,
)
from tests.support import RecordingMailer, sign_in


@pytest.fixture
async def two_chambers(
    make_chamber: MakeChamber, make_user: MakeUser
) -> tuple[Member, Member, Member]:
    """Chamber A with two members, chamber B with one."""
    a, b = await make_chamber("Alpha"), await make_chamber("Beta")
    return (
        await make_user(a, UserRole.OWNER),
        await make_user(a, UserRole.ASSOCIATE),
        await make_user(b, UserRole.OWNER),
    )


async def test_no_chamber_bound_means_no_rows(
    app_db: Database, two_chambers: tuple[Member, Member, Member]
) -> None:
    async with app_db.anonymous_session() as s:
        assert await s.scalar(select(func.count()).select_from(User)) == 0
        assert await s.scalar(text("SELECT count(*) FROM chambers")) == 0


async def test_each_chamber_sees_only_its_own_rows(
    app_db: Database, two_chambers: tuple[Member, Member, Member]
) -> None:
    a_owner, a_assoc, b_owner = two_chambers
    async with app_db.tenant_session(a_owner.chamber_id) as s:
        ids = set((await s.scalars(select(User.id))).all())
        assert ids == {a_owner.id, a_assoc.id}
        assert await s.get(User, b_owner.id) is None
        assert await s.scalar(text("SELECT count(*) FROM chambers")) == 1
    async with app_db.tenant_session(b_owner.chamber_id) as s:
        assert set((await s.scalars(select(User.id))).all()) == {b_owner.id}


async def test_cannot_insert_rows_for_another_chamber(
    app_db: Database, two_chambers: tuple[Member, Member, Member]
) -> None:
    a_owner, _, b_owner = two_chambers
    async with app_db.tenant_session(a_owner.chamber_id) as s:
        s.add(
            User(
                chamber_id=b_owner.chamber_id,
                name="Intruder",
                role=UserRole.OWNER,
                email="intruder@example.com",
            )
        )
        with pytest.raises(DBAPIError, match="row-level security"):
            await s.flush()


async def test_cannot_update_or_steal_another_chambers_rows(
    app_db: Database, owner_engine: AsyncEngine, two_chambers: tuple[Member, Member, Member]
) -> None:
    a_owner, a_assoc, b_owner = two_chambers
    async with app_db.tenant_session(a_owner.chamber_id) as s:
        result = await s.execute(update(User).where(User.id == b_owner.id).values(name="Hacked"))
        assert result.rowcount == 0  # type: ignore[attr-defined]
        await s.commit()
    async with owner_engine.connect() as conn:
        name = await conn.scalar(text("SELECT name FROM users WHERE id = :u"), {"u": b_owner.id})
    assert name != "Hacked"

    # Moving one of A's own rows into chamber B is refused by WITH CHECK.
    async with app_db.tenant_session(a_owner.chamber_id) as s:
        with pytest.raises(DBAPIError, match="row-level security"):
            await s.execute(
                update(User).where(User.id == a_assoc.id).values(chamber_id=b_owner.chamber_id)
            )


async def test_app_role_cannot_delete(
    app_db: Database, two_chambers: tuple[Member, Member, Member]
) -> None:
    a_owner, a_assoc, _ = two_chambers
    async with app_db.tenant_session(a_owner.chamber_id) as s:
        with pytest.raises(DBAPIError, match="permission denied"):
            await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": a_assoc.id})


async def test_audit_log_is_append_only(
    app_db: Database, two_chambers: tuple[Member, Member, Member]
) -> None:
    a_owner, _, _ = two_chambers
    async with app_db.tenant_session(a_owner.chamber_id) as s:
        s.add(
            AuditLog(
                chamber_id=a_owner.chamber_id,
                actor_user_id=a_owner.id,
                action="test.event",
                entity_type="user",
            )
        )
        await s.commit()
    for statement in ("UPDATE audit_log SET action = 'x'", "DELETE FROM audit_log"):
        async with app_db.tenant_session(a_owner.chamber_id) as s:
            with pytest.raises(DBAPIError, match="permission denied"):
                await s.execute(text(statement))


async def test_composite_foreign_key_blocks_cross_chamber_links(
    owner_engine: AsyncEngine, two_chambers: tuple[Member, Member, Member]
) -> None:
    """Even a privileged connection cannot link chamber A's row to chamber B's user."""
    a_owner, _, b_owner = two_chambers
    async with owner_engine.begin() as conn:
        with pytest.raises(IntegrityError, match="fk_audit_log_actor_same_chamber"):
            await conn.execute(
                text(
                    "INSERT INTO audit_log (chamber_id, actor_user_id, action, entity_type) "
                    "VALUES (:c, :u, 'x', 'user')"
                ),
                {"c": a_owner.chamber_id, "u": b_owner.id},
            )


async def test_tenant_binding_survives_commit_and_never_leaks_via_pool(
    two_chambers: tuple[Member, Member, Member],
) -> None:
    a_owner, _, _ = two_chambers
    # One pooled connection, reused by every session below.
    db = Database(TEST_DATABASE_URL, pool_size=1, max_overflow=0)
    try:
        async with db.tenant_session(a_owner.chamber_id) as s:
            assert await s.scalar(select(func.count()).select_from(User)) == 2
            await s.commit()
            # A new transaction after commit is re-bound to the same chamber.
            assert await s.scalar(select(func.count()).select_from(User)) == 2
        async with db.anonymous_session() as s:
            assert await s.scalar(select(func.count()).select_from(User)) == 0
    finally:
        await db.dispose()


async def test_every_chamber_owned_table_has_rls(owner_engine: AsyncEngine) -> None:
    """Fails when a migration adds a chamber_id table without enable_tenant_rls()."""
    async with owner_engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT c.relname, c.relrowsecurity, "
                    "       EXISTS (SELECT 1 FROM pg_policy p WHERE p.polrelid = c.oid) "
                    "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r' AND ("
                    "  c.relname = 'chambers' OR EXISTS ("
                    "    SELECT 1 FROM information_schema.columns col "
                    "    WHERE col.table_schema = 'public' AND col.table_name = c.relname "
                    "      AND col.column_name = 'chamber_id'))"
                )
            )
        ).all()
    assert {r[0] for r in rows} >= {"chambers", "users", "audit_log"}
    unprotected = [r[0] for r in rows if not (r[1] and r[2])]
    assert unprotected == []


async def test_api_refuses_to_run_as_a_privileged_role() -> None:
    db = Database(TEST_MIGRATION_DATABASE_URL)
    try:
        with pytest.raises(AppRoleError, match="Refusing to start"):
            await db.verify_app_role_is_restricted()
    finally:
        await db.dispose()


async def test_api_shows_only_own_chamber(
    client: AsyncClient, mailer: RecordingMailer, two_chambers: tuple[Member, Member, Member]
) -> None:
    a_owner, a_assoc, b_owner = two_chambers
    await sign_in(client, mailer, b_owner.email)
    team = (await client.get("/api/team")).json()
    assert [uuid.UUID(m["id"]) for m in team] == [b_owner.id]

    await client.post("/api/auth/logout")
    await sign_in(client, mailer, a_owner.email)
    team_ids = {uuid.UUID(m["id"]) for m in (await client.get("/api/team")).json()}
    assert team_ids == {a_owner.id, a_assoc.id}

"""Roles are enforced on the server for every protected endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models import UserRole
from tests.conftest import MakeChamber, MakeUser
from tests.support import RecordingMailer, sign_in


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (UserRole.OWNER, 200),
        (UserRole.SENIOR, 200),
        (UserRole.ASSOCIATE, 200),
        (UserRole.CLERK, 200),
        (UserRole.CLIENT_READONLY, 403),
    ],
)
async def test_team_list_is_for_staff_only(
    role: UserRole,
    expected: int,
    client: AsyncClient,
    mailer: RecordingMailer,
    make_chamber: MakeChamber,
    make_user: MakeUser,
) -> None:
    member = await make_user(await make_chamber("Alpha"), role)
    await sign_in(client, mailer, member.email)
    assert (await client.get("/api/team")).status_code == expected


async def test_protected_endpoints_need_sign_in(client: AsyncClient) -> None:
    assert (await client.get("/api/me")).status_code == 401
    assert (await client.get("/api/team")).status_code == 401
    assert (await client.post("/api/auth/logout-everywhere")).status_code == 401


async def test_role_change_applies_without_new_sign_in(
    client: AsyncClient,
    mailer: RecordingMailer,
    make_chamber: MakeChamber,
    make_user: MakeUser,
    owner_engine: AsyncEngine,
) -> None:
    member = await make_user(await make_chamber("Alpha"), UserRole.ASSOCIATE)
    await sign_in(client, mailer, member.email)
    assert (await client.get("/api/team")).status_code == 200
    async with owner_engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET role = 'client_readonly' WHERE id = :u"), {"u": member.id}
        )
    assert (await client.get("/api/team")).status_code == 403

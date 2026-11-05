"""Magic-link sign-in, sessions, sign-out and CSRF protection."""

from __future__ import annotations

from datetime import timedelta

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.clock import FixedClock
from app.models import UserRole
from tests.conftest import MakeChamber, MakeUser
from tests.support import RecordingMailer, sign_in


async def test_unknown_email_gets_same_reply_and_no_mail(
    client: AsyncClient, mailer: RecordingMailer
) -> None:
    reply = await client.post("/api/auth/request-link", json={"email": "nobody@example.com"})
    assert reply.status_code == 202
    assert "sign-in link is on its way" in reply.json()["detail"]
    assert mailer.sent == []


async def test_sign_in_with_magic_link(
    client: AsyncClient,
    mailer: RecordingMailer,
    make_chamber: MakeChamber,
    make_user: MakeUser,
    owner_engine: AsyncEngine,
) -> None:
    chamber = await make_chamber("Alpha Chambers")
    owner = await make_user(chamber, UserRole.OWNER, "Owner@Alpha.example".lower())

    # Email is matched case-insensitively.
    reply = await client.post("/api/auth/request-link", json={"email": "OWNER@alpha.example"})
    assert reply.status_code == 202
    assert len(mailer.sent) == 1
    sent = mailer.sent[0]
    assert sent.to == owner.email
    assert sent.link.startswith("http://localhost:3000/auth/verify#token=")

    verified = await client.post("/api/auth/verify", json={"token": sent.token})
    assert verified.status_code == 200, verified.text
    body = verified.json()
    assert body["user"]["id"] == str(owner.id)
    assert body["user"]["role"] == "owner"
    assert body["chamber"]["name"] == "Alpha Chambers"
    set_cookie = verified.headers["set-cookie"]
    assert "an_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie

    me = await client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == owner.email

    async with owner_engine.connect() as conn:
        actions = (
            (
                await conn.execute(
                    text("SELECT action FROM audit_log WHERE actor_user_id = :u"), {"u": owner.id}
                )
            )
            .scalars()
            .all()
        )
    assert actions == ["auth.login"]


async def test_link_works_only_once(
    client: AsyncClient, mailer: RecordingMailer, make_chamber: MakeChamber, make_user: MakeUser
) -> None:
    member = await make_user(await make_chamber("Alpha"))
    first = await sign_in(client, mailer, member.email)
    assert first.status_code == 200
    again = await client.post("/api/auth/verify", json={"token": mailer.sent[-1].token})
    assert again.status_code == 400


async def test_garbage_token_is_rejected(client: AsyncClient) -> None:
    reply = await client.post("/api/auth/verify", json={"token": "x" * 43})
    assert reply.status_code == 400


async def test_requests_are_rate_limited_per_email(
    client: AsyncClient, mailer: RecordingMailer, make_chamber: MakeChamber, make_user: MakeUser
) -> None:
    member = await make_user(await make_chamber("Alpha"))
    for _ in range(5):
        ok = await client.post("/api/auth/request-link", json={"email": member.email})
        assert ok.status_code == 202
    blocked = await client.post("/api/auth/request-link", json={"email": member.email})
    assert blocked.status_code == 429
    assert len(mailer.sent) == 5


async def test_session_expires_after_ttl(
    client: AsyncClient,
    mailer: RecordingMailer,
    clock: FixedClock,
    make_chamber: MakeChamber,
    make_user: MakeUser,
) -> None:
    member = await make_user(await make_chamber("Alpha"))
    await sign_in(client, mailer, member.email)
    clock.advance(timedelta(days=29))
    assert (await client.get("/api/me")).status_code == 200
    clock.advance(timedelta(days=2))
    assert (await client.get("/api/me")).status_code == 401


async def test_tampered_cookie_is_rejected(
    client: AsyncClient, mailer: RecordingMailer, make_chamber: MakeChamber, make_user: MakeUser
) -> None:
    member = await make_user(await make_chamber("Alpha"))
    await sign_in(client, mailer, member.email)
    token = client.cookies["an_session"]
    client.cookies.set("an_session", token[:-2] + ("AA" if token[-2:] != "AA" else "BB"))
    assert (await client.get("/api/me")).status_code == 401


async def test_logout_clears_cookie(
    client: AsyncClient, mailer: RecordingMailer, make_chamber: MakeChamber, make_user: MakeUser
) -> None:
    member = await make_user(await make_chamber("Alpha"))
    await sign_in(client, mailer, member.email)
    assert (await client.post("/api/auth/logout")).status_code == 204
    assert (await client.get("/api/me")).status_code == 401


async def test_logout_everywhere_revokes_old_sessions(
    client: AsyncClient,
    mailer: RecordingMailer,
    clock: FixedClock,
    make_chamber: MakeChamber,
    make_user: MakeUser,
) -> None:
    member = await make_user(await make_chamber("Alpha"))
    await sign_in(client, mailer, member.email)
    stolen = client.cookies["an_session"]

    assert (await client.post("/api/auth/logout-everywhere")).status_code == 204
    client.cookies.set("an_session", stolen)
    assert (await client.get("/api/me")).status_code == 401

    clock.advance(timedelta(seconds=5))
    client.cookies.clear()
    assert (await sign_in(client, mailer, member.email)).status_code == 200
    assert (await client.get("/api/me")).status_code == 200


async def test_removed_user_loses_access_immediately(
    client: AsyncClient,
    mailer: RecordingMailer,
    make_chamber: MakeChamber,
    make_user: MakeUser,
    owner_engine: AsyncEngine,
) -> None:
    member = await make_user(await make_chamber("Alpha"))
    await sign_in(client, mailer, member.email)
    async with owner_engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET deleted_at = now() WHERE id = :u"), {"u": member.id}
        )
    assert (await client.get("/api/me")).status_code == 401
    # And a removed user cannot request a new link.
    await client.post("/api/auth/request-link", json={"email": member.email})
    assert len(mailer.sent) == 1


async def test_state_changing_requests_need_csrf_header(app: FastAPI) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as bare:
        reply = await bare.post("/api/auth/request-link", json={"email": "a@example.com"})
    assert reply.status_code == 403
    assert reply.headers["x-request-id"]

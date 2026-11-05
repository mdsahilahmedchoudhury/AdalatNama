"""Pure unit tests: settings safety, session tokens, clock, chamber settings, seed."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.auth.sessions import decode_session, encode_session
from app.clock import FixedClock
from app.config import Settings
from app.db.session import Database
from app.models import Chamber, User
from app.schemas.chamber import ChamberSettings
from app.seed import SEED, seed, stable_id

SECRET = "x" * 40


def test_production_refuses_development_values() -> None:
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None, environment="production")
    message = str(excinfo.value)
    for fragment in ("SESSION_SECRET", "MAILER", "COOKIE_SECURE", "WEB_BASE_URL"):
        assert fragment in message


def test_production_accepts_safe_values() -> None:
    s = Settings(
        _env_file=None,
        environment="production",
        session_secret=SECRET,
        mailer="smtp",
        cookie_secure=True,
        web_base_url="https://app.example.in",
    )
    assert s.environment == "production"


def test_session_token_round_trip_and_expiry() -> None:
    now = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    uid, cid = uuid.uuid4(), uuid.uuid4()
    token = encode_session(
        user_id=uid, chamber_id=cid, now=now, ttl=timedelta(days=1), secret=SECRET
    )
    claims = decode_session(token, now=now + timedelta(hours=23), secret=SECRET)
    assert claims is not None
    assert (claims.user_id, claims.chamber_id) == (uid, cid)
    assert decode_session(token, now=now + timedelta(days=1), secret=SECRET) is None
    assert decode_session(token, now=now, secret="y" * 40) is None
    assert decode_session("not-a-token", now=now, secret=SECRET) is None


def test_fixed_clock_requires_aware_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FixedClock(datetime(2026, 1, 1))
    clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    clock.advance(timedelta(hours=18))
    assert clock.now().hour == 18


def test_chamber_settings_defaults_and_validation() -> None:
    s = ChamberSettings()
    assert (s.digest_time, s.morning_list_time) == ("18:00", "07:30")
    with pytest.raises(ValidationError):
        ChamberSettings(digest_time="25:00")


async def test_seed_is_idempotent_and_goes_through_rls(app_db: Database) -> None:
    first = await seed(app_db)
    assert len(first) == sum(1 + len(c.users) for c in SEED)
    assert await seed(app_db) == []
    demo = stable_id("chamber:demo")
    async with app_db.tenant_session(demo) as s:
        assert (await s.get(Chamber, demo)) is not None
        assert await s.scalar(select(func.count()).select_from(User)) == 5

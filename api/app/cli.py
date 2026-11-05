"""Operator command line.

  uv run python -m app.cli seed
      Create the fictional demo chambers and users (idempotent).
  uv run python -m app.cli create-chamber --name "..." --city "..." \\
        --owner-name "..." --owner-email "..."
      Create a real chamber and its first owner.
  uv run python -m app.cli login-link EMAIL
      Print a one-time sign-in link for EMAIL (for first sign-in, or when
      email is not configured yet). Treat the printed link like a password.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from redis.asyncio import Redis
from sqlalchemy import text

from app.auth import magic_links
from app.config import get_settings
from app.db.session import Database
from app.models import Chamber, User, UserRole
from app.models.chamber import DEFAULT_CHAMBER_SETTINGS
from app.seed import seed


async def _seed() -> int:
    db = Database(get_settings().database_url)
    try:
        created = await seed(db)
    finally:
        await db.dispose()
    print("\n".join(created) if created else "Seed data already present; nothing to do.")
    return 0


async def _create_chamber(name: str, city: str, owner_name: str, owner_email: str) -> int:
    db = Database(get_settings().database_url)
    chamber_id = uuid.uuid4()
    try:
        async with db.tenant_session(chamber_id) as session:
            session.add(
                Chamber(
                    id=chamber_id, name=name, city=city, settings=dict(DEFAULT_CHAMBER_SETTINGS)
                )
            )
            await session.flush()
            session.add(
                User(
                    chamber_id=chamber_id,
                    name=owner_name,
                    role=UserRole.OWNER,
                    email=owner_email.lower(),
                )
            )
            await session.commit()
    finally:
        await db.dispose()
    print(f"Created chamber {name!r} ({chamber_id}) with owner {owner_email.lower()}")
    return 0


async def _login_link(email: str) -> int:
    settings = get_settings()
    db = Database(settings.database_url)
    redis = Redis.from_url(settings.redis_url)
    try:
        async with db.anonymous_session() as session:
            found = (
                await session.execute(
                    text("SELECT user_id, chamber_id FROM auth_find_user_by_email(:email)"),
                    {"email": email.lower()},
                )
            ).first()
        if found is None:
            print(f"No active user with email {email!r}.", file=sys.stderr)
            return 1
        token = await magic_links.issue_token(
            redis,
            user_id=found.user_id,
            chamber_id=found.chamber_id,
            ttl_seconds=settings.magic_link_ttl_minutes * 60,
        )
    finally:
        await redis.aclose()
        await db.dispose()
    print(f"{settings.web_base_url.rstrip('/')}/auth/verify#token={token}")
    print(f"(valid once, for {settings.magic_link_ttl_minutes} minutes)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run one command."""
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="create fictional demo data")
    cc = sub.add_parser("create-chamber", help="create a chamber and its owner")
    cc.add_argument("--name", required=True)
    cc.add_argument("--city", required=True)
    cc.add_argument("--owner-name", required=True)
    cc.add_argument("--owner-email", required=True)
    ll = sub.add_parser("login-link", help="print a one-time sign-in link")
    ll.add_argument("email")
    args = parser.parse_args(argv)

    if args.command == "seed":
        return asyncio.run(_seed())
    if args.command == "create-chamber":
        return asyncio.run(_create_chamber(args.name, args.city, args.owner_name, args.owner_email))
    return asyncio.run(_login_link(args.email))


if __name__ == "__main__":
    raise SystemExit(main())

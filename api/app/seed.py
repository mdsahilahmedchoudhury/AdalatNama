"""Development seed data: two fictional chambers with one user per role.

Run:  uv run python -m app.cli seed

Everything here is invented for local development and demos. No real chamber,
lawyer or client appears. Seeding is idempotent: fixed ids are reused, so
running it twice changes nothing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.db.session import Database
from app.models import Chamber, User, UserRole
from app.models.chamber import DEFAULT_CHAMBER_SETTINGS

_NAMESPACE = uuid.UUID("6f1d3a52-6c1e-4d39-9a7e-0d0a7d4f2b11")


def stable_id(label: str) -> uuid.UUID:
    """A fixed UUID per seed label, so the seed is repeatable."""
    return uuid.uuid5(_NAMESPACE, label)


@dataclass(frozen=True)
class SeedUser:
    """One seeded person."""

    label: str
    name: str
    role: UserRole
    email: str


@dataclass(frozen=True)
class SeedChamber:
    """One seeded chamber and its people."""

    label: str
    name: str
    city: str
    users: tuple[SeedUser, ...]


SEED: tuple[SeedChamber, ...] = (
    SeedChamber(
        label="chamber:demo",
        name="Demo Law Chambers",
        city="Srinagar",
        users=(
            SeedUser(
                "user:demo:owner", "Rehana Demo", UserRole.OWNER, "owner@demo-chambers.example"
            ),
            SeedUser(
                "user:demo:senior", "Imran Demo", UserRole.SENIOR, "senior@demo-chambers.example"
            ),
            SeedUser(
                "user:demo:associate",
                "Sana Demo",
                UserRole.ASSOCIATE,
                "associate@demo-chambers.example",
            ),
            SeedUser(
                "user:demo:clerk", "Bilal Demo", UserRole.CLERK, "clerk@demo-chambers.example"
            ),
            SeedUser(
                "user:demo:client",
                "Client Demo",
                UserRole.CLIENT_READONLY,
                "client@demo-chambers.example",
            ),
        ),
    ),
    SeedChamber(
        label="chamber:other",
        name="Other Demo Chambers",
        city="Jammu",
        users=(
            SeedUser(
                "user:other:owner", "Owner Other", UserRole.OWNER, "owner@other-chambers.example"
            ),
        ),
    ),
)


async def seed(db: Database) -> list[str]:
    """Create any missing seed chambers and users. Returns a line per row created."""
    created: list[str] = []
    for spec in SEED:
        chamber_id = stable_id(spec.label)
        # The chamber id is bound before the chamber exists: RLS lets a session
        # insert exactly the chamber it is bound to, and nothing else.
        async with db.tenant_session(chamber_id) as session:
            if await session.get(Chamber, chamber_id) is None:
                session.add(
                    Chamber(
                        id=chamber_id,
                        name=spec.name,
                        city=spec.city,
                        settings=dict(DEFAULT_CHAMBER_SETTINGS),
                    )
                )
                await session.flush()
                created.append(f"chamber {spec.name}")
            for u in spec.users:
                user_id = stable_id(u.label)
                if await session.get(User, user_id) is None:
                    session.add(
                        User(
                            id=user_id,
                            chamber_id=chamber_id,
                            name=u.name,
                            role=u.role,
                            email=u.email,
                        )
                    )
                    created.append(f"user {u.email} ({u.role.value})")
            await session.commit()
    return created

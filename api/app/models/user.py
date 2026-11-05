"""User: a member of exactly one chamber (v1; see DECISIONS.md D-007)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey


class UserRole(enum.StrEnum):
    """What a user may do inside their chamber. Enforced server-side on every endpoint."""

    OWNER = "owner"
    SENIOR = "senior"
    ASSOCIATE = "associate"
    CLERK = "clerk"
    CLIENT_READONLY = "client_readonly"


# Roles that work on the chamber's matters (everyone except a read-only client).
STAFF_ROLES = frozenset({UserRole.OWNER, UserRole.SENIOR, UserRole.ASSOCIATE, UserRole.CLERK})


class User(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    """A person who signs in to a chamber."""

    __tablename__ = "users"
    __table_args__ = (
        # Lets other chamber-owned tables use composite foreign keys
        # (chamber_id, user_id), so a row can never point at another chamber's user.
        UniqueConstraint("chamber_id", "id", name="uq_users_chamber_id_id"),
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        Index(
            "uq_users_email_active",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    chamber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chambers.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda roles: [r.value for r in roles],
        ),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    notification_prefs: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # Sessions issued before this moment are rejected ("sign out everywhere").
    sessions_valid_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

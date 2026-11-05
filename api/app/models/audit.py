"""AuditLog: append-only record of who changed what, and when."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKey


class AuditLog(UUIDPrimaryKey, Base):
    """One audited action. The app role may only INSERT and SELECT (never UPDATE/DELETE)."""

    __tablename__ = "audit_log"
    __table_args__ = (
        ForeignKeyConstraint(
            ["chamber_id", "actor_user_id"],
            ["users.chamber_id", "users.id"],
            name="fk_audit_log_actor_same_chamber",
        ),
        Index("ix_audit_log_chamber_created", "chamber_id", "created_at"),
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
    )

    chamber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chambers.id"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    request_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

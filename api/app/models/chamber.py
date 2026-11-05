"""Chamber: the tenant. Every chamber-owned row carries its `chamber_id`."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey

DEFAULT_CHAMBER_SETTINGS: dict[str, Any] = {
    "digest_time": "18:00",
    "morning_list_time": "07:30",
    "quiet_hours": {"start": "22:00", "end": "07:00"},
}


class Chamber(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    """A law chamber (the unit of tenancy, billing and data ownership)."""

    __tablename__ = "chambers"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default=text("'Asia/Kolkata'")
    )
    # Validated by app.schemas.chamber.ChamberSettings before it is written.
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

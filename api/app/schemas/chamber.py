"""Chamber settings: validated shape of `chambers.settings`."""

from __future__ import annotations

from pydantic import BaseModel, Field

HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


class QuietHours(BaseModel):
    """No notifications between `start` and `end` (chamber local time)."""

    start: str = Field(default="22:00", pattern=HHMM)
    end: str = Field(default="07:00", pattern=HHMM)


class ChamberSettings(BaseModel):
    """Per-chamber schedule settings, in the chamber's time zone."""

    digest_time: str = Field(default="18:00", pattern=HHMM)
    morning_list_time: str = Field(default="07:30", pattern=HHMM)
    quiet_hours: QuietHours = Field(default_factory=QuietHours)

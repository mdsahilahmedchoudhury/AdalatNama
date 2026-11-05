"""Time source used everywhere instead of calling `datetime.now()` directly.

Scheduled behaviour (6 PM digest, 07:30 cause list, session expiry, alert
windows) must be testable without waiting, so code receives a `Clock` and
tests pass a `FixedClock` they can move forward.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    """Anything that can tell the current time as a timezone-aware UTC datetime."""

    def now(self) -> datetime: ...


class SystemClock:
    """The real wall clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """A clock that only moves when told to. For tests and replay tools."""

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("FixedClock needs a timezone-aware datetime")
        self._now = start.astimezone(UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        """Move the clock forward by `delta`."""
        self._now += delta

    def set(self, moment: datetime) -> None:
        """Jump to an exact moment."""
        if moment.tzinfo is None:
            raise ValueError("FixedClock needs a timezone-aware datetime")
        self._now = moment.astimezone(UTC)

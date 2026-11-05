"""Writing to the append-only audit log."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


def record_audit(
    db: AsyncSession,
    *,
    chamber_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Add an audit row to the session; it is written when the caller commits.

    `action` is a dotted verb such as "auth.login" or "case.next_date.changed".
    """
    entry = AuditLog(
        chamber_id=chamber_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        request_id=request_id,
    )
    db.add(entry)
    return entry

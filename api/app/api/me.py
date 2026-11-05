"""The signed-in user, their chamber and their team."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.auth.deps import CurrentUser, TenantDB, require_roles
from app.models import Chamber, User
from app.models.user import STAFF_ROLES
from app.schemas.me import ChamberOut, MeOut, UserOut

router = APIRouter(prefix="/api", tags=["me"])

StaffUser = Annotated[User, Depends(require_roles(*STAFF_ROLES))]


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser, db: TenantDB) -> MeOut:
    """Who is signed in, and in which chamber."""
    chamber = await db.get(Chamber, user.chamber_id)
    assert chamber is not None  # noqa: S101  (RLS + FK guarantee it exists)
    return MeOut(user=UserOut.model_validate(user), chamber=ChamberOut.model_validate(chamber))


@router.get("/team", response_model=list[UserOut])
async def team(user: StaffUser, db: TenantDB) -> list[UserOut]:
    """Everyone in the signed-in user's chamber. Not available to read-only clients."""
    rows = await db.scalars(
        select(User)
        # RLS already limits rows to this chamber; the filter is defence in depth.
        .where(User.chamber_id == user.chamber_id, User.deleted_at.is_(None))
        .order_by(User.role, User.name)
    )
    return [UserOut.model_validate(u) for u in rows]

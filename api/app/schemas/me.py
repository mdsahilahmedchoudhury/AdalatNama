"""Responses describing the signed-in user and their chamber."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.models import UserRole


class ChamberOut(BaseModel):
    """Public facts about a chamber."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    city: str | None
    timezone: str


class UserOut(BaseModel):
    """A chamber member as shown to colleagues."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    role: UserRole
    email: str


class MeOut(BaseModel):
    """The signed-in user and their chamber."""

    user: UserOut
    chamber: ChamberOut

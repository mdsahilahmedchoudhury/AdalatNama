"""Sign-in request bodies and replies."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RequestLinkIn(BaseModel):
    """Ask for a sign-in link to be emailed."""

    email: EmailStr


class VerifyIn(BaseModel):
    """Exchange a sign-in link token for a session."""

    token: str = Field(min_length=10, max_length=256)


class MessageOut(BaseModel):
    """A plain human-readable reply."""

    detail: str

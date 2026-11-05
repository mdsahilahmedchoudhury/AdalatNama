"""FastAPI dependencies: services, the signed-in user, tenant DB session, role checks."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.sessions import SessionClaims, decode_session
from app.models import User, UserRole
from app.services import Services

NOT_SIGNED_IN = "You are not signed in, or your session has ended."


def get_services(request: Request) -> Services:
    """The app's shared services (database, Redis, mailer, clock, settings)."""
    services: Services = request.app.state.services
    return services


ServicesDep = Annotated[Services, Depends(get_services)]


def get_claims(request: Request, services: ServicesDep) -> SessionClaims:
    """Verify the session cookie, or fail with 401."""
    token = request.cookies.get(services.settings.session_cookie_name)
    claims = (
        decode_session(
            token,
            now=services.clock.now(),
            secret=services.settings.session_secret.get_secret_value(),
        )
        if token
        else None
    )
    if claims is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, NOT_SIGNED_IN)
    return claims


ClaimsDep = Annotated[SessionClaims, Depends(get_claims)]


async def get_db(claims: ClaimsDep, services: ServicesDep) -> AsyncIterator[AsyncSession]:
    """A database session restricted (by Postgres RLS) to the signed-in user's chamber."""
    async with services.db.tenant_session(claims.chamber_id) as session:
        yield session


TenantDB = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(claims: ClaimsDep, db: TenantDB) -> User:
    """Load the signed-in user fresh from the database (role changes apply at once)."""
    user = await db.get(User, claims.user_id)
    if (
        user is None
        or user.deleted_at is not None
        or claims.issued_at < int(user.sessions_valid_after.timestamp())
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, NOT_SIGNED_IN)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    """Dependency factory: allow only users whose role is in `roles` (else 403)."""
    allowed = frozenset(roles)

    async def check(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role does not allow this action.")
        return user

    return check

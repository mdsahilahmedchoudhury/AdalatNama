"""Sign-in by email magic link; sign-out.

Flow: POST /api/auth/request-link emails a one-time link to the web app's
/auth/verify page. The token travels in the URL *fragment* (#token=...), which
browsers never send to servers, so it cannot end up in access logs. That page
POSTs the token to /api/auth/verify, which sets the session cookie.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from sqlalchemy import text

from app.audit import record_audit
from app.auth import magic_links
from app.auth.deps import CurrentUser, ServicesDep, TenantDB
from app.auth.sessions import encode_session
from app.logging import get_logger
from app.models import Chamber, User
from app.schemas.auth import MessageOut, RequestLinkIn, VerifyIn
from app.schemas.me import ChamberOut, MeOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = get_logger(__name__)

LINK_SENT = "If that email belongs to a chamber member, a sign-in link is on its way."
LINK_INVALID = "This sign-in link is invalid, already used, or expired. Request a new one."


@router.post("/request-link", status_code=status.HTTP_202_ACCEPTED, response_model=MessageOut)
async def request_link(
    body: RequestLinkIn, services: ServicesDep, background: BackgroundTasks
) -> MessageOut:
    """Email a sign-in link. Replies identically whether or not the email exists."""
    s = services.settings
    email = body.email.lower()
    allowed = await magic_links.allow_request(
        services.redis,
        email=email,
        limit=s.magic_link_requests_per_window,
        window_seconds=s.magic_link_window_minutes * 60,
    )
    if not allowed:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many sign-in requests for this email. Wait a few minutes and try again.",
        )

    async with services.db.anonymous_session() as session:
        found = (
            await session.execute(
                text("SELECT user_id, chamber_id FROM auth_find_user_by_email(:email)"),
                {"email": email},
            )
        ).first()
    if found is None:
        log.info("magic_link_unknown_email")
        return MessageOut(detail=LINK_SENT)

    async with services.db.tenant_session(found.chamber_id) as session:
        user = await session.get(User, found.user_id)
    if user is None:  # pragma: no cover  (lookup and RLS disagree: should be impossible)
        log.error("magic_link_user_vanished", user_id=str(found.user_id))
        return MessageOut(detail=LINK_SENT)

    token = await magic_links.issue_token(
        services.redis,
        user_id=user.id,
        chamber_id=user.chamber_id,
        ttl_seconds=s.magic_link_ttl_minutes * 60,
    )
    link = f"{s.web_base_url.rstrip('/')}/auth/verify#token={token}"
    # Sent after the reply so response time does not reveal whether the email exists.
    background.add_task(services.mailer.send_magic_link, to=user.email, name=user.name, link=link)
    return MessageOut(detail=LINK_SENT)


@router.post("/verify", response_model=MeOut)
async def verify(
    body: VerifyIn, request: Request, response: Response, services: ServicesDep
) -> MeOut:
    """Exchange a one-time token for a session cookie."""
    grant = await magic_links.consume_token(services.redis, body.token)
    if grant is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, LINK_INVALID)

    async with services.db.tenant_session(grant.chamber_id) as session:
        user = await session.get(User, grant.user_id)
        chamber = await session.get(Chamber, grant.chamber_id)
        if user is None or user.deleted_at is not None or chamber is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, LINK_INVALID)
        record_audit(
            session,
            chamber_id=chamber.id,
            actor_user_id=user.id,
            action="auth.login",
            entity_type="user",
            entity_id=user.id,
            request_id=getattr(request.state, "request_id", None),
        )
        await session.commit()
        me = MeOut(user=UserOut.model_validate(user), chamber=ChamberOut.model_validate(chamber))

    s = services.settings
    token = encode_session(
        user_id=user.id,
        chamber_id=chamber.id,
        now=services.clock.now(),
        ttl=timedelta(days=s.session_ttl_days),
        secret=s.session_secret.get_secret_value(),
    )
    response.set_cookie(
        s.session_cookie_name,
        token,
        max_age=s.session_ttl_days * 86400,
        httponly=True,
        secure=s.cookie_secure,
        samesite="lax",
        path="/",
    )
    return me


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(services: ServicesDep) -> Response:
    """Forget this browser's session cookie."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(services.settings.session_cookie_name, path="/")
    return response


@router.post("/logout-everywhere", status_code=status.HTTP_204_NO_CONTENT)
async def logout_everywhere(
    user: CurrentUser, db: TenantDB, services: ServicesDep, request: Request
) -> Response:
    """End every session this user has, on every device."""
    user.sessions_valid_after = services.clock.now() + timedelta(seconds=1)
    record_audit(
        db,
        chamber_id=user.chamber_id,
        actor_user_id=user.id,
        action="auth.logout_everywhere",
        entity_type="user",
        entity_id=user.id,
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(services.settings.session_cookie_name, path="/")
    return response

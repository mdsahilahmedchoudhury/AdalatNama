"""FastAPI application factory.

Run in development:  uv run uvicorn --factory app.main:create_app --reload
"""

from __future__ import annotations

import re
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.api import auth, health, me
from app.auth.mailer import Mailer, build_mailer
from app.clock import Clock, SystemClock
from app.config import Settings, get_settings
from app.db.session import Database
from app.logging import configure_logging, get_logger
from app.services import Services

log = get_logger(__name__)

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "adalatnama"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def create_app(
    settings: Settings | None = None,
    *,
    mailer: Mailer | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    """Build the API. Tests pass their own settings, mailer and clock."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_output=settings.environment == "production")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = Database(settings.database_url)
        await db.verify_app_role_is_restricted()
        redis = Redis.from_url(settings.redis_url)
        app.state.services = Services(
            settings=settings,
            db=db,
            redis=redis,
            mailer=mailer or build_mailer(settings),
            clock=clock or SystemClock(),
        )
        log.info("api_started", environment=settings.environment)
        try:
            yield
        finally:
            await redis.aclose()
            await db.dispose()

    app = FastAPI(
        title="AdalatNama API",
        version="0.1.0",
        lifespan=lifespan,
        # Interactive docs only outside production.
        docs_url=None if settings.environment == "production" else "/api/docs",
        openapi_url=None if settings.environment == "production" else "/api/openapi.json",
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Tag each request with an id (logged and echoed) and apply the CSRF rule.

        CSRF rule: state-changing /api requests must carry the header
        `X-Requested-With: adalatnama`. Browsers cannot add a custom header to a
        cross-site request without a CORS preflight, which this API never grants.
        """
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if REQUEST_ID_PATTERN.match(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            if (
                request.method in UNSAFE_METHODS
                and request.url.path.startswith("/api/")
                and request.headers.get(CSRF_HEADER) != CSRF_VALUE
            ):
                response: Response = JSONResponse(
                    {"detail": "Missing X-Requested-With header."}, status_code=403
                )
            else:
                response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers["X-Request-ID"] = request_id
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(me.router)
    return app

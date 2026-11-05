"""Application settings, read from environment variables (and `.env` in development).

Every setting has a safe development default except where a default would be
dangerous in production; `Settings.check_production_safety` refuses to start a
production deployment that still uses a development value.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SESSION_SECRET = "dev-only-insecure-session-secret-change-me"  # noqa: S105


class Settings(BaseSettings):
    """All runtime configuration for the API and the worker."""

    model_config = SettingsConfigDict(
        # `../.env` is the shared file used by Docker Compose; `.env` allows an
        # API-only override when running `uv run` from this directory.
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # --- Database -----------------------------------------------------------
    # The API and worker connect as the least-privilege app role (row-level
    # security applies). Migrations and the seed script use the owner role.
    database_url: str = "postgresql+asyncpg://adalatnama_app:app_dev_pw@localhost:5432/adalatnama"
    migration_database_url: str = (
        "postgresql+asyncpg://adalatnama_owner:owner_dev_pw@localhost:5432/adalatnama"
    )
    db_app_role: str = "adalatnama_app"

    # --- Redis (job queue, magic-link tokens, rate limits, worker heartbeat) --
    redis_url: str = "redis://localhost:6379/0"

    # --- Sessions and magic links ---------------------------------------------
    session_secret: SecretStr = SecretStr(DEV_SESSION_SECRET)
    session_cookie_name: str = "an_session"
    session_ttl_days: int = Field(default=30, ge=1, le=90)
    cookie_secure: bool = False
    magic_link_ttl_minutes: int = Field(default=15, ge=5, le=60)
    magic_link_requests_per_window: int = Field(default=5, ge=1)
    magic_link_window_minutes: int = Field(default=15, ge=1)
    # Public URL of the web app; magic links point here.
    web_base_url: str = "http://localhost:3000"

    # --- Email ------------------------------------------------------------------
    # "console" prints magic links to the API log (development only).
    mailer: Literal["console", "smtp"] = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = "AdalatNama <no-reply@localhost>"
    smtp_starttls: bool = True

    # --- Locale -------------------------------------------------------------------
    default_timezone: str = "Asia/Kolkata"

    # --- Worker ---------------------------------------------------------------------
    # The API reports the worker as stale if no heartbeat arrived within this window.
    worker_heartbeat_stale_after_seconds: int = 180

    @property
    def tz(self) -> ZoneInfo:
        """The default chamber time zone as a ZoneInfo object."""
        return ZoneInfo(self.default_timezone)

    @model_validator(mode="after")
    def check_production_safety(self) -> Settings:
        """Refuse development-only values when ENVIRONMENT=production."""
        if self.environment != "production":
            return self
        problems: list[str] = []
        secret = self.session_secret.get_secret_value()
        if secret == DEV_SESSION_SECRET or len(secret) < 32:
            problems.append("SESSION_SECRET must be a random value of at least 32 characters")
        if self.mailer != "smtp":
            problems.append("MAILER must be 'smtp' (the console mailer prints sign-in links)")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true (cookies must only travel over HTTPS)")
        if not self.web_base_url.startswith("https://"):
            problems.append("WEB_BASE_URL must be an https:// URL")
        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings (cached)."""
    return Settings()

"""Outgoing email for sign-in links.

`ConsoleMailer` prints the link to the API log instead of emailing it. It is
for local development only; production settings refuse it.
`SmtpMailer` sends real mail through any SMTP relay.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.config import Settings
from app.logging import get_logger

log = get_logger(__name__)


class Mailer(Protocol):
    """Sends the sign-in email."""

    async def send_magic_link(self, *, to: str, name: str, link: str) -> None: ...


def _body(name: str, link: str, ttl_minutes: int) -> str:
    return (
        f"Hello {name},\n\n"
        f"Use this link to sign in to AdalatNama. It works once and expires in "
        f"{ttl_minutes} minutes:\n\n{link}\n\n"
        "If you did not ask to sign in, ignore this email. Nobody can sign in without it.\n"
    )


class ConsoleMailer:
    """Development only: logs the sign-in link instead of sending it."""

    def __init__(self, ttl_minutes: int) -> None:
        self.ttl_minutes = ttl_minutes
        log.warning("console_mailer_active", note="sign-in links are printed, not emailed")

    async def send_magic_link(self, *, to: str, name: str, link: str) -> None:
        log.warning("console_mailer_magic_link", to=to, link=link)


class SmtpMailer:
    """Sends sign-in links through an SMTP relay (STARTTLS by default)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _send_blocking(self, message: EmailMessage) -> None:
        s = self.settings
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as smtp:
            if s.smtp_starttls:
                smtp.starttls()
            if s.smtp_username:
                smtp.login(s.smtp_username, s.smtp_password.get_secret_value())
            smtp.send_message(message)

    async def send_magic_link(self, *, to: str, name: str, link: str) -> None:
        message = EmailMessage()
        message["From"] = self.settings.smtp_from
        message["To"] = to
        message["Subject"] = "Your AdalatNama sign-in link"
        message.set_content(_body(name, link, self.settings.magic_link_ttl_minutes))
        await asyncio.to_thread(self._send_blocking, message)
        log.info("magic_link_sent", to_domain=to.rsplit("@", 1)[-1])


def build_mailer(settings: Settings) -> Mailer:
    """Pick the mailer configured by MAILER."""
    if settings.mailer == "smtp":
        return SmtpMailer(settings)
    return ConsoleMailer(settings.magic_link_ttl_minutes)

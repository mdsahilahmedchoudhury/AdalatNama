"""Test helpers: a mailer that records instead of sending, and sign-in shortcuts."""

from __future__ import annotations

from dataclasses import dataclass, field

from httpx import AsyncClient, Response


@dataclass
class SentLink:
    """One sign-in email captured by RecordingMailer."""

    to: str
    name: str
    link: str

    @property
    def token(self) -> str:
        return self.link.split("#token=", 1)[1]


@dataclass
class RecordingMailer:
    """Collects sign-in emails in memory. Test-only."""

    sent: list[SentLink] = field(default_factory=list)

    async def send_magic_link(self, *, to: str, name: str, link: str) -> None:
        self.sent.append(SentLink(to=to, name=name, link=link))


async def sign_in(client: AsyncClient, mailer: RecordingMailer, email: str) -> Response:
    """Request a link for `email` and follow it, as the web app would."""
    before = len(mailer.sent)
    reply = await client.post("/api/auth/request-link", json={"email": email})
    assert reply.status_code == 202, reply.text
    assert len(mailer.sent) == before + 1, "no sign-in email was sent"
    return await client.post("/api/auth/verify", json={"token": mailer.sent[-1].token})

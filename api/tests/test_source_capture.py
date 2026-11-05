"""The Phase 0.5 capture tool obeys robots.txt, retries politely and records provenance."""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

from tools.source_capture import Capturer, Target, load_targets, within_court_hours

PDF = b"%PDF-1.4\n% synthetic test bytes\n"
# A Thursday at 11:00 IST (court hours) and the same day at 20:00 IST.
IN_HOURS = datetime(2026, 11, 5, 5, 30, tzinfo=UTC)
AFTER_HOURS = datetime(2026, 11, 5, 14, 30, tzinfo=UTC)


class _Handler(BaseHTTPRequestHandler):
    hits: dict[str, int] = {}  # noqa: RUF012  (shared test state, reset per server)

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        self.hits[self.path] = self.hits.get(self.path, 0) + 1
        if self.path == "/robots.txt":
            self._send(200, b"User-agent: *\nDisallow: /private/\n", "text/plain")
        elif self.path == "/list.pdf":
            self._send(200, PDF, "application/pdf")
        elif self.path == "/flaky":
            if self.hits[self.path] == 1:
                self._send(429, b"slow down", "text/plain", {"Retry-After": "1"})
            else:
                self._send(200, b"<html>ok</html>", "text/html; charset=utf-8")
        elif self.path == "/board":
            self._send(200, b'{"court": "1", "item": "12"}', "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def _send(
        self, status: int, body: bytes, ctype: str, extra: dict[str, str] | None = None
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def server() -> Iterator[str]:
    _Handler.hits = {}
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _capturer(tmp_path: Path, sleeps: list[float], now: datetime = IN_HOURS) -> Capturer:
    clock = iter(range(1_000_000))
    return Capturer(
        httpx.Client(trust_env=False, follow_redirects=True),
        tmp_path,
        min_delay=10.0,
        jitter=0.0,
        sleep=sleeps.append,
        monotonic=lambda: float(next(clock)),
        now=lambda: now,
    )


def test_saves_bytes_with_provenance(server: str, tmp_path: Path) -> None:
    sleeps: list[float] = []
    result = _capturer(tmp_path, sleeps).capture(
        Target("sample", f"{server}/list.pdf", "test-source", "cause_list", "unit test")
    )
    assert result.outcome == "saved"
    assert result.file is not None
    saved = Path(result.file)
    assert saved.suffix == ".pdf"
    assert saved.read_bytes() == PDF
    meta = json.loads(saved.with_suffix(".meta.json").read_text())
    assert meta["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert meta["url"] == f"{server}/list.pdf"
    assert meta["fetched_at_ist"].endswith("+05:30")
    assert meta["note"] == "unit test"
    assert "AdalatNama-SourceDiscovery" in meta["user_agent"]


def test_robots_txt_is_obeyed(server: str, tmp_path: Path) -> None:
    result = _capturer(tmp_path, []).capture(
        Target("blocked", f"{server}/private/x", "test-source", "other")
    )
    assert result.outcome == "skipped_robots"
    assert "/private/x" not in _Handler.hits


def test_retries_honour_retry_after_and_throttle(server: str, tmp_path: Path) -> None:
    sleeps: list[float] = []
    result = _capturer(tmp_path, sleeps).capture(
        Target("flaky", f"{server}/flaky", "test-source", "other")
    )
    assert result.outcome == "saved"
    assert result.attempts == 2
    assert 1.0 in sleeps  # Retry-After honoured
    # Every request to the host after the first waited for the per-host gap.
    assert any(s >= 8.0 for s in sleeps)


def test_http_errors_are_recorded_not_saved(server: str, tmp_path: Path) -> None:
    result = _capturer(tmp_path, []).capture(
        Target("missing", f"{server}/nope", "test-source", "other")
    )
    assert result.outcome == "http_error"
    assert result.status == 404
    assert result.file is None


def test_unreachable_host_is_reported_as_such(tmp_path: Path) -> None:
    # Port 9 (discard) on localhost: nothing listens, the connection is refused.
    result = _capturer(tmp_path, []).capture(
        Target("down", "http://127.0.0.1:9/list.pdf", "test-source", "cause_list")
    )
    assert result.outcome == "unreachable"
    assert "unreachable" in result.detail
    assert result.file is None


def test_display_boards_only_in_court_hours(server: str, tmp_path: Path) -> None:
    target = Target("board", f"{server}/board", "test-source", "display_board")
    late = _capturer(tmp_path, [], now=AFTER_HOURS).capture(target)
    assert late.outcome == "skipped_hours"
    assert "/board" not in _Handler.hits
    assert _capturer(tmp_path, [], now=IN_HOURS).capture(target).outcome == "saved"


def test_court_hours_rule() -> None:
    assert within_court_hours(IN_HOURS)
    assert not within_court_hours(AFTER_HOURS)
    sunday_noon = datetime(2026, 11, 8, 6, 30, tzinfo=UTC)
    assert not within_court_hours(sunday_noon)


def test_targets_file_is_valid() -> None:
    targets = load_targets(Path(__file__).resolve().parents[1] / "tools" / "capture_targets.toml")
    assert targets, "capture_targets.toml lists no targets"
    assert len({t.id for t in targets}) == len(targets), "duplicate target ids"
    assert all(t.url.startswith("https://") for t in targets)


def test_rejects_unknown_capability_and_scheme() -> None:
    with pytest.raises(ValueError, match="capability"):
        Target("x", "https://example.in", "s", "bulk_download")
    with pytest.raises(ValueError, match="http"):
        Target("x", "ftp://example.in/file", "s", "other")

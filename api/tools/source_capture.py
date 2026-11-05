"""Polite capture of public court pages as recorded fixtures (Phase 0.5, Source Discovery).

This is research tooling, not an adapter. It fetches an explicit list of public
URLs once, saves the exact bytes the server returned, and writes a provenance
record beside each file, so parsers can later be built and tested against real
material (see SOURCES.md).

    uv run python -m tools.source_capture --targets tools/capture_targets.toml
    uv run python -m tools.source_capture --targets tools/capture_targets.toml --only sci-causelist
    uv run python -m tools.source_capture --url https://example.in/list.pdf --id my-sample \\
        --source-key example --capability cause_list

Rules it enforces (non-negotiable, from the build brief §2.1 and §2A):

* GET requests to explicitly listed URLs only. It never follows links, submits
  forms, keeps sessions or touches a CAPTCHA.
* robots.txt is fetched first and obeyed. If robots.txt cannot be read (other
  than "not found"), the host is skipped. Obeying robots.txt is necessary but
  not sufficient: a source's terms of use decide whether automation is allowed.
* One request at a time, at least `--min-delay` seconds between requests to
  the same host (plus random jitter), a descriptive User-Agent, and a bounded
  number of retries with exponential backoff that honours Retry-After.
* Display boards are captured only during court hours (Mon-Sat, 09:30-17:30 IST).
* Output goes to the git-ignored `private/` folder by default, because captured
  court documents name real people and this repository is public.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
import tomllib
import urllib.robotparser
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from datetime import time as dtime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_USER_AGENT = (
    "AdalatNama-SourceDiscovery/0.1 "
    "(+https://github.com/mdsahilahmedchoudhury/AdalatNama; one-off research capture)"
)
DEFAULT_OUT = Path(__file__).resolve().parents[2] / "private" / "source-captures"
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RETRY_AFTER_SECONDS = 120.0
COURT_HOURS = (dtime(9, 30), dtime(17, 30))
CAPABILITIES = frozenset(
    {"cause_list", "case_status", "orders", "display_board", "policy", "index", "other"}
)
EXTENSIONS = {
    "application/pdf": "pdf",
    "text/html": "html",
    "application/json": "json",
    "text/plain": "txt",
    "text/xml": "xml",
    "application/xml": "xml",
}


@dataclass(frozen=True)
class Target:
    """One URL to capture, and why."""

    id: str
    url: str
    source_key: str
    capability: str
    note: str = ""

    def __post_init__(self) -> None:
        if self.capability not in CAPABILITIES:
            raise ValueError(f"{self.id}: unknown capability {self.capability!r}")
        if urlsplit(self.url).scheme not in {"http", "https"}:
            raise ValueError(f"{self.id}: only http(s) URLs can be captured")


@dataclass
class CaptureResult:
    """What happened to one target; written as `<id>.meta.json` and to the run log."""

    id: str
    url: str
    source_key: str
    capability: str
    outcome: str  # saved | http_error | skipped_robots | skipped_hours | unreachable | failed
    detail: str = ""
    status: int | None = None
    final_url: str | None = None
    content_type: str | None = None
    bytes: int | None = None
    sha256: str | None = None
    file: str | None = None
    attempts: int = 0
    fetched_at_utc: str | None = None
    fetched_at_ist: str | None = None
    user_agent: str = ""
    response_headers: dict[str, str] = field(default_factory=dict)


def load_targets(path: Path) -> list[Target]:
    """Read `[[target]]` tables from a TOML file."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return [Target(**entry) for entry in data.get("target", [])]


class HostThrottle:
    """Keeps at least `min_delay` (+ jitter) seconds between requests to one host."""

    def __init__(
        self,
        min_delay: float,
        jitter: float,
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        self.min_delay = min_delay
        self.jitter = jitter
        self._sleep = sleep
        self._monotonic = monotonic
        self._rng = rng or random.Random()  # noqa: S311  (timing jitter, not security)
        self._last: dict[str, float] = {}

    def wait(self, host: str) -> None:
        """Block until this host may be contacted again, then mark it contacted."""
        last = self._last.get(host)
        if last is not None:
            gap = self.min_delay + self._rng.uniform(0, self.jitter)
            remaining = gap - (self._monotonic() - last)
            if remaining > 0:
                self._sleep(remaining)
        self._last[host] = self._monotonic()


class RobotsPolicy:
    """Fetches and caches robots.txt per origin; unreadable robots.txt means 'skip'."""

    def __init__(self, client: httpx.Client, throttle: HostThrottle, user_agent: str) -> None:
        self._client = client
        self._throttle = throttle
        self._user_agent = user_agent
        self._cache: dict[str, urllib.robotparser.RobotFileParser | str] = {}

    def check(self, url: str) -> tuple[str, str]:
        """Return (verdict, reason); verdict is "allowed", "disallowed" or "unreachable"."""
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._cache:
            self._cache[origin] = self._load(origin, parts.netloc)
        parser = self._cache[origin]
        if isinstance(parser, str):
            return "unreachable", parser
        if parser.can_fetch(self._user_agent, url):
            return "allowed", "allowed by robots.txt"
        return "disallowed", "disallowed by robots.txt"

    def _load(self, origin: str, host: str) -> urllib.robotparser.RobotFileParser | str:
        self._throttle.wait(host)
        try:
            response = self._client.get(f"{origin}/robots.txt")
        except httpx.HTTPError as exc:
            return f"host unreachable ({type(exc).__name__}: {exc}); skipped"
        parser = urllib.robotparser.RobotFileParser()
        if response.status_code in {404, 410}:
            parser.parse([])  # no robots.txt: everything allowed by robots
        elif response.status_code == 200:
            parser.parse(response.text.splitlines())
        else:
            return f"robots.txt returned HTTP {response.status_code}; host skipped"
        return parser


def within_court_hours(moment: datetime) -> bool:
    """Mon-Sat, 09:30-17:30 India time."""
    local = moment.astimezone(IST)
    start, end = COURT_HOURS
    return local.weekday() < 6 and start <= local.time() <= end


def _retry_after(response: httpx.Response, default: float) -> float:
    value = response.headers.get("retry-after", "")
    try:
        return min(max(float(value), 0.0), MAX_RETRY_AFTER_SECONDS)
    except ValueError:
        return default


def _extension(content_type: str | None) -> str:
    base = (content_type or "").split(";", 1)[0].strip().lower()
    return EXTENSIONS.get(base, "bin")


class Capturer:
    """Runs targets one by one under the politeness rules and saves what comes back."""

    def __init__(
        self,
        client: httpx.Client,
        out_dir: Path,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        min_delay: float = 10.0,
        jitter: float = 5.0,
        max_attempts: int = 3,
        backoff_base: float = 5.0,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.client = client
        self.out_dir = out_dir
        self.user_agent = user_agent
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self._sleep = sleep
        self._now = now
        self.throttle = HostThrottle(min_delay, jitter, sleep=sleep, monotonic=monotonic)
        self.robots = RobotsPolicy(client, self.throttle, user_agent)

    def run(self, targets: Sequence[Target]) -> list[CaptureResult]:
        """Capture every target and write a run log next to the files."""
        results = [self.capture(t) for t in targets]
        day_dir = self.out_dir / self._now().astimezone(IST).date().isoformat()
        day_dir.mkdir(parents=True, exist_ok=True)
        log = day_dir / "run-log.jsonl"
        with log.open("a", encoding="utf-8") as fh:
            for r in results:
                fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
        return results

    def capture(self, target: Target) -> CaptureResult:
        """Fetch one target politely and save the response body with its provenance."""
        result = CaptureResult(
            id=target.id,
            url=target.url,
            source_key=target.source_key,
            capability=target.capability,
            outcome="failed",
            user_agent=self.user_agent,
        )
        if target.capability == "display_board" and not within_court_hours(self._now()):
            result.outcome = "skipped_hours"
            result.detail = "display boards are captured only during court hours"
            return result

        verdict, reason = self.robots.check(target.url)
        if verdict != "allowed":
            result.outcome = "unreachable" if verdict == "unreachable" else "skipped_robots"
            result.detail = reason
            return result

        host = urlsplit(target.url).netloc
        response: httpx.Response | None = None
        for attempt in range(1, self.max_attempts + 1):
            result.attempts = attempt
            self.throttle.wait(host)
            try:
                response = self.client.get(target.url)
            except httpx.HTTPError as exc:
                result.detail = f"{type(exc).__name__}: {exc}"
                response = None
            else:
                if response.status_code not in RETRY_STATUSES:
                    break
                result.detail = f"HTTP {response.status_code}"
            if attempt < self.max_attempts:
                delay = self.backoff_base * 2 ** (attempt - 1)
                if response is not None:
                    delay = _retry_after(response, delay)
                self._sleep(delay)

        if response is None:
            return result

        moment = self._now()
        body = response.content
        result.status = response.status_code
        result.final_url = str(response.url)
        result.content_type = response.headers.get("content-type")
        result.bytes = len(body)
        result.sha256 = hashlib.sha256(body).hexdigest()
        result.fetched_at_utc = moment.isoformat()
        result.fetched_at_ist = moment.astimezone(IST).isoformat()
        result.response_headers = {
            k: v
            for k, v in response.headers.items()
            if k.lower()
            in {"content-type", "content-length", "last-modified", "etag", "date", "server"}
        }
        if response.status_code >= 400:
            result.outcome = "http_error"
            result.detail = f"HTTP {response.status_code}"
            return result

        day_dir = self.out_dir / moment.astimezone(IST).date().isoformat()
        day_dir.mkdir(parents=True, exist_ok=True)
        path = day_dir / f"{target.id}.{_extension(result.content_type)}"
        path.write_bytes(body)
        result.file = str(path)
        result.outcome = "saved"
        result.detail = reason
        (day_dir / f"{target.id}.meta.json").write_text(
            json.dumps(asdict(result) | {"note": target.note}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return result


def build_client(user_agent: str, timeout: float) -> httpx.Client:
    """An HTTP client with a descriptive User-Agent; redirects followed, nothing else."""
    return httpx.Client(
        headers={"User-Agent": user_agent, "Accept-Language": "en-IN,en;q=0.8"},
        timeout=timeout,
        follow_redirects=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    p = argparse.ArgumentParser(prog="python -m tools.source_capture", description=__doc__)
    p.add_argument("--targets", type=Path, help="TOML file with [[target]] entries")
    p.add_argument("--only", nargs="*", default=[], help="capture only ids starting with these")
    p.add_argument("--url", help="capture a single URL (with --id, --source-key, --capability)")
    p.add_argument("--id")
    p.add_argument("--source-key")
    p.add_argument("--capability", default="other")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--min-delay", type=float, default=10.0)
    p.add_argument("--jitter", type=float, default=5.0)
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = p.parse_args(argv)

    if args.url:
        if not (args.id and args.source_key):
            p.error("--url needs --id and --source-key")
        targets = [Target(args.id, args.url, args.source_key, args.capability)]
    elif args.targets:
        targets = load_targets(args.targets)
        if args.only:
            targets = [t for t in targets if any(t.id.startswith(o) for o in args.only)]
    else:
        p.error("give --targets FILE or --url URL")

    with build_client(args.user_agent, args.timeout) as client:
        capturer = Capturer(
            client,
            args.out,
            user_agent=args.user_agent,
            min_delay=args.min_delay,
            jitter=args.jitter,
        )
        results = capturer.run(targets)

    for r in results:
        size = f"{r.bytes}B" if r.bytes is not None else "-"
        print(f"{r.outcome:15} {r.status or '-':>4} {size:>10}  {r.id}  {r.detail}")
    return 0 if all(r.outcome == "saved" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

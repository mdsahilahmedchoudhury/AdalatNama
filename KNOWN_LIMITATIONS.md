# Known limitations

Updated at the end of every phase. Anything mocked, untested on real material, or missing is listed here.

_Last updated: Phase 0 (foundations)._

## Verification status

- **Docker:** verified in CI, not on a developer machine. The build sandbox could not pull from Docker Hub (HTTP 429), and containers there cannot reach PyPI or npm, so images were not built locally. CI run #1 (job "Stack · Docker Compose + e2e") built both images, booted the full Compose stack (db, redis, migrate, api, worker, web), loaded seed data and passed the Playwright sign-in test.
- **SMTP email has not been tested against a real mail server.** `SmtpMailer` is standard-library `smtplib` code. Until SMTP settings exist, sign-in links come from the console mailer or `python -m app.cli login-link`.

## Development-only stand-ins

- **`ConsoleMailer`** prints sign-in links to the API log instead of emailing them. It logs a warning at startup, and production settings refuse it (`MAILER=smtp` is required).
- **Seed data** (`app.cli seed`) is fictional and exists only for demos and tests.

## Not built yet (by design: later phases)

- No court data of any kind: no cause lists, display boards, orders or eCourts lookups. Source discovery is Phase 0.5, and nothing pretends to fetch court data in the meantime.
- No cases, clients, hearings, calendar or import (Phase 1). The home screen says so plainly.
- No Telegram bot, notification engine or Web Push (Phase 2).
- No team or user management screens. Chambers and users are created with the CLI (`create-chamber`, `seed`). Inviting users from the web app is planned for Phase 1, because assignments need it.
- No offline support. The PWA has a manifest and icons (installable from the browser) but no service worker yet (Phase 6).
- Dark-mode colour tokens exist but have not been reviewed on real devices.

## Security and compliance gaps (scheduled for Phase 6 unless noted)

- Rate limiting covers only sign-in link requests. General API rate limiting is not in place yet.
- No backups, no encryption-at-rest configuration (this depends on the hosting choice), and no restore drill.
- The audit log records sign-in and "sign out everywhere" only. Case, date and assignment changes start being audited in Phase 1 as those features arrive.
- **DPDP Act, 2023:** not assessed. Nothing in this codebase should be read as a compliance claim. It is a separate legal workstream (consent, purpose limitation, erasure, breach logging) to verify at implementation time.
- No per-device session list; only "sign out on all devices".
- Dependency scanning is Dependabot only. `npm audit` reports advisories in development-only packages (none in runtime dependencies at Phase 0). A CI audit gate is Phase 6.

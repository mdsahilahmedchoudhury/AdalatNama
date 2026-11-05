# Decisions

One paragraph per decision, newest last. "Proposed" entries need the product owner's approval before they are built.

### D-001 · Repository layout (Phase 0)
One repository, three top-level parts: `api/` (FastAPI app, ARQ worker, Alembic migrations, operator CLI, all in one Python package and one Docker image), `web/` (Next.js app) and `infra/` (database bootstrap). The API and the worker share models and settings, so splitting them would only add duplication. Court-source adapters will live in `api/app/sources/<adapter>/` behind the §6 interfaces, each with its own fixtures and tests.

### D-002 · Stack as recommended, Python pinned to 3.12 (Phase 0)
The §3 stack is used unchanged: FastAPI, PostgreSQL 16, SQLAlchemy 2 + Alembic, ARQ + Redis, Next.js + Tailwind + shadcn/ui, Docker Compose. Python is pinned to `>=3.12,<3.13` and dependencies are locked with `uv` (`api/uv.lock`); the web app uses `package-lock.json`. Risk noted: ARQ is in maintenance mode upstream. It works and the brief prefers it, but if it stalls, the jobs are plain async functions and can move to another queue without rewriting them.

### D-003 · Tenant isolation is enforced by Postgres row-level security (Phase 0)
Every chamber-owned table gets an RLS policy `chamber_id = app_current_chamber_id()`. The value comes from a transaction-local setting (`set_config('app.chamber_id', …, true)`) that the session layer applies at the start of every transaction (`after_begin`). It is therefore re-applied after a commit and can never leak to the next user of a pooled connection. With no chamber set, policies match nothing (fail closed). The API and worker connect as `adalatnama_app`, which is not a superuser, not the table owner and has no BYPASSRLS; the API refuses to start otherwise (`Database.verify_app_role_is_restricted`). RLS is ENABLEd, not FORCEd, so the migration role (the owner) keeps the access it needs for migrations and the sign-in lookup. Composite foreign keys `(chamber_id, x_id)` make cross-chamber links impossible even for privileged connections. `tests/test_tenant_isolation.py` fails if any table with a `chamber_id` column lacks RLS.

### D-004 · Sign-in lookup through one SECURITY DEFINER function (Phase 0)
Before sign-in nobody has a chamber, so RLS hides every user. Rather than giving the app role a bypass, one function, `auth_find_user_by_email(email)`, owned by the migration role, returns only `(user_id, chamber_id)` for an active user with that exact email. It has a fixed `search_path` and EXECUTE is granted to the app role alone.

### D-005 · Email magic links (Phase 0)
Tokens are 256-bit random values. Only their SHA-256 hash is stored in Redis, with a 15-minute TTL, and they are consumed atomically (`GETDEL`), so each works once. Requests are limited to 5 per email per 15 minutes, counted whether or not the email exists. The reply is identical for unknown emails and the email is sent after the response, so neither content nor timing reveals membership. The link carries the token in the URL fragment (`#token=`), which browsers never send to servers. The verify page waits for a button press, so corporate link scanners that pre-open emails cannot use up the link.

### D-006 · Sessions (Phase 0)
After sign-in the API sets an HttpOnly, SameSite=Lax cookie holding a signed HS256 token (user id, chamber id, issue and expiry times; 30 days by default, because juniors live on their phones). Role and active status are re-read from the database on every request, so a role change or removal applies at once. "Sign out on all devices" moves `users.sessions_valid_after` forward, which invalidates every earlier token. Expiry is checked against an injected `Clock`, never the wall clock, so it is testable.

### D-007 · One email = one chamber account (v1)
Active emails are unique across the whole system (`uq_users_email_active`). A lawyer in two chambers would need two emails. This keeps sign-in unambiguous. It is an open question (OPEN_QUESTIONS Q4) and can be lifted later by adding a chamber picker after sign-in.

### D-008 · CSRF protection by custom header (Phase 0)
Every state-changing `/api` request must carry `X-Requested-With: adalatnama`. A browser cannot add a custom header to a cross-site request without a CORS preflight, and the API grants no CORS. Together with SameSite=Lax cookies this blocks cross-site request forgery without token plumbing. The Telegram webhook (Phase 2) will be exempted and authenticated by Telegram's secret-token header instead.

### D-009 · Browser talks only to Next.js; `/api/*` is proxied (Phase 0)
Next.js rewrites `/api/*` to the FastAPI service, so the session cookie is first-party and no CORS is needed. Next 16 bakes `next.config` in at build time, so `API_INTERNAL_URL` is a Docker build argument (default `http://api:8000`). Server Components read the same variable at request time and forward the visitor's cookies.

### D-010 · Next.js 16 with Cache Components off (Phase 0)
`create-next-app` 16.4 enables `cacheComponents` and `partialPrefetching`. Every AdalatNama screen is per-user and request-time (session, chamber, today's date in IST), so those features would add Suspense and caching rules without a benefit yet. They are off; revisit once there are genuinely shared, cacheable pages.

### D-011 · shadcn/ui components added by hand (Phase 0)
The shadcn CLI could not reach `ui.shadcn.com` from the build sandbox, which blocks that host. The components (`button`, `input`, `label`, `card`) were written in shadcn's own format with its dependencies (`radix-ui`, `class-variance-authority`, `tailwind-merge`, `lucide-react`), and `components.json` is in place, so `npx shadcn add <component>` works normally on a developer machine.

### D-012 · No hard deletes by the app; audit log is append-only (Phase 0)
The app role has no DELETE privilege on any table. Removal is a soft delete (`deleted_at`). `audit_log` grants only SELECT and INSERT, so history cannot be rewritten through the app. The DPDP "deletion on request" and "delete my chamber" flows (Phase 6) will be explicit owner-only admin operations, themselves logged.

### D-013 · A Clock abstraction from day one (Phase 0)
All time-dependent logic receives a `Clock` (`SystemClock` in production, `FixedClock` in tests). The 6 PM digest, 07:30 cause-list run, quiet hours and display-board alert windows can therefore be tested by moving a clock, as §8 requires.

### D-014 · Proposed: split cause-list entries from matches; user-owned rows carry `chamber_id`
§4 puts `matched_case_id` on `CauseListEntry` but lists "cause-list matches" as chamber-owned. A published cause list is public and shared by every chamber that appears in it, while a match is private to one chamber. Proposal: a global `cause_list_entries` table (fetched and parsed once per forum and day) plus a chamber-owned `cause_list_matches` table (confidence, method, confirm/reject state). Likewise `day_watches` and `notification_log` hang off a user but also carry `chamber_id`, so RLS protects them. Needs approval before Phase 3 (OPEN_QUESTIONS Q7).

### D-015 · Fictional seed data on reserved domains (Phase 0)
`python -m app.cli seed` creates "Demo Law Chambers" (one user per role) and "Other Demo Chambers" (for isolation demos). All names are invented and all emails use the reserved `.example` TLD (`.test` is rejected by the email validator). Seeding goes through the app role and RLS, and uses fixed UUIDs, so re-running it changes nothing.

### D-016 · Schedules run in IST; per-chamber times through a dispatcher (Phase 0, applies from Phase 2)
The ARQ worker's cron runs in `Asia/Kolkata`. Chambers can configure their digest and morning-list times, so later phases will not register one cron entry per chamber. A minute-level dispatcher job will read chamber settings and enqueue the work that is due, with idempotency keys.

### D-017 · Development conveniences refuse to run in production (Phase 0)
With `ENVIRONMENT=production`, settings validation rejects the development session secret (or any secret shorter than 32 characters), the console mailer, insecure cookies and a non-HTTPS web URL. Interactive API docs are disabled in production.

### D-018 · `uv` installed from PyPI in the API image (Phase 0)
The API Dockerfile installs `uv==0.11.32` with pip rather than copying it from `ghcr.io/astral-sh/uv`. It needs one less registry and is equally reproducible.

### D-019 · The repository is public, so client data has hard guardrails (Phase 0)
`AdalatNama` was created as a public repository. No client or case data may ever be committed: the eCourts export, order PDFs from the chamber's own cases and similar files go in the git-ignored `private/` folder or outside the repo (see SECURITY.md). Court-source fixtures (public cause lists, display-board pages) are public records, but they still name real litigants. Before any are committed in Phase 0.5, the repository should be made private, or the fixtures must be trimmed or redacted (OPEN_QUESTIONS Q1).

### D-020 · Proposed: order of preference for court data sources (Phase 0.5)
For every capability: (1) an official push the chamber already receives (for example eCourts' automated emails or SMS to a registered advocate); (2) a document the court publishes for public download (PDF cause lists, display boards); (3) a human-in-the-loop step where the user solves a CAPTCHA; (4) an authorised or paid provider, only on the product owner's decision. Never OCR or other CAPTCHA bypass, session reuse, calling a portal's background endpoints to skip its form, or IP rotation or VPNs to evade a geofence. Details and evidence are in SOURCES.md.

### D-021 · Source discovery uses one polite capture tool, saving to private/ (Phase 0.5)
`api/tools/source_capture.py` is research tooling, not an adapter. It fetches only listed URLs and obeys robots.txt, skipping a host whose robots.txt cannot be read. It keeps at least 10 s plus jitter between requests to a host, makes bounded retries that honour Retry-After, sends a descriptive User-Agent, and captures display boards only in court hours. Raw bytes and a provenance record (URL, UTC and IST time, SHA-256, headers) go to the git-ignored `private/source-captures/`, because captured court documents name real people and the repository is public (D-019).

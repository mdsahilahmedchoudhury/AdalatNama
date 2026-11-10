# AdalatNama

**AdalatNama** (*adalat*: court, *-nama*: record) is a case management system for small and mid-size litigation chambers in India. It replaces the handwritten case diary and the hand-compiled daily cause list. Cases come in from the eCourts app; the chamber's listings are matched across High Court, district court, tribunal and consumer-commission cause lists each morning. Every lawyer gets tomorrow's list at 6 PM, a phone buzz as their case nears on the display board, and new orders saved to the case overnight.

It tracks and reminds. It does not give legal advice: every derived date shows its source, and court-sourced dates always win.

> **Status: Phase 0 (foundations) complete.** Sign-in, tenancy, the app shell, the job worker, CI and Docker are in place. No court data is integrated yet; see [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

| Phase | Scope | State |
|---|---|---|
| 0 | Foundations: repo, Docker, CI, auth, tenancy, seed | ✅ done |
| 0.5 | Source discovery: how each court source can legitimately be read ([SOURCES.md](SOURCES.md)) | in progress: pilot sources verified; all-HC survey pending |
| 1 | Core CRM: eCourts import, case list, filters, calendar, .ics | planned ([plan](docs/PHASE1_PLAN.md)) |
| 2 | Telegram bot + notification engine | planned |
| 3 | Cause lists: adapters, matching, consolidated list, 6 PM digest | planned |
| 4 | Live display-board tracking | planned |
| 5 | Nightly order tracking | planned |
| 6 | Hardening: backups, load, accessibility, PWA, onboarding | planned |

## Repository layout

```
api/                  FastAPI API + ARQ worker + operator CLI (Python 3.12, uv)
  app/
    api/              HTTP routes (health, auth, me/team)
    auth/             magic links, session tokens, mailer, role checks
    db/               engine, tenant-scoped sessions (RLS), migration helpers
    models/           SQLAlchemy models
    schemas/          Pydantic request/response models
    worker/           ARQ worker settings and jobs
    cli.py            seed / create-chamber / login-link
  tools/              source_capture.py: polite one-off capture of public court pages
  alembic/            migrations (0001_foundations)
  tests/              pytest suite, incl. cross-tenant leakage tests
web/                  Next.js 16 app (TypeScript, Tailwind 4, shadcn/ui), mobile-first PWA
  src/app/            login, magic-link verify, signed-in shell
  e2e/                Playwright smoke tests (phone viewport)
infra/postgres/init/  creates the restricted database role the app uses
docs/                 ER diagram, Phase 1 plan, open questions
private/              git-ignored: real client files live here, never in git
```

## Run it with Docker

```bash
cp .env.example .env
```

Edit `.env` and replace every `CHANGE ME` value, then:

```bash
docker compose up --build
```

```bash
docker compose exec api python -m app.cli seed
```

```bash
docker compose exec api python -m app.cli login-link owner@demo-chambers.example
```

Open the printed link in a browser and press **Continue**. The web app is at http://localhost:3000; the API docs are at http://localhost:8000/api/docs. In development, sign-in emails are printed to the `api` log (`docker compose logs api`) instead of being sent.

## Run it without Docker (development)

Needs Postgres 16, Redis 7, Python 3.12 with [uv](https://docs.astral.sh/uv/), and Node 22.

1. Create the owner role and databases (the defaults in `api/app/config.py` match these local-only passwords):

   ```bash
   sudo -u postgres psql -c "CREATE ROLE adalatnama_owner LOGIN SUPERUSER PASSWORD 'owner_dev_pw'" -c "CREATE DATABASE adalatnama OWNER adalatnama_owner" -c "CREATE DATABASE adalatnama_test OWNER adalatnama_owner"
   ```

2. Create the restricted app role in each database:

   ```bash
   for db in adalatnama adalatnama_test; do PGHOST=localhost PGPASSWORD=owner_dev_pw POSTGRES_USER=adalatnama_owner POSTGRES_DB=$db DB_APP_PASSWORD=app_dev_pw ./infra/postgres/init/01-app-role.sh; done
   ```

3. API, migrations, seed, then the API and the worker (in two terminals):

   ```bash
   cd api && uv sync && uv run alembic upgrade head && uv run python -m app.cli seed
   ```

   ```bash
   cd api && uv run uvicorn --factory app.main:create_app --reload
   ```

   ```bash
   cd api && uv run arq app.worker.settings.WorkerSettings
   ```

4. Web app:

   ```bash
   cd web && npm install && npm run dev
   ```

5. Sign in: open http://localhost:3000, or mint a link directly:

   ```bash
   cd api && uv run python -m app.cli login-link owner@demo-chambers.example
   ```

## Tests and checks

```bash
cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy app tests && uv run pytest
```

```bash
cd web && npm run lint && npm run format:check && npm run typecheck && npm run build
```

```bash
cd web && npx playwright test
```

The Playwright test expects the stack running on http://localhost:3000 with seed data. CI runs all three, plus a full Docker Compose boot ([.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Documents

- [SOURCES.md](SOURCES.md): court data sources, access classes and the adapter plan (draft)
- [DECISIONS.md](DECISIONS.md): why things are the way they are
- [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md): what is mocked, unverified or missing
- [SECURITY.md](SECURITY.md): confidentiality rules (read before committing anything)
- [docs/ER.md](docs/ER.md): the full data model (Mermaid)
- [docs/PHASE1_PLAN.md](docs/PHASE1_PLAN.md): the next build phase
- [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md): decisions waiting on the product owner

## Acknowledgement

The product brief takes its workflow from CourtSync, a chamber tool built by Hammad Altaf Hafiz. AdalatNama is an independent implementation with its own code, name and visual identity; it uses none of CourtSync's branding or assets.

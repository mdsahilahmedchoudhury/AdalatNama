# Security and confidentiality

AdalatNama handles privileged client information. These rules apply to everyone who works on this repository, human or AI.

## Never commit client or case data

This repository is (at the time of writing) **public**. Never commit:

- the chamber's eCourts app export, or any file derived from it;
- order or judgment PDFs downloaded for the chamber's own matters;
- database dumps, logs or screenshots containing real names, case numbers or contact details;
- `.env` files, tokens (Telegram, SMTP, session secrets) or private keys.

Put working copies of such files in `private/`, which git ignores, or keep them outside the repository. Tests use **synthetic** data that copies the real file's *structure* but contains invented values.

Public court material (cause lists, display-board pages) recorded as test fixtures still names real litigants. Commit it only once the repository is private, or after trimming it to the minimum needed and redacting names that the test does not need.

## How data is isolated

- Every chamber's rows are protected by Postgres row-level security, enforced by the database for the restricted role the API uses (see DECISIONS.md D-003).
- The API refuses to start if it is connected with a role that could bypass those policies.
- `api/tests/test_tenant_isolation.py` is the cross-tenant leakage suite. Every new chamber-owned table must pass it.

## Reporting a problem

If you find a security issue, do not open a public issue. Contact the repository owner directly.

## Secrets

- Secrets are read from the environment (`.env` locally, the host's secret store in production). See `.env.example`.
- Production startup refuses development secrets, the console mailer and insecure cookies.
- Rotate `SESSION_SECRET` to sign everyone out. Rotation steps for the Telegram bot token will be documented in Phase 2.

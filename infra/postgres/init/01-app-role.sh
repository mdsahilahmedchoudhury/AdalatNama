#!/usr/bin/env bash
# Creates the least-privilege role the API and worker connect as.
#
# Runs once, when the Postgres data directory is first initialised (the
# official postgres image executes every script in /docker-entrypoint-initdb.d).
# CI and local setups run it by hand with the same environment variables.
#
#   POSTGRES_USER      the owner/migration role (superuser in the docker image)
#   POSTGRES_DB        the application database
#   DB_APP_ROLE        login role used by the API and worker (default adalatnama_app)
#   DB_APP_PASSWORD    its password (required)
#
# The app role is deliberately NOT a superuser, NOT the table owner and has
# NO BYPASSRLS, so Postgres row-level security applies to every query it runs.
# The API refuses to start if it finds itself connected with any of those powers.
set -euo pipefail

: "${DB_APP_PASSWORD:?DB_APP_PASSWORD must be set}"
APP_ROLE="${DB_APP_ROLE:-adalatnama_app}"

psql -v ON_ERROR_STOP=1 \
     --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" \
     -v app_role="${APP_ROLE}" -v app_password="${DB_APP_PASSWORD}" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS',
              :'app_role', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_role')
\gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_role')
\gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'app_role')
\gexec
SQL

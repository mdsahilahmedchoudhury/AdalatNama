"""Helpers used by Alembic migrations for row-level security and grants.

Every new chamber-owned table must call `enable_tenant_rls()` and
`grant_to_app_role()` in its migration. The cross-tenant test suite
(`tests/test_tenant_isolation.py`) checks that every table with a
`chamber_id` column has RLS enabled, so a forgotten call fails CI.
"""

from __future__ import annotations

from alembic import op
from app.config import get_settings


def app_role() -> str:
    """The restricted role the API and worker connect as."""
    return get_settings().db_app_role


def quote_ident(name: str) -> str:
    """Quote an SQL identifier (table or role name)."""
    return '"' + name.replace('"', '""') + '"'


def enable_tenant_rls(table: str, *, column: str = "chamber_id") -> None:
    """Restrict every row of `table` to the chamber in `app.chamber_id`.

    One permissive policy covers SELECT, INSERT, UPDATE and DELETE: rows are
    visible only when `column = app_current_chamber_id()`, and new or updated
    rows must satisfy the same condition. With no chamber set, nothing matches.
    """
    t = quote_ident(table)
    op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON {t} "
        f"USING ({quote_ident(column)} = app_current_chamber_id()) "
        f"WITH CHECK ({quote_ident(column)} = app_current_chamber_id())"
    )


def grant_to_app_role(table: str, privileges: str) -> None:
    """Grant table privileges (e.g. "SELECT, INSERT") to the app role."""
    op.execute(f"GRANT {privileges} ON {quote_ident(table)} TO {quote_ident(app_role())}")

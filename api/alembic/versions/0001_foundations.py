"""Foundations: tenancy helpers, chambers, users, audit log, sign-in lookup.

Revision ID: 0001_foundations
Revises:
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.db.migration_helpers import (
    app_role,
    enable_tenant_rls,
    grant_to_app_role,
    quote_ident,
)

revision: str = "0001_foundations"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER_ROLES = ("owner", "senior", "associate", "clerk", "client_readonly")


def upgrade() -> None:
    # pg_trgm powers fuzzy party-name matching from Phase 1 onwards.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # The chamber bound to the current transaction, or NULL (which matches nothing).
    op.execute(
        """
        CREATE FUNCTION app_current_chamber_id() RETURNS uuid
        LANGUAGE sql STABLE PARALLEL SAFE
        AS $$ SELECT nullif(current_setting('app.chamber_id', true), '')::uuid $$
        """
    )

    op.create_table(
        "chambers",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default=sa.text("'Asia/Kolkata'"),
            nullable=False,
        ),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chambers")),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("chamber_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.Enum(*USER_ROLES, name="user_role"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "notification_prefs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "sessions_valid_after",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_users_email_lowercase")),
        sa.ForeignKeyConstraint(
            ["chamber_id"], ["chambers.id"], name=op.f("fk_users_chamber_id_chambers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("chamber_id", "id", name="uq_users_chamber_id_id"),
        sa.UniqueConstraint("telegram_chat_id", name=op.f("uq_users_telegram_chat_id")),
    )
    op.create_index(op.f("ix_users_chamber_id"), "users", ["chamber_id"])
    op.create_index(
        "uq_users_email_active",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("chamber_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["chamber_id", "actor_user_id"],
            ["users.chamber_id", "users.id"],
            name="fk_audit_log_actor_same_chamber",
        ),
        sa.ForeignKeyConstraint(
            ["chamber_id"], ["chambers.id"], name=op.f("fk_audit_log_chamber_id_chambers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index("ix_audit_log_chamber_created", "audit_log", ["chamber_id", "created_at"])
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])

    # --- Row-level security -------------------------------------------------
    # chambers is keyed by its own id; the others by chamber_id.
    enable_tenant_rls("chambers", column="id")
    enable_tenant_rls("users")
    enable_tenant_rls("audit_log")

    # --- Grants to the restricted app role ------------------------------------
    # No DELETE anywhere: removal is soft delete; erasure is an owner-only admin flow.
    grant_to_app_role("chambers", "SELECT, INSERT, UPDATE")
    grant_to_app_role("users", "SELECT, INSERT, UPDATE")
    grant_to_app_role("audit_log", "SELECT, INSERT")  # append-only
    grant_to_app_role("alembic_version", "SELECT")  # lets /api/health report the schema

    # --- Sign-in lookup ----------------------------------------------------------
    # Before sign-in nobody has a chamber, so RLS hides every user. This one
    # function, owned by the migration role, answers "which active user has
    # this email?" and nothing else. It returns ids only.
    op.execute(
        """
        CREATE FUNCTION auth_find_user_by_email(p_email text)
        RETURNS TABLE (user_id uuid, chamber_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = pg_catalog, public, pg_temp
        AS $$
            SELECT u.id, u.chamber_id
            FROM public.users u
            JOIN public.chambers c ON c.id = u.chamber_id
            WHERE u.email = lower(p_email)
              AND u.deleted_at IS NULL
              AND c.deleted_at IS NULL
        $$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION auth_find_user_by_email(text) FROM PUBLIC")
    op.execute(
        f"GRANT EXECUTE ON FUNCTION auth_find_user_by_email(text) TO {quote_ident(app_role())}"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS auth_find_user_by_email(text)")
    op.drop_table("audit_log")
    op.drop_table("users")
    op.drop_table("chambers")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP FUNCTION IF EXISTS app_current_chamber_id()")

"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False, unique=True),
        sa.Column("profile_picture", sa.Text(), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("member_id", sa.String(64), nullable=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("ofc_status", sa.String(32), nullable=False, server_default="Active"),
        sa.Column("bio", sa.String(300), nullable=True),
        sa.Column("password", sa.String(255), nullable=True),
        sa.Column("provider", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("public_year", sa.Integer(), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_account_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("account_locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_users_user_id", "users", ["user_id"])
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "user_oshis",
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("member_id", sa.String(64), primary_key=True),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("hash_refresh_token", sa.String(64), nullable=False, unique=True),
        sa.Column("device", sa.String(255), nullable=False, server_default=""),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("browser", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_hash", "refresh_tokens", ["hash_refresh_token"])

    op.create_table(
        "login_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("device", sa.String(255), nullable=False, server_default=""),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("browser", sa.String(255), nullable=False, server_default=""),
        sa.Column("login_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent_raw", sa.Text(), nullable=True),
    )
    op.create_index("ix_login_history_user_id", "login_history", ["user_id"])

    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("hash_token", sa.String(64), nullable=False),
        sa.Column("token_type", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_verification_tokens_user_id", "verification_tokens", ["user_id"])
    op.create_index("ix_verification_hash_type", "verification_tokens", ["hash_token", "token_type"])

    op.create_table(
        "members",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("nickname", sa.String(50), nullable=True),
        sa.Column("generation", sa.String(50), nullable=True),
        sa.Column("jiko", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("href", sa.String(255), nullable=True),
        sa.Column("img", sa.Text(), nullable=True),
        sa.Column("birthdate", sa.String(50), nullable=True),
        sa.Column("blood_type", sa.String(10), nullable=True),
        sa.Column("horoscope", sa.String(50), nullable=True),
        sa.Column("height", sa.String(20), nullable=True),
        sa.Column("socials", postgresql.JSONB(), nullable=True),
        sa.Column("member_type", sa.String(50), nullable=True, server_default="JKT48"),
        sa.Column("member_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_members_name", "members", ["name"])
    op.create_index("ix_members_active", "members", ["active"])

    op.create_table(
        "setlists",
        sa.Column("setlist_id", sa.String(64), primary_key=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("title_japanese", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("type", sa.String(32), nullable=False, server_default="setlist"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("songs", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_setlists_title", "setlists", ["title"])

    op.create_table(
        "events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url", sa.Text(), nullable=False, server_default=""),
        sa.Column("label", sa.String(100), nullable=False, server_default=""),
        sa.Column("type", sa.String(50), nullable=True),
        sa.Column("setlist_id", sa.String(64), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_title", "events", ["title"])
    op.create_index("ix_events_date", "events", ["date"])
    op.create_index("ix_events_setlist_id", "events", ["setlist_id"])

    op.create_table(
        "event_members",
        sa.Column("event_id", sa.String(64), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("member_id", sa.String(64), primary_key=True),
        sa.Column("role", sa.String(32), primary_key=True, server_default="member"),
    )
    op.create_index("ix_event_members_member_id", "event_members", ["member_id"])

    op.create_table(
        "news",
        sa.Column("news_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("category", sa.String(100), nullable=False, server_default=""),
        sa.Column("link", sa.String(500), nullable=False, unique=True),
        sa.Column("background_image", sa.Text(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("valid_date_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_body", sa.Text(), nullable=False, server_default=""),
        sa.Column("short_description", sa.Text(), nullable=True),
    )
    op.create_index("ix_news_link", "news", ["link"])
    op.create_index("ix_news_valid_date_from", "news", ["valid_date_from"])

    op.create_table(
        "concerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("theme", sa.String(255), nullable=True),
        sa.Column("type", sa.String(64), nullable=False, server_default="Anniversary"),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(255), nullable=False, server_default=""),
        sa.Column("details", sa.Text(), nullable=False, server_default=""),
        sa.Column("benefits", postgresql.JSONB(), nullable=True),
        sa.Column("ticket_price", postgresql.JSONB(), nullable=True),
        sa.Column("image", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_concerts_date", "concerts", ["date"])

    op.create_table(
        "sorter_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("filters", postgresql.JSONB(), nullable=True),
        sa.Column("results", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sorter_results_user_id", "sorter_results", ["user_id"])


def downgrade() -> None:
    op.drop_table("sorter_results")
    op.drop_table("concerts")
    op.drop_table("news")
    op.drop_table("event_members")
    op.drop_table("events")
    op.drop_table("setlists")
    op.drop_table("members")
    op.drop_table("verification_tokens")
    op.drop_table("login_history")
    op.drop_table("refresh_tokens")
    op.drop_table("user_oshis")
    op.drop_table("users")

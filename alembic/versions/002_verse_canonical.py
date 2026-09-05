"""JKT48Verse canonical schema

- users: tambah kolom komunitas (role, avatar_seed, theme, notif, poin, sanksi) + seq
- anggota/news/schedule: bentuk kanonik JKT48Verse (menggantikan tabel legacy)
- tabel baru: chat, games, encyclopedia, glossary, motivations, notifications,
  bookmarks, birthday wishes, reports, moderation, contributors, activity, app_meta

Revision ID: 002_verse
Revises: 001_initial
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_verse"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- USERS: kolom komunitas ----------
    op.add_column("users", sa.Column("seq", sa.BigInteger(), nullable=True))
    op.execute("CREATE SEQUENCE users_seq_seq AS bigint OWNED BY users.seq")
    op.execute("UPDATE users SET seq = nextval('users_seq_seq')")
    op.execute("ALTER TABLE users ALTER COLUMN seq SET NOT NULL")
    op.execute("ALTER TABLE users ALTER COLUMN seq SET DEFAULT nextval('users_seq_seq')")
    op.create_unique_constraint("uq_users_seq", "users", ["seq"])

    # beri server default pada kolom waktu legacy 001
    op.alter_column("users", "created_at", server_default=sa.func.now())
    op.alter_column("users", "updated_at", server_default=sa.func.now())

    op.add_column("users", sa.Column("role", sa.String(16), nullable=False, server_default="MEMBER"))
    op.add_column("users", sa.Column("avatar_seed", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("theme", sa.String(8), nullable=False, server_default="system"))
    op.add_column("users", sa.Column("lang", sa.String(2), nullable=False, server_default="id"))
    op.add_column("users", sa.Column("multi_live_layout", sa.String(8), nullable=False, server_default="row-2"))
    op.add_column("users", sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("hide_oshi", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("notif_prefs", postgresql.JSONB(), nullable=True))
    op.add_column("users", sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("block_reason", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("muted_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("points", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("streak", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("last_daily_date", sa.Date(), nullable=True))

    op.add_column("login_history", sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("login_history", sa.Column("kind", sa.String(16), nullable=False, server_default="member"))
    op.add_column("login_history", sa.Column("username", sa.String(64), nullable=True))

    # ---------- DROP legacy (data skema lama; scraper bisa re-seed) ----------
    op.drop_table("user_oshis")
    op.drop_table("event_members")
    op.drop_table("events")
    op.drop_table("news")
    op.drop_table("members")
    op.drop_table("sorter_results")

    # ---------- MEMBERS (kanonik) ----------
    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("nickname", sa.String(60), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="regular"),
        sa.Column("team", sa.String(24), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("height", sa.String(12), nullable=True),
        sa.Column("blood_type", sa.String(4), nullable=True),
        sa.Column("horoscope", sa.String(20), nullable=True),
        sa.Column("jikoshoukai", sa.Text(), nullable=True),
        sa.Column("hobbies", sa.Text(), nullable=True),
        sa.Column("trivia", sa.Text(), nullable=True),
        sa.Column("socials", postgresql.JSONB(), nullable=True),
        sa.Column("show_birthday", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_members_slug", "members", ["slug"])
    op.create_index("ix_members_name", "members", ["name"])
    op.create_index("ix_members_gen", "members", ["generation"])
    op.create_index("ix_members_status", "members", ["status"])

    op.create_table(
        "user_oshi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_seq", sa.BigInteger(), sa.ForeignKey("users.seq", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("user_seq", "member_id", name="user_oshi_uq"),
    )
    op.create_index("ix_user_oshi_user_seq", "user_oshi", ["user_seq"])

    # ---------- SCHEDULES ----------
    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("type", sa.String(12), nullable=False, server_default="theater"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("map_url", sa.Text(), nullable=True),
        sa.Column("setlist", sa.String(120), nullable=True),
        sa.Column("ticket_status", sa.String(12), nullable=False, server_default="unknown"),
        sa.Column("ticket_url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("flag", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_schedules_title", "schedules", ["title"])
    op.create_index("ix_schedules_start_at", "schedules", ["start_at"])

    op.create_table(
        "schedule_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("schedule_id", sa.Integer(), sa.ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("schedule_id", "member_id", name="schedule_members_uq"),
    )
    op.create_index("ix_schedule_members_schedule", "schedule_members", ["schedule_id"])

    op.create_table(
        "schedule_reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_seq", sa.BigInteger(), sa.ForeignKey("users.seq", ondelete="CASCADE"), nullable=False),
        sa.Column("schedule_id", sa.Integer(), sa.ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_seq", "schedule_id", name="schedule_reminders_uq"),
    )
    op.create_index("ix_schedule_reminders_user", "schedule_reminders", ["user_seq"])

    # ---------- NEWS ----------
    op.create_table(
        "news",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(12), nullable=False, server_default="other"),
        sa.Column("is_highlighted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_news_slug", "news", ["slug"])
    op.create_index("ix_news_category", "news", ["category"])
    op.create_index("ix_news_published_at", "news", ["published_at"])

    # ---------- LIVE SESSIONS ----------
    op.create_table(
        "live_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), nullable=True),
        sa.Column("member_name", sa.String(100), nullable=False),
        sa.Column("platform", sa.String(12), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("room_key", sa.String(120), nullable=True),
        sa.Column("stream_url", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("viewers", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replay_url", sa.Text(), nullable=True),
    )
    op.create_index("ix_live_sessions_member", "live_sessions", ["member_id"])
    op.create_index("ix_live_sessions_started", "live_sessions", ["started_at"])
    op.create_index("ix_live_sessions_room_key", "live_sessions", ["room_key"])

    # ---------- WIKI ----------
    op.create_table(
        "encyclopedia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(60), nullable=False, unique=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "glossary",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("term", sa.String(80), nullable=False),
        sa.Column("meaning", sa.Text(), nullable=False),
    )
    op.create_index("ix_glossary_term", "glossary", ["term"])
    op.create_table(
        "motivations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("author", sa.String(100), nullable=True),
        sa.Column("template", sa.String(24), nullable=False, server_default="jkt48-red-white"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("featured_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------- GAMES ----------
    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=True),
        sa.Column("correct_index", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(8), nullable=False, server_default="easy"),
        sa.Column("category", sa.String(16), nullable=False, server_default="umum"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "guess_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hints", postgresql.JSONB(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("user_seq", sa.BigInteger(), nullable=True),
        sa.Column("game", sa.String(16), nullable=False),
        sa.Column("level", sa.String(8), nullable=True),
        sa.Column("question_ids", postgresql.JSONB(), nullable=True),
        sa.Column("current_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hints_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("question_shown_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_game_sessions_user", "game_sessions", ["user_seq"])
    op.create_table(
        "game_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_seq", sa.BigInteger(), nullable=False),
        sa.Column("game", sa.String(16), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("detail", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("game_scores_idx", "game_scores", ["game", "created_at"])
    op.create_table(
        "sorter_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_seq", sa.BigInteger(), nullable=False),
        sa.Column("ranking", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sorter_results_user", "sorter_results", ["user_seq"])

    # ---------- CHAT & MODERASI ----------
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_seq", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="MEMBER"),
        sa.Column("avatar_seed", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("body", sa.String(500), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("chat_created_idx", "chat_messages", ["created_at"])
    op.create_index("ix_chat_user", "chat_messages", ["user_seq"])
    op.create_table(
        "chat_reactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_seq", sa.BigInteger(), nullable=False),
        sa.Column("emoji", sa.String(8), nullable=False),
        sa.UniqueConstraint("message_id", "user_seq", name="chat_reactions_uq"),
    )
    op.create_index("ix_chat_reactions_message", "chat_reactions", ["message_id"])
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("reporter_seq", sa.BigInteger(), nullable=False),
        sa.Column("target_user_seq", sa.BigInteger(), nullable=True),
        sa.Column("target_username", sa.String(64), nullable=True),
        sa.Column("reason", sa.String(24), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_reports_message", "reports", ["message_id"])
    op.create_table(
        "banned_words",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("word", sa.String(60), nullable=False, unique=True),
    )
    op.create_table(
        "moderation_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_seq", sa.BigInteger(), nullable=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------- BIRTHDAY / BOOKMARK / NOTIF ----------
    op.create_table(
        "birthday_wishes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_seq", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("message", sa.String(200), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("member_id", "user_seq", "year", name="birthday_wishes_uq"),
    )
    op.create_index("ix_birthday_wishes_member", "birthday_wishes", ["member_id"])
    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_seq", sa.BigInteger(), nullable=False),
        sa.Column("entity_type", sa.String(16), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_seq", "entity_type", "entity_id", name="bookmarks_uq"),
    )
    op.create_index("ix_bookmarks_user", "bookmarks", ["user_seq"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_seq", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(24), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("href", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("notif_user_idx", "notifications", ["user_seq", "is_read"])
    op.create_table(
        "ai_search_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_seq", sa.BigInteger(), nullable=True),
        sa.Column("client_key", sa.String(64), nullable=True),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("query", sa.String(200), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("feedback", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_history_client", "ai_search_history", ["client_key"])
    op.create_table(
        "contributors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("role", sa.String(60), nullable=False),
        sa.Column("contribution", sa.Text(), nullable=False),
    )
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_seq", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_activity_user", "activity_logs", ["user_seq"])
    op.create_table(
        "app_meta",
        sa.Column("key", sa.String(40), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # tidak didukung: skema kanonik menggantikan legacy
    pass

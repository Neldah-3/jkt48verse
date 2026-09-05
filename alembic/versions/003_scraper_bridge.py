"""kolom jembatan untuk sync scraper (external id jkt48.com)

Scraper menulis ke schema kanonik JKT48Verse (migration 002). Agar upsert
idempoten tanpa merusak FK yang sudah ada, ditambahkan kolom external id:

- members.external_id  → id member dari jkt48.com (string numerik)
- news.source_id       → id berita dari jkt48.com
- schedules.source_id  → id event/teater dari jkt48.com

Revision ID: 003_scraper_bridge
Revises: 002_verse
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_scraper_bridge"
down_revision: Union[str, None] = "002_verse"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("members", sa.Column("external_id", sa.String(64), nullable=True))
    op.create_index("uq_members_external_id", "members", ["external_id"], unique=True)

    op.add_column("news", sa.Column("source_id", sa.String(32), nullable=True))
    op.create_index("uq_news_source_id", "news", ["source_id"], unique=True)
    op.add_column("news", sa.Column("source_url", sa.Text(), nullable=True))

    op.add_column("schedules", sa.Column("source_id", sa.String(80), nullable=True))
    op.create_index("uq_schedules_source_id", "schedules", ["source_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_schedules_source_id", table_name="schedules")
    op.drop_column("schedules", "source_id")
    op.drop_index("uq_news_source_id", table_name="news")
    op.drop_column("news", "source_url")
    op.drop_column("news", "source_id")
    op.drop_index("uq_members_external_id", table_name="members")
    op.drop_column("members", "external_id")

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from scripts.member_seed import member_fields
from scripts.seed import (
    seed_content,
    seed_games,
    seed_members,
    seed_setlists,
    seed_staff,
    seed_users,
)
from src.models import GuessQuestion, Member, QuizQuestion, User, UserOshi

pytestmark = pytest.mark.asyncio


async def test_full_seed_is_idempotent_and_preserves_references(pg_app):
    source = json.loads(
        (Path(__file__).parents[2] / "scripts/members_seed.json").read_text()
    )
    expected = len({member_fields(row)["slug"] for row in source})
    async with pg_app.sessions() as session:
        for seed in [
            seed_users,
            seed_staff,
            seed_members,
            seed_setlists,
            seed_content,
            seed_games,
        ]:
            await seed(session)
        await session.commit()
        members = (await session.execute(select(Member))).scalars().all()
        ids = {m.slug: m.id for m in members}
        assert len(members) == expected > 0
        assert all(m.external_id for m in members)
        uid = (
            await session.execute(select(User.seq).where(User.username == "fansdemo"))
        ).scalar_one()
        member = members[0]
        member.hobbies = "Curated locally"
        session.add(UserOshi(user_seq=uid, member_id=member.id, rank=0))
        await session.commit()
        for seed in [
            seed_users,
            seed_staff,
            seed_members,
            seed_setlists,
            seed_content,
            seed_games,
        ]:
            await seed(session)
        await session.commit()
        again = (await session.execute(select(Member))).scalars().all()
        assert {m.slug: m.id for m in again} == ids
        assert member.hobbies == "Curated locally"
        assert (
            await session.execute(select(func.count()).select_from(UserOshi))
        ).scalar_one() == 1
        assert (
            await session.execute(select(func.count()).select_from(QuizQuestion))
        ).scalar_one() > 0
        assert (
            await session.execute(select(func.count()).select_from(GuessQuestion))
        ).scalar_one() > 0
        # Explicit member IDs must not leave the SERIAL sequence behind.
        fresh = Member(slug="new-test-member", name="Test", nickname="Test")
        session.add(fresh)
        await session.flush()
        assert fresh.id > max(ids.values())

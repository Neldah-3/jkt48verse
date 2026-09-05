import asyncio
import json
from datetime import date
from pathlib import Path

import pytest

from scripts.member_seed import birth_date, member_fields


def test_checked_in_snapshot_is_convertible_and_has_active_members():
    rows = json.loads(
        (Path(__file__).parents[1] / "scripts/members_seed.json").read_text()
    )
    converted = [member_fields(row) for row in rows]
    assert len(converted) == len(rows) > 0
    assert all(row["slug"] and row["external_id"] for row in converted)
    assert any(row["status"] == "trainee" for row in converted)
    assert any(row["status"] == "graduated" for row in converted)
    assert any(row["status"] == "regular" for row in converted)


def test_legacy_member_fields_and_indonesian_dates():
    result = member_fields(
        {
            "id": "277",
            "name": "Abigail Rachel",
            "nickname": "Aralie",
            "active": True,
            "member_type": "TRAINEE",
            "generation": "12",
            "birthdate": "06 Agustus 2008",
            "href": "/member/detail?member=abigail-rachel-1&type=TRAINEE",
            "jiko": "Halo!",
        }
    )
    assert result["external_id"] == "277"
    assert result["slug"] == "abigail-rachel"
    assert result["status"] == "trainee"
    assert result["generation"] == 12
    assert result["birth_date"] == date(2008, 8, 6)
    assert result["jikoshoukai"] == "Halo!"
    assert result["socials"] == {}
    assert birth_date("2008-08-06") == result["birth_date"]
    assert birth_date(None) is None


def test_invalid_seed_rows_fail_instead_of_silently_disappearing():
    with pytest.raises(ValueError):
        member_fields({"id": "1"})
    with pytest.raises(ValueError):
        birth_date("31 Februari 2000")


def test_demo_seeder_refuses_non_development_before_touching_database(monkeypatch):
    from scripts.seed import seed_users
    from src.config import config

    monkeypatch.setattr(config, "ENV", "prod")
    with pytest.raises(ValueError, match="ENV=dev"):
        asyncio.run(seed_users(None))

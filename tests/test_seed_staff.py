"""Seeder kredensial staff: hanya slot lengkap 4/4 yang jadi akun.

Tes ini tidak butuh database — session diganti dengan objek palsu yang
meniru ``AsyncSession`` untuk bagian yang dipakai ``seed_staff``.
"""

import asyncio

import pytest

from src.auth import staff_credentials as sc


class FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalars(self):
        return FakeScalars(self._rows)


class FakeSession:
    """Menyimpan user yang sudah ada + menampung user baru yang di-add."""

    def __init__(self, existing=None):
        self.existing = existing or []
        self.added = []

    async def execute(self, query):  # query tidak diinspeksi (urutan pemakaian tetap)
        return FakeResult(list(self.existing))

    def add(self, obj):
        self.added.append(obj)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for role, count in sc.ROLE_SLOTS:
        for slot in range(1, count + 1):
            for field in sc.REQUIRED_FIELDS:
                monkeypatch.delenv(f"{sc.ROLE_PREFIX[role]}_{slot}_{field}", raising=False)
    sc.reload()
    yield
    sc.reload()


def _set(monkeypatch, label, **values):
    for key, value in values.items():
        monkeypatch.setenv(f"{label}_{key}", value)
    sc.reload()


def _run(coro):
    return asyncio.run(coro)


def test_seed_membuat_hanya_slot_yang_lengkap(monkeypatch):
    from scripts.seed import seed_staff

    _set(
        monkeypatch,
        "ADMIN_1",
        USERNAME="AdminSatu",
        EMAIL="admin1@jkt48verse.local",
        PASSWORD="Password-1",
        ACCESS_CODE="CODE-1",
    )
    # slot tidak lengkap: ACCESS_CODE kosong → false
    _set(
        monkeypatch,
        "ADMIN_2",
        USERNAME="AdminDua",
        EMAIL="admin2@jkt48verse.local",
        PASSWORD="Password-2",
        ACCESS_CODE="",
    )
    # 3 moderator lengkap, sisanya kosong
    for i in (1, 2, 3):
        _set(
            monkeypatch,
            f"MOD_{i}",
            USERNAME=f"mod{i}",
            EMAIL=f"mod{i}@jkt48verse.local",
            PASSWORD=f"Password-{i}",
            ACCESS_CODE=f"MODCODE-{i}",
        )

    session = FakeSession()
    _run(seed_staff(session))

    created = session.added
    assert len(created) == 4  # 1 admin + 3 moderator
    assert {u.role for u in created} == {"ADMIN", "MODERATOR"}
    assert "AdminSatu" in {u.username for u in created}
    assert "AdminDua" not in {u.username for u in created}  # slot false → tidak dibuat
    for u in created:
        assert u.provider == sc.PROVIDER
        assert u.is_email_verified is True
        assert u.password and u.password.startswith("$2")


def test_seed_menonaktifkan_user_staff_yang_slotnya_false(monkeypatch):
    from src.models import User

    from scripts.seed import seed_staff

    # user lama dari slot MOD_5, tapi env MOD_5 kini tidak dilengkapi
    orphan = User(username="mod5", email="mod5@jkt48verse.local", password="$2b$12$abc")
    orphan.provider = sc.PROVIDER

    session = FakeSession(existing=[orphan])
    _run(seed_staff(session))

    assert orphan.password is None, "user dengan slot false harus tidak bisa login"
    assert session.added == []

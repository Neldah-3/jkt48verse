"""Integrasi login staff: code akses wajib & harus persis.

Endpoint /auth/signin kini menerima field form ``access_code``.
Akun yang lahir dari slot ADMIN_n / MOD_n tidak bisa login tanpa code akses
yang sama persis (besar/kecil huruf, spasi, dan karakter dihitung).
"""

import pytest
from fastapi.testclient import TestClient

from src.auth import staff_credentials as sc
from src.dependencies import get_auth_service
from src.main import app

STAFF = {
    "USERNAME": "AdminSatu",
    "EMAIL": "admin1@jkt48verse.local",
    "PASSWORD": "Password-1",
    "ACCESS_CODE": "JKT48-Admin-01",
}


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)


class FakeSession:
    async def execute(self, *args, **kwargs):
        return FakeResult([])

    async def commit(self):
        return None


class _SessionFactory:
    async def __aenter__(self):
        return FakeSession()

    async def __aexit__(self, *args):
        return False


class FakeSecurityService:
    def __init__(self):
        self.failed = 0

    async def handle_failed_login(self, *args, **kwargs):
        self.failed += 1


class FakeAuthService:
    def __init__(self):
        self.security_service = FakeSecurityService()

    async def authenticate_user(self, username, password):
        if username not in (STAFF["USERNAME"], STAFF["EMAIL"]):
            raise AssertionError("user tidak dikenal")
        if password != STAFF["PASSWORD"]:
            raise AssertionError("password salah")
        return type(
            "User",
            (),
            {
                "userId": "u-1",
                "username": STAFF["USERNAME"],
                "email": STAFF["EMAIL"],
            },
        )()

    def create_access_token(self, data):
        return "access-token-abc"

    async def register_refresh_token_activity(self, *args, **kwargs):
        return "refresh-token-abc"


@pytest.fixture()
def client(monkeypatch):
    for role, count in sc.ROLE_SLOTS:
        for slot in range(1, count + 1):
            for field in sc.REQUIRED_FIELDS:
                monkeypatch.delenv(f"{sc.ROLE_PREFIX[role]}_{slot}_{field}", raising=False)
    for key, value in STAFF.items():
        monkeypatch.setenv(f"ADMIN_1_{key}", value)
    sc.reload()

    # hindari sentuh database saat pengecekan blokir
    monkeypatch.setattr(
        "src.database.database_instance.session_factory", lambda: _SessionFactory()
    )
    fake = FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: fake
    yield TestClient(app), fake
    app.dependency_overrides.pop(get_auth_service, None)
    sc.reload()


def test_login_staff_tanpa_code_akses_ditolak(client):
    c, _ = client
    res = c.post(
        "/api/auth/signin",
        data={"username": STAFF["USERNAME"], "password": STAFF["PASSWORD"], "access_code": ""},
    )
    assert res.status_code == 401
    assert "code akses" in res.json()["detail"].lower()


def test_login_staff_code_salah_ditolak_dan_dihitung_gagal(client):
    c, fake = client
    res = c.post(
        "/api/auth/signin",
        data={
            "username": STAFF["USERNAME"],
            "password": STAFF["PASSWORD"],
            "access_code": "jkt48-admin-01",  # beda besar/kecil
        },
    )
    assert res.status_code == 401
    assert fake.security_service.failed == 1


def test_login_staff_code_benar_berhasil(client):
    c, _ = client
    res = c.post(
        "/api/auth/signin",
        data={
            "username": STAFF["USERNAME"],
            "password": STAFF["PASSWORD"],
            "access_code": STAFF["ACCESS_CODE"],
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["access_token"] == "access-token-abc"


def test_slot_tidak_lengkap_tidak_bisa_login(client, monkeypatch):
    c, _ = client
    monkeypatch.delenv("ADMIN_1_ACCESS_CODE")
    sc.reload()
    res = c.post(
        "/api/auth/signin",
        data={
            "username": STAFF["USERNAME"],
            "password": STAFF["PASSWORD"],
            "access_code": STAFF["ACCESS_CODE"],
        },
    )
    assert res.status_code == 403
    assert "ADMIN_1" in res.json()["detail"]

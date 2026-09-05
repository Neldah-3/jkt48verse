"""Kredensial staff: 3 Admin + 10 Moderator, aturan ALL-OR-NOTHING.

Satu slot harus punya USERNAME + EMAIL + PASSWORD + ACCESS_CODE.
Kalau satu saja kosong ⇒ slot = False (nonaktif) & akun tidak bisa login.
Nilai dicocokkan 100% persis (besar/kecil huruf, spasi, karakter dihitung).
"""

import pytest

from src.auth import staff_credentials as sc

FULL = {
    "USERNAME": "Neldah",
    "EMAIL": "neldah@jkt48verse.local",
    "PASSWORD": "Ra#hasia-123",
    "ACCESS_CODE": "JKT48-Admin-01",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Bersihkan semua env staff sebelum & sesudah tiap test."""
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


def test_jumlah_slot_yang_disediakan():
    assert sc.ADMIN_SLOT_COUNT == 3
    assert sc.MODERATOR_SLOT_COUNT == 10
    summary = sc.summary()
    assert summary["admin"]["slots"] == 3
    assert summary["mod"]["slots"] == 10
    # total slot yang dilaporkan = 13
    assert len(sc.report()) == 13


def test_slot_kosong_bernilai_false_tanpa_didefinisikan():
    assert sc.staff_credentials() == []
    report = {row["label"]: row for row in sc.report()}
    for row in report.values():
        assert row["active"] is False
        assert row["defined"] is False


def test_slot_lengkap_menjadi_aktif(monkeypatch):
    _set(monkeypatch, "ADMIN_1", **FULL)
    creds = sc.admin_credentials()
    assert len(creds) == 1
    cred = creds[0]
    assert cred.role == "ADMIN" and cred.slot == 1
    assert cred.username == "Neldah"
    assert sc.moderator_credentials() == []
    assert sc.summary()["admin"]["active"] == 1


@pytest.mark.parametrize("hilang", list(sc.REQUIRED_FIELDS))
def test_satu_field_kosong_membuat_slot_nonaktif(monkeypatch, hilang):
    """Satu karakter pun hilang ⇒ false & tidak bisa login."""
    values = dict(FULL)
    values[hilang] = ""
    _set(monkeypatch, "ADMIN_2", **values)
    assert sc.admin_credentials() == []
    slot = {row["label"]: row for row in sc.report()}["ADMIN_2"]
    assert slot["active"] is False
    assert slot["defined"] is True
    assert hilang in " ".join(slot["missing"])

    # user dengan identitas itu tetap tidak bisa login
    gate = sc.gate_login(FULL["USERNAME"], FULL["EMAIL"], FULL["ACCESS_CODE"])
    assert gate is not None
    assert gate.code == "SLOT_INCOMPLETE"


def test_tidak_semua_slot_wajib_diisi(monkeypatch):
    """Cukup 1 user yang lengkap; sisanya boleh kosong (false)."""
    _set(monkeypatch, "MOD_7", **FULL)
    creds = sc.moderator_credentials()
    assert len(creds) == 1 and creds[0].slot == 7
    assert sc.summary()["mod"] == {"active": 1, "slots": 10, "inactive": 9}


def test_login_tanpa_code_akses_ditolak(monkeypatch):
    _set(monkeypatch, "ADMIN_1", **FULL)
    gate = sc.gate_login(FULL["USERNAME"], FULL["EMAIL"], "")
    assert gate is not None and gate.code == "CODE_REQUIRED"

    gate = sc.gate_login(FULL["USERNAME"], FULL["EMAIL"], None)
    assert gate is not None and gate.code == "CODE_REQUIRED"


def test_code_akses_case_sensitive_dan_karakter_persis(monkeypatch):
    _set(monkeypatch, "ADMIN_1", **FULL)


    # benar → boleh login
    assert sc.gate_login(FULL["USERNAME"], FULL["EMAIL"], "JKT48-Admin-01") is None
    # beda besar/kecil → ditolak
    assert sc.gate_login(FULL["USERNAME"], FULL["EMAIL"], "jkt48-admin-01").code == "CODE_INVALID"
    # kurang satu karakter → ditolak
    assert sc.gate_login(FULL["USERNAME"], FULL["EMAIL"], "JKT48-Admin-0").code == "CODE_INVALID"
    # spasi ekstra → ditolak (spasi ikut terhitung)
    assert sc.gate_login(FULL["USERNAME"], FULL["EMAIL"], " JKT48-Admin-01").code == "CODE_INVALID"


def test_username_email_dicocokkan_persis(monkeypatch):
    _set(monkeypatch, "ADMIN_1", **FULL)
    # persis → ketemu
    assert sc.find_credential(FULL["USERNAME"], FULL["EMAIL"]) is not None
    # beda besar/kecil → tidak ketemu (nilai dipakai apa adanya)
    assert sc.find_credential("neldah", "Neldah@JKT48verse.local") is None
    # dan kalau sampai tidak ketemu slot, user biasa tetap boleh login
    assert sc.gate_login("neldah", "Neldah@JKT48verse.local", "") is None


def test_user_biasa_tidak_butuh_code(monkeypatch):
    """User di luar slot staff tetap login seperti biasa."""
    _set(monkeypatch, "MOD_1", **FULL)
    assert sc.gate_login("fansdemo", "fans@jkt48verse.local", "") is None


def test_username_duplikat_dinonaktifkan(monkeypatch):
    _set(monkeypatch, "ADMIN_1", **FULL)
    dup = dict(FULL, EMAIL="kedua@jkt48verse.local")
    _set(monkeypatch, "ADMIN_2", **dup)
    creds = sc.admin_credentials()
    assert len(creds) == 1 and creds[0].slot == 1
    slot2 = {row["label"]: row for row in sc.report()}["ADMIN_2"]
    assert slot2["active"] is False and "duplikat" in slot2["reason"]


def test_laporan_menyensor_nilai_rahasia(monkeypatch):
    _set(monkeypatch, "ADMIN_1", **FULL)
    row = {r["label"]: r for r in sc.report()}["ADMIN_1"]
    blob = str(row)
    assert FULL["PASSWORD"] not in blob
    assert FULL["ACCESS_CODE"] not in blob
    assert row["email"].endswith("@jkt48verse.local")


def test_mod_10_slot_tersedia(monkeypatch):
    for i in range(1, 11):
        _set(
            monkeypatch,
            f"MOD_{i}",
            USERNAME=f"mod{i}",
            EMAIL=f"mod{i}@jkt48verse.local",
            PASSWORD=f"Password-{i}",
            ACCESS_CODE=f"MOD-CODE-{i}",
        )
    creds = sc.moderator_credentials()
    assert len(creds) == 10
    assert sc.summary()["mod"]["active"] == 10


def test_signin_menerima_field_access_code():
    """Endpoint /auth/signin harus menerima field form access_code."""
    from src.main import app

    route = next(r for r in app.routes if getattr(r, "path", None) == "/api/auth/signin")
    names = {p.name for p in route.dependant.body_params}
    assert "access_code" in names

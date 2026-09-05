"""Smoke test + regression test bug kritis JKT48Verse.

Tidak membutuhkan database/Redis sungguhan: hanya verifikasi struktur
aplikasi, routing, dan util murni.
"""

import re
from datetime import datetime, timezone


def test_app_imports_and_routes_registered():
    from src.main import app

    paths = {getattr(r, "path", None) for r in app.routes}
    for expected in [
        "/api/health",
        "/api/auth/signin",
        "/api/auth/me",
        "/api/members",
        "/api/schedules/upcoming",
        "/api/chat",
        "/api/ai/search",
        "/api/games/leaderboard/daily",
        "/api/motivation/daily",
    ]:
        assert expected in paths, f"route {expected} hilang"


def test_reminder_route_not_shadowed_by_schedule_detail():
    """Regression: GET /schedules/reminders harus terdaftar SEBELUM
    GET /schedules/{schedule_id} agar tidak 422 (shadowed)."""
    from src.main import app

    idx_reminders = idx_detail = None
    for i, r in enumerate(app.routes):
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", set()) or set()
        if path == "/api/schedules/reminders" and "GET" in methods:
            idx_reminders = i
        if path == "/api/schedules/{schedule_id}" and "GET" in methods:
            idx_detail = i
    assert idx_reminders is not None, "route GET /api/schedules/reminders tidak ada"
    assert idx_detail is not None, "route GET /api/schedules/{schedule_id} tidak ada"
    assert idx_reminders < idx_detail, "/schedules/reminders tertutup oleh /schedules/{schedule_id}"


def test_reminder_toggle_accepts_json_body():
    """Regression: frontend mengirim body {scheduleId}; backend harus
    menerimanya sebagai Pydantic model (bukan query param)."""
    from src.verse.routes.community import ReminderToggleIn

    data = ReminderToggleIn(**{"scheduleId": 12})
    assert data.scheduleId == 12


def test_token_models_have_to_dict():
    """Regression: repository auth memanggil .to_dict() pada model token;
    ketiadaan method ini pernah membuat verifikasi OTP error 500."""
    from src.models import LoginHistory, RefreshToken, VerificationToken

    vt = VerificationToken(
        user_id="u1",
        hash_token="h",
        token_type="otp",
        expires_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    d = vt.to_dict()
    assert d["userId"] == "u1"
    assert d["tokenType"] == "otp"
    assert d["expiresAt"].year == 2026

    rt = RefreshToken(user_id="u1", hash_refresh_token="x")
    assert rt.to_dict()["hashRefreshToken"] == "x"

    lh = LoginHistory(user_id="u1")
    assert lh.to_dict()["userId"] == "u1"


def test_profile_in_uses_camelcase_field():
    """Regression: PATCH /account/profile gagal karena akses `avatar_seed`
    padahal nama field Pydantic adalah `avatarSeed`."""
    from src.verse.routes.community import ProfileIn

    p = ProfileIn(bio="halo", avatarSeed=4)
    assert p.avatarSeed == 4


def test_wib_helpers():
    from src.verse.helpers import wib_date_key, wib_midnight, wib_parts

    # 2026-09-05 00:30 WIB == 2026-09-04 17:30 UTC
    utc = datetime(2026, 9, 4, 17, 30, tzinfo=timezone.utc)
    p = wib_parts(utc)
    assert (p["day"], p["month"], p["year"]) == (5, 9, 2026)
    assert wib_date_key(utc) == "2026-09-05"
    mid = wib_midnight(2026, 9, 5)
    assert mid == datetime(2026, 9, 4, 17, 0, tzinfo=timezone.utc)


def test_moderation_normalize_and_emoji():
    from src.verse.moderation import check_emoji, normalize_text

    assert normalize_text("4nj1ng") == "anjing"
    assert "goblok" in normalize_text("GOBLOKKKK!!!")

    ok, bad = check_emoji("halo semua 😊")
    assert ok and bad is None
    ok, bad = check_emoji("halo 👋")
    assert not ok and bad == "👋"


def test_daily_motivation_uses_date_not_string():
    """Regression: featured_on (DATE) pernah dibandingkan dengan string
    sehingga Postgres menolak (date = varchar)."""
    import inspect

    from src.verse.routes import content

    src = inspect.getsource(content.daily_motivation)
    assert "fromisoformat" in src, "daily_motivation harus memakai objek date"


def test_account_overview_imports_member():
    """Regression: NameError 'Member' di /account/overview."""
    import inspect

    from src.verse.routes import community

    src = inspect.getsource(community.account_overview)
    assert re.search(r"from src\.models import \([^)]*\bMember\b[^)]*\)", src, re.S), (
        "account_overview harus mengimpor Member"
    )


def test_guess_view_builds_dict_options():
    """Regression: _guess_view pernah mencampur Row dan dict sehingga
    `o.id` meledak dengan AttributeError pada opsi dict."""
    import inspect

    from src.verse.routes import games

    src = inspect.getsource(games._guess_view)
    assert '{"id": o["id"], "name": o["name"]}' in src, (
        "opsi guess harus diserialisasi dari dict konsisten"
    )


def test_config_admin_password_not_hardcoded():
    from src.config import Settings

    s = Settings(
        ENV="dev",
        SECRET_KEY="dummy_secret_key_for_testing_12345",
        DATABASE_URL="postgresql://u:p@localhost/db",
    )
    assert s.ADMIN_PASSWORD.get_secret_value() == "", (
        "password admin tidak boleh punya default hardcoded"
    )

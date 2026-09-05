import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from sqlalchemy import func, select

from scripts.seed import seed_staff
from src.auth import staff_credentials as sc
from src.config import config
from src.models import RefreshToken, User
from src.users.repository import UserRepository
from src.users.service import UserService

pytestmark = pytest.mark.asyncio
PASSWORD = "OnlyForRegression123!"


async def make_user(pg_app, name="VerseFan", email="fan@example.org"):
    async with pg_app.sessions() as session:
        user = await UserService(session).create_user(name, email, PASSWORD)
        user.is_email_verified = True
        await session.commit()
        return user.user_id


async def user_state(pg_app, user_id):
    async with pg_app.sessions() as session:
        return (
            await session.execute(select(User).where(User.user_id == user_id))
        ).scalar_one()


async def login(pg_app, username="VerseFan", password=PASSWORD, code=""):
    return await pg_app.client.post(
        "/api/auth/signin",
        data={
            "username": username,
            "password": password,
            "access_code": code,
        },
    )


async def make_staff(pg_app, monkeypatch):
    for key, value in {
        "USERNAME": "AdminSatu",
        "EMAIL": "AdminSatu@example.org",
        "PASSWORD": PASSWORD,
        "ACCESS_CODE": "Case Sensitive Code",
    }.items():
        monkeypatch.setenv(f"ADMIN_1_{key}", value)
    sc.reload()
    async with pg_app.sessions() as session:
        await seed_staff(session)
        await session.commit()
        return (await session.execute(select(User.user_id))).scalar_one()


async def test_failed_passwords_survive_request_rollback_and_lock(pg_app):
    uid = await make_user(pg_app)
    for expected in range(1, config.max_login_attempts + 1):
        response = await login(pg_app, password="wrong")
        assert response.status_code == 401
        assert (await user_state(pg_app, uid)).failed_login_attempts == expected
    user = await user_state(pg_app, uid)
    assert user.is_account_locked and user.account_locked_until > datetime.now(
        timezone.utc
    )
    assert (await login(pg_app)).status_code == 400
    assert not pg_app.client.cookies.get("token")


async def test_security_counter_does_not_commit_other_request_writes(pg_app):
    uid = await make_user(pg_app)
    async with pg_app.sessions() as session:
        user = await session.get(User, (await user_state(pg_app, uid)).id)
        user.bio = "must be rolled back"
        await session.flush()
        assert await UserRepository(session).record_failed_login(uid, 5, 15) == 1
        await session.rollback()
    user = await user_state(pg_app, uid)
    assert user.bio is None
    assert user.failed_login_attempts == 1


async def test_wrong_staff_access_code_is_counted_without_reset(pg_app, monkeypatch):
    uid = await make_staff(pg_app, monkeypatch)
    for expected in range(1, 6):
        response = await login(pg_app, "AdminSatu", code="wrong-code")
        assert response.status_code == 401
        assert (await user_state(pg_app, uid)).failed_login_attempts == expected
    assert (
        await login(pg_app, "AdminSatu", code="Case Sensitive Code")
    ).status_code == 400


async def test_success_resets_failures_only_after_both_credentials_pass(
    pg_app, monkeypatch
):
    uid = await make_staff(pg_app, monkeypatch)
    await login(pg_app, "AdminSatu", code="wrong-code")
    response = await login(pg_app, "AdminSatu", code="Case Sensitive Code")
    assert response.status_code == 200
    assert (await user_state(pg_app, uid)).failed_login_attempts == 0
    assert (await pg_app.client.get("/api/auth/me")).json()["role"] == "ADMIN"


async def test_expired_lock_starts_a_new_failure_window(pg_app):
    uid = await make_user(pg_app)
    async with pg_app.sessions() as session:
        user = (await session.execute(select(User))).scalar_one()
        user.failed_login_attempts = 5
        user.is_account_locked = True
        user.account_locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        await session.commit()
    response = await asyncio.wait_for(login(pg_app, password="wrong"), timeout=10)
    assert response.status_code == 401
    user = await user_state(pg_app, uid)
    assert user.failed_login_attempts == 1 and not user.is_account_locked
    assert (await login(pg_app)).status_code == 200


async def test_concurrent_failures_are_not_lost(pg_app, monkeypatch):
    uid = await make_user(pg_app)
    monkeypatch.setattr(config, "MAX_LOGIN_ATTEMPTS", 20)
    responses = await asyncio.wait_for(
        asyncio.gather(*(login(pg_app, password="wrong") for _ in range(8))), timeout=20
    )
    assert all(r.status_code == 401 for r in responses)
    assert (await user_state(pg_app, uid)).failed_login_attempts == 8


async def test_normal_user_case_insensitive_but_staff_exact(pg_app, monkeypatch):
    await make_user(pg_app)
    for identity in ["VerseFan", "versefan", "VERSEFAN", "FAN@EXAMPLE.ORG"]:
        assert (await login(pg_app, identity)).status_code == 200
    # Staff has a different identity so it cannot collide with the member above.
    for key, value in {
        "USERNAME": "StaffCase",
        "EMAIL": "Staff@example.org",
        "PASSWORD": PASSWORD,
        "ACCESS_CODE": "Code",
    }.items():
        monkeypatch.setenv(f"ADMIN_1_{key}", value)
    async with pg_app.sessions() as session:
        await seed_staff(session)
        await session.commit()
    assert (await login(pg_app, "staffcase", code="Code")).status_code == 401
    assert (await login(pg_app, "StaffCase", code="Code")).status_code == 200
    assert (await login(pg_app, "Staff@example.org", code="Code")).status_code == 200


async def test_disabled_staff_sessions_never_revive_on_reactivation(
    pg_app, monkeypatch
):
    uid = await make_staff(pg_app, monkeypatch)
    assert (
        await login(pg_app, "AdminSatu", code="Case Sensitive Code")
    ).status_code == 200
    assert (await pg_app.client.get("/api/admin/stats")).status_code == 200
    old_cookies = dict(pg_app.client.cookies)
    monkeypatch.setenv("ADMIN_1_ACCESS_CODE", "")
    async with pg_app.sessions() as session:
        await seed_staff(session)
        await session.commit()
        assert (
            await session.execute(select(func.count()).select_from(RefreshToken))
        ).scalar_one() == 0
    assert (await user_state(pg_app, uid)).password is None
    assert (await pg_app.client.get("/api/admin/stats")).status_code in (401, 403, 404)
    assert (await pg_app.client.get("/api/auth/me")).status_code == 401
    assert (
        await pg_app.client.post(
            "/api/auth/refresh", headers={"x-csrf-token": old_cookies["csrf_token"]}
        )
    ).status_code == 401
    monkeypatch.setenv("ADMIN_1_ACCESS_CODE", "Case Sensitive Code")
    async with pg_app.sessions() as session:
        await seed_staff(session)
        await session.commit()
    assert (await pg_app.client.get("/api/admin/stats")).status_code in (401, 403, 404)
    assert (
        await login(pg_app, "AdminSatu", code="Case Sensitive Code")
    ).status_code == 200


async def test_removing_staff_slot_blocks_access_even_before_reseeding(
    pg_app, monkeypatch
):
    await make_staff(pg_app, monkeypatch)
    assert (
        await login(pg_app, "AdminSatu", code="Case Sensitive Code")
    ).status_code == 200
    csrf = pg_app.client.cookies["csrf_token"]
    for field in sc.REQUIRED_FIELDS:
        monkeypatch.setenv(f"ADMIN_1_{field}", "")
    sc.reload()
    assert (await pg_app.client.get("/api/auth/me")).status_code == 401
    assert (
        await pg_app.client.post("/api/auth/refresh", headers={"x-csrf-token": csrf})
    ).status_code == 401
    async with pg_app.sessions() as session:
        assert (
            await session.execute(select(func.count()).select_from(RefreshToken))
        ).scalar_one() == 0


async def test_expired_access_token_and_refresh_cookie_return_401_not_guest_200(pg_app):
    uid = await make_user(pg_app)
    assert (await pg_app.client.get("/api/auth/me")).json()["role"] == "GUEST"
    await login(pg_app)
    access = pg_app.client.cookies["token"]
    claims = jwt.decode(access, config.secret_key, algorithms=[config.algorithm])
    assert claims["sub"] == uid and claims["sid"]
    claims["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired = jwt.encode(claims, config.secret_key, algorithm=config.algorithm)
    pg_app.client.cookies.set("token", expired, domain="testserver.local", path="/")
    assert (await pg_app.client.get("/api/auth/me")).status_code == 401
    pg_app.client.cookies.delete("token")
    assert (await pg_app.client.get("/api/auth/me")).status_code == 401
    csrf = pg_app.client.cookies["csrf_token"]
    assert (
        await pg_app.client.post("/api/auth/refresh", headers={"x-csrf-token": csrf})
    ).status_code == 200
    assert (await pg_app.client.get("/api/auth/me")).json()["userId"]


async def test_logout_revokes_access_and_refresh_tokens(pg_app):
    await make_user(pg_app)
    await login(pg_app)
    saved = dict(pg_app.client.cookies)
    assert (
        await pg_app.client.post(
            "/api/auth/logout", headers={"x-csrf-token": saved["csrf_token"]}
        )
    ).status_code == 200
    pg_app.client.cookies.clear()
    pg_app.client.cookies.update(saved)
    assert (await pg_app.client.get("/api/auth/me")).status_code == 401
    assert (
        await pg_app.client.post(
            "/api/auth/refresh", headers={"x-csrf-token": saved["csrf_token"]}
        )
    ).status_code == 401


async def test_seed_accounts_cannot_login_in_production(pg_app, monkeypatch):
    await make_user(pg_app)
    async with pg_app.sessions() as session:
        user = (await session.execute(select(User))).scalar_one()
        user.provider = "seed"
        await session.commit()
    await login(pg_app)
    csrf = pg_app.client.cookies["csrf_token"]
    monkeypatch.setattr(config, "ENV", "prod")
    assert (await pg_app.client.get("/api/auth/me")).status_code == 401
    assert (
        await pg_app.client.post("/api/auth/refresh", headers={"x-csrf-token": csrf})
    ).status_code == 401
    assert (await login(pg_app)).status_code == 401


# ---------------- Lupa password & reset password (link + OTP) ----------------
NEW_PASSWORD = "PasswordBaru123!"


async def test_password_reset_otp_full_flow(pg_app):
    await make_user(pg_app)
    r = await pg_app.client.post(
        "/api/auth/forgot-password/otp", json={"email": "fan@example.org"}
    )
    assert r.status_code == 200
    body = r.json()
    # RESEND kosong + ENV=dev → kode dikembalikan sebagai devCode
    code = body["devCode"]
    assert len(code) == 6 and code.isdigit()

    r = await pg_app.client.post(
        "/api/auth/reset-password/otp",
        json={
            "email": "fan@example.org",
            "code": code,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert r.status_code == 200 and r.json()["reset"] is True

    # Password lama tidak bisa lagi, password baru bisa dipakai login.
    assert (await login(pg_app)).status_code == 401
    assert (await login(pg_app, password=NEW_PASSWORD)).status_code == 200


async def test_password_reset_otp_unknown_email_is_generic(pg_app):
    r = await pg_app.client.post(
        "/api/auth/forgot-password/otp", json={"email": "ghost@example.org"}
    )
    # Anti-enumerasi: respons 200 generik tanpa devCode.
    assert r.status_code == 200
    assert "devCode" not in r.json()


async def test_password_reset_otp_wrong_code_limited_then_reusable(pg_app):
    await make_user(pg_app)
    r = await pg_app.client.post(
        "/api/auth/forgot-password/otp", json={"email": "fan@example.org"}
    )
    code = r.json()["devCode"]

    for i in range(5):
        wrong = "000000" if code != "000000" else "000001"
        r = await pg_app.client.post(
            "/api/auth/reset-password/otp",
            json={
                "email": "fan@example.org",
                "code": wrong,
                "new_password": NEW_PASSWORD,
                "confirm_password": NEW_PASSWORD,
            },
        )
        assert r.status_code == 400 and r.json()["reset"] is False
        if i == 4:
            assert "Terlalu banyak percobaan" in r.json()["message"]

    # Kode lama hangus walau sekarang ditebak benar.
    r = await pg_app.client.post(
        "/api/auth/reset-password/otp",
        json={
            "email": "fan@example.org",
            "code": code,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert r.status_code == 400

    # Minta kode baru → sukses dipakai reset.
    r = await pg_app.client.post(
        "/api/auth/forgot-password/otp", json={"email": "fan@example.org"}
    )
    code2 = r.json()["devCode"]
    r = await pg_app.client.post(
        "/api/auth/reset-password/otp",
        json={
            "email": "fan@example.org",
            "code": code2,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert r.status_code == 200 and r.json()["reset"] is True


async def test_password_reset_otp_expired_code_rejected(pg_app):
    from src.models import VerificationToken

    await make_user(pg_app)
    r = await pg_app.client.post(
        "/api/auth/forgot-password/otp", json={"email": "fan@example.org"}
    )
    code = r.json()["devCode"]

    async with pg_app.sessions() as session:
        row = (await session.execute(select(VerificationToken))).scalar_one()
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await session.commit()

    r = await pg_app.client.post(
        "/api/auth/reset-password/otp",
        json={
            "email": "fan@example.org",
            "code": code,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert r.status_code == 400 and r.json()["reset"] is False


async def test_password_reset_otp_validation(pg_app):
    await make_user(pg_app)
    r = await pg_app.client.post(
        "/api/auth/forgot-password/otp", json={"email": "fan@example.org"}
    )
    code = r.json()["devCode"]
    # Konfirmasi password tidak cocok
    r = await pg_app.client.post(
        "/api/auth/reset-password/otp",
        json={
            "email": "fan@example.org",
            "code": code,
            "new_password": NEW_PASSWORD,
            "confirm_password": "Beda123!Beda",
        },
    )
    assert r.status_code == 400 and "tidak cocok" in r.json()["message"]
    # Password terlalu pendek
    r = await pg_app.client.post(
        "/api/auth/reset-password/otp",
        json={
            "email": "fan@example.org",
            "code": code,
            "new_password": "pendek",
            "confirm_password": "pendek",
        },
    )
    assert r.status_code == 400 and "8 karakter" in r.json()["message"]


async def test_password_reset_link_flow(pg_app, monkeypatch):
    """Alur link email: /auth/forgot-password → /auth/reset-password?token=."""
    from unittest.mock import AsyncMock

    from src.auth.email_service import EmailService

    sent = AsyncMock()
    monkeypatch.setattr(EmailService, "send_password_reset", sent)

    await make_user(pg_app)
    r = await pg_app.client.post(
        "/api/auth/forgot-password", json={"email": "fan@example.org"}
    )
    assert r.status_code == 200
    token = sent.call_args[0][2]  # (self, email, token, username)

    r = await pg_app.client.post(
        "/api/auth/reset-password",
        json={
            "token": token,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert r.status_code == 200
    assert (await login(pg_app, password=NEW_PASSWORD)).status_code == 200

    # Token yang sudah dipakai tidak bisa dipakai dua kali.
    r = await pg_app.client.post(
        "/api/auth/reset-password",
        json={
            "token": token,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert r.status_code == 400

"""Regression: lupa password + reset password via OTP 6 digit.

Butuh PostgreSQL nyata (TEST_DATABASE_URL). Mode dev tanpa RESEND_API_KEY
membuat endpoint mengembalikan devCode sehingga OTP bisa dipakai di test.
"""
import pytest
from sqlalchemy import select

from src.models import RefreshToken, User, VerificationToken
from src.users.service import UserService

pytestmark = pytest.mark.asyncio

PASSWORD = "OnlyForRegression123!"
NEW_PASSWORD = "BrandNewPassword456!"
EMAIL = "fan@example.org"


async def make_user(pg_app, name="VerseFan", email=EMAIL):
    async with pg_app.sessions() as session:
        user = await UserService(session).create_user(name, email, PASSWORD)
        user.is_email_verified = True
        await session.commit()
        return user.user_id


async def request_otp(pg_app, email=EMAIL):
    return await pg_app.client.post(
        "/api/auth/forgot-password-otp", json={"email": email}
    )


async def login(pg_app, username="VerseFan", password=PASSWORD):
    return await pg_app.client.post(
        "/api/auth/signin",
        data={"username": username, "password": password, "access_code": ""},
    )


async def test_forgot_password_returns_dev_code_without_leaking_existence(pg_app):
    await make_user(pg_app)

    res = await request_otp(pg_app)
    assert res.status_code == 200
    body = res.json()
    assert body.get("devCode") and len(body["devCode"]) == 6

    # Email tidak terdaftar → respons identik & netral, tanpa devCode
    res = await request_otp(pg_app, "ghost@example.org")
    assert res.status_code == 200
    ghost = res.json()
    assert ghost.get("devCode") is None
    assert ghost["message"] == body["message"]


async def test_full_reset_flow_revokes_sessions_and_allows_new_password(pg_app):
    user_id = await make_user(pg_app)

    # Punya sesi aktif sebelum reset
    assert (await login(pg_app)).status_code == 200

    code = (await request_otp(pg_app)).json()["devCode"]
    res = await pg_app.client.post(
        "/api/auth/reset-password-otp",
        json={
            "email": EMAIL,
            "code": code,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Semua refresh token dicabut
    async with pg_app.sessions() as session:
        tokens = (
            (
                await session.execute(
                    select(RefreshToken).where(RefreshToken.user_id == user_id)
                )
            )
            .scalars()
            .all()
        )
    assert tokens == []

    # Password lama mati, password baru hidup
    assert (await login(pg_app, password=PASSWORD)).status_code == 401
    assert (await login(pg_app, password=NEW_PASSWORD)).status_code == 200


async def test_otp_is_single_use_and_wrong_code_rejected(pg_app):
    await make_user(pg_app)
    code = (await request_otp(pg_app)).json()["devCode"]

    wrong = "000000" if code != "000000" else "111111"
    res = await pg_app.client.post(
        "/api/auth/reset-password-otp",
        json={
            "email": EMAIL,
            "code": wrong,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert res.status_code == 400

    # Kode benar → sukses sekali...
    ok = await pg_app.client.post(
        "/api/auth/reset-password-otp",
        json={
            "email": EMAIL,
            "code": code,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert ok.status_code == 200

    # ...dan hangus setelah dipakai
    again = await pg_app.client.post(
        "/api/auth/reset-password-otp",
        json={
            "email": EMAIL,
            "code": code,
            "new_password": "AnotherPass789!",
            "confirm_password": "AnotherPass789!",
        },
    )
    assert again.status_code == 400


async def test_verify_reset_otp_issues_single_use_reset_token(pg_app):
    await make_user(pg_app)
    code = (await request_otp(pg_app)).json()["devCode"]

    res = await pg_app.client.post(
        "/api/auth/verify-reset-otp", json={"email": EMAIL, "code": code}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is True
    reset_token = body["resetToken"]
    assert reset_token

    # OTP sudah dikonsumsi — verifikasi ulang gagal
    res = await pg_app.client.post(
        "/api/auth/verify-reset-otp", json={"email": EMAIL, "code": code}
    )
    assert res.status_code == 400

    # resetToken bisa dipakai di endpoint reset-password berbasis token
    res = await pg_app.client.post(
        "/api/auth/reset-password",
        json={
            "token": reset_token,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert res.status_code == 200
    assert (await login(pg_app, password=NEW_PASSWORD)).status_code == 200


async def test_password_policy_and_mismatch_rejected(pg_app):
    await make_user(pg_app)
    code = (await request_otp(pg_app)).json()["devCode"]

    # Konfirmasi tidak sama
    res = await pg_app.client.post(
        "/api/auth/reset-password-otp",
        json={
            "email": EMAIL,
            "code": code,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD + "x",
        },
    )
    assert res.status_code == 400

    # Terlalu pendek
    res = await pg_app.client.post(
        "/api/auth/reset-password-otp",
        json={
            "email": EMAIL,
            "code": code,
            "new_password": "short",
            "confirm_password": "short",
        },
    )
    assert res.status_code == 400

    # OTP tidak boleh ikut hangus oleh permintaan yang gagal validasi
    ok = await pg_app.client.post(
        "/api/auth/reset-password-otp",
        json={
            "email": EMAIL,
            "code": code,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert ok.status_code == 200


async def test_reset_purges_leftover_link_tokens(pg_app):
    user_id = await make_user(pg_app)

    # Ada token reset berbasis link yang tersisa
    await pg_app.client.post("/api/auth/forgot-password", json={"email": EMAIL})

    code = (await request_otp(pg_app)).json()["devCode"]
    res = await pg_app.client.post(
        "/api/auth/reset-password-otp",
        json={
            "email": EMAIL,
            "code": code,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        },
    )
    assert res.status_code == 200

    async with pg_app.sessions() as session:
        leftovers = (
            (
                await session.execute(
                    select(VerificationToken).where(
                        VerificationToken.user_id == user_id,
                        VerificationToken.token_type.in_(
                            ["password_reset", "reset_otp"]
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
    assert leftovers == []

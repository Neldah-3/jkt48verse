"""Pastikan identitas JKT48Verse konsisten di seluruh email notifikasi."""

from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

from src.auth.email_service import EmailService
from src.config import Settings


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method, kwargs, subject",
    [
        (
            "send_email_verification",
            {"token": "test-token", "username": "Fans"},
            "Verify Your Email - JKT48Verse",
        ),
        (
            "send_password_reset",
            {"token": "test-token", "username": "Fans"},
            "Reset Your Password - JKT48Verse",
        ),
        (
            "send_account_locked_notification",
            {"username": "Fans", "lockout_duration": 15},
            "Account Locked - JKT48Verse",
        ),
        (
            "send_feedback_status_update",
            {
                "name": "Fans",
                "new_status": "implemented",
                "admin_notes": "Sudah diperbarui.",
                "feedback_message": "Mohon perbarui identitas aplikasi.",
            },
            "Update Status Masukan: Telah Diimplementasikan - JKT48Verse",
        ),
    ],
)
async def test_notification_email_branding(monkeypatch, method, kwargs, subject):
    service = EmailService(Settings())
    send_email = AsyncMock()
    monkeypatch.setattr(service, "_send_email", send_email)

    await getattr(service, method)(email="fans@example.com", **kwargs)

    send_email.assert_awaited_once()
    payload = send_email.await_args.args[0]
    assert payload["to"] == "fans@example.com"
    assert payload["subject"] == subject

    document = BeautifulSoup(payload["html"], "html.parser")
    assert document.h1.get_text() == "JKT48Verse"
    assert any(p.get_text() == "JKT48Verse" for p in document.find_all("p"))
    assert "mypage" not in document.get_text().lower()

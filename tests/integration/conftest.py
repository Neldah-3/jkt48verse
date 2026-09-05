"""Real PostgreSQL tests, opt-in via TEST_DATABASE_URL (never DATABASE_URL).

The named database must end with _test and already have `alembic upgrade head`.
Its application tables are truncated between tests; do not use production data.
"""
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth import staff_credentials as sc
from src.auth.email_service import EmailService
from src.config import config
from src.database import database_instance
from src.limiter import limiter
from src.main import app
from src.models import Base
from src.redis_client import redis_instance


@pytest_asyncio.fixture
async def pg_app(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests")
    parsed = make_url(url).set(drivername="postgresql+asyncpg")
    if not (parsed.database or "").endswith("_test"):
        pytest.fail(
            "Refusing to truncate a database whose name does not end with _test"
        )
    engine = create_async_engine(parsed, pool_size=5, max_overflow=15)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    tables = ", ".join(f'"{name}"' for name in Base.metadata.tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))
    monkeypatch.setattr(database_instance, "engine", engine)
    monkeypatch.setattr(database_instance, "session_factory", sessions)
    monkeypatch.setattr(config, "ENV", "dev")
    monkeypatch.setattr(config, "RESEND_API_KEY", SecretStr(""))
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(EmailService, "send_account_locked_notification", AsyncMock())
    for role, count in sc.ROLE_SLOTS:
        for i in range(1, count + 1):
            for key in sc.REQUIRED_FIELDS:
                monkeypatch.setenv(f"{sc.ROLE_PREFIX[role]}_{i}_{key}", "")
    sc.reload()
    monkeypatch.setattr(redis_instance, "_memory", True)
    await redis_instance.connect()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app),
            base_url="http://testserver",
            headers={"user-agent": "regression-tests"},
        ) as client:
            yield SimpleNamespace(client=client, sessions=sessions)
    finally:
        sc._REGISTRY = None
        await redis_instance.close()
        await engine.dispose()

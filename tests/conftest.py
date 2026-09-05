"""Konfigurasi environment untuk test (sebelum import aplikasi)."""

import os

os.environ.setdefault("ENV", "dev")
os.environ.setdefault("SECRET_KEY", "dummy_secret_key_for_testing_12345")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/mypage48_test"
)
os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("ORIGINS", "http://localhost:3000")

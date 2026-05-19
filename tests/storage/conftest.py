"""Fixtures для integration-тестов storage."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


def pytest_configure(config) -> None:
    """Загрузить Supabase credentials из secrets.toml до первого теста."""
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"):
        return
    secrets_file = ROOT / ".streamlit" / "secrets.toml"
    if not secrets_file.exists():
        return
    with open(secrets_file, "rb") as f:
        secrets = tomllib.load(f)
    os.environ.setdefault("SUPABASE_URL", secrets.get("SUPABASE_URL", ""))
    os.environ.setdefault("SUPABASE_KEY", secrets.get("SUPABASE_KEY", ""))


@pytest.fixture(scope="session")
def supabase_client():
    from src.storage.supabase_client import _get_client
    _get_client.cache_clear()
    return _get_client()


@pytest.fixture(autouse=True)
def use_test_tables(monkeypatch):
    """Перенаправить все функции на тестовые таблицы."""
    import src.storage.supabase_client as sc
    monkeypatch.setattr(sc, "_KPS_TABLE", "kps_test")
    monkeypatch.setattr(sc, "_CONTRACTS_TABLE", "contracts_test")


@pytest.fixture(autouse=True)
def truncate_tables(supabase_client):
    """TRUNCATE тестовых таблиц перед каждым тестом."""
    supabase_client.table("kps_test").delete().gte("created_at", "1900-01-01").execute()
    supabase_client.table("contracts_test").delete().gte("created_at", "1900-01-01").execute()
    yield

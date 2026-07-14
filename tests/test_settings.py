"""Тесты core/settings.py — env-only чтение секретов (P0-06)."""
from __future__ import annotations

import pytest

from core.settings import get_secret


def test_get_secret_returns_env_value(monkeypatch):
    monkeypatch.setenv("P006_TEST_SECRET", "value-123")
    assert get_secret("P006_TEST_SECRET") == "value-123"


def test_get_secret_missing_raises_with_key_name(monkeypatch):
    monkeypatch.delenv("P006_TEST_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="P006_TEST_SECRET"):
        get_secret("P006_TEST_SECRET")

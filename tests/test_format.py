"""Тесты для src/utils/format.py."""
from __future__ import annotations

from src.utils.format import format_phone


def test_format_phone_canonical() -> None:
    assert format_phone("+7 903 651-85-77") == "+7 (903) 651-85-77"


def test_format_phone_empty_returns_empty() -> None:
    assert format_phone("") == ""


def test_format_phone_unrecognized_returns_raw() -> None:
    assert format_phone("8-800-555-35-35") == "8-800-555-35-35"


def test_format_phone_with_dashes_only() -> None:
    assert format_phone("+7-903-651-85-77") == "+7 (903) 651-85-77"

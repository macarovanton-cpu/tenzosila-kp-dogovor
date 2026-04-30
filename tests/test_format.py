"""Тесты для src/utils/format.py."""
from __future__ import annotations

from src.utils.format import fmt_int_spaces, fmt_rub, format_phone, pluralize


def test_format_phone_canonical() -> None:
    assert format_phone("+7 903 651-85-77") == "+7 (903) 651-85-77"


def test_format_phone_empty_returns_empty() -> None:
    assert format_phone("") == ""


def test_format_phone_unrecognized_returns_raw() -> None:
    assert format_phone("8-800-555-35-35") == "8-800-555-35-35"


def test_format_phone_with_dashes_only() -> None:
    assert format_phone("+7-903-651-85-77") == "+7 (903) 651-85-77"


# --- fmt_rub ---


def test_fmt_rub_zero() -> None:
    assert fmt_rub(0) == "0 ₽"


def test_fmt_rub_thousands() -> None:
    assert fmt_rub(1000) == "1 000 ₽"


def test_fmt_rub_millions() -> None:
    assert fmt_rub(1_234_567) == "1 234 567 ₽"


def test_fmt_rub_float_truncates() -> None:
    assert fmt_rub(1716619.9) == "1 716 619 ₽"


# --- fmt_int_spaces ---


def test_fmt_int_spaces_zero() -> None:
    assert fmt_int_spaces(0) == "0"


def test_fmt_int_spaces_hundreds() -> None:
    assert fmt_int_spaces(999) == "999"


def test_fmt_int_spaces_thousands() -> None:
    assert fmt_int_spaces(1000) == "1 000"


def test_fmt_int_spaces_millions() -> None:
    assert fmt_int_spaces(1_234_567) == "1 234 567"


# --- pluralize ---


def test_pluralize_one() -> None:
    assert pluralize(1, ("день", "дня", "дней")) == "1 день"


def test_pluralize_two() -> None:
    assert pluralize(2, ("день", "дня", "дней")) == "2 дня"


def test_pluralize_five() -> None:
    assert pluralize(5, ("день", "дня", "дней")) == "5 дней"


def test_pluralize_eleven() -> None:
    """11 — исключение, форма «дней» а не «один день»."""
    assert pluralize(11, ("день", "дня", "дней")) == "11 дней"


def test_pluralize_twenty_one() -> None:
    assert pluralize(21, ("день", "дня", "дней")) == "21 день"


def test_pluralize_zero() -> None:
    assert pluralize(0, ("день", "дня", "дней")) == "0 дней"

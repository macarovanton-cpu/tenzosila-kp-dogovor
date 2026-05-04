"""Тесты для страницы генерации договора."""
from __future__ import annotations

from datetime import date

from src.contracts.utils import format_date_parts
from src.utils.format import sanitize_filename


def test_filename_sanitization():
    """Запрещённые символы заменяются на _, пробелы остаются."""
    dirty = 'ООО "Рога/Копыта" <test>: *файл*'
    clean = sanitize_filename(dirty)
    assert '"' not in clean
    assert '/' not in clean
    assert '<' not in clean
    assert '>' not in clean
    assert ':' not in clean
    assert '*' not in clean
    assert ' ' in clean
    assert 'ООО' in clean
    assert 'Рога' in clean


def test_format_date_integration():
    """format_date_parts корректно разбирает date(2026, 5, 4)."""
    d = date(2026, 5, 4)
    result = format_date_parts(str(d))
    assert result["ДОГОВОР_ДЕНЬ"] == "4"
    assert result["ДОГОВОР_МЕСЯЦ"] == "мая"
    assert result["ДОГОВОР_ГОД"] == "2026"
    assert result["ДОГОВОР_ДАТА_ПОЛНАЯ"] == "04.05.2026"

"""Тесты для страницы генерации договора."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

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


# ---------------------------------------------------------------------------
# Тесты сохранения generated в session_state
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_session_state():
    """Мокаем st.session_state как обычный dict для тестов страницы."""
    state: dict = {}
    with patch("src.contracts.state.st") as mock_st:
        mock_st.session_state = state
        yield state


class TestGeneratedStatePage:
    def test_generated_contains_both_files(self, mock_session_state):
        """После генерации cs['generated'] содержит байты обоих документов."""
        from src.contracts.state import init_contract_state
        init_contract_state()
        cs = mock_session_state["contract"]
        cs["generated"] = {
            "contract_bytes": b"contract_content",
            "contract_filename": "Договор_1_ООО.docx",
            "spec_bytes": b"spec_content",
            "spec_filename": "Спецификация_1_ООО.docx",
        }
        gen = cs["generated"]
        assert gen["contract_bytes"] == b"contract_content"
        assert gen["spec_bytes"] == b"spec_content"
        assert gen["contract_filename"] == "Договор_1_ООО.docx"
        assert gen["spec_filename"] == "Спецификация_1_ООО.docx"

    def test_rerun_does_not_lose_bytes(self, mock_session_state):
        """Повторный rerun (init_contract_state) не затирает generated."""
        from src.contracts.state import init_contract_state
        init_contract_state()
        cs = mock_session_state["contract"]
        cs["generated"] = {
            "contract_bytes": b"contract_data",
            "contract_filename": "Договор.docx",
            "spec_bytes": b"spec_data",
            "spec_filename": "Спецификация.docx",
        }
        init_contract_state()  # симуляция rerun
        assert cs["generated"] is not None
        assert cs["generated"]["contract_bytes"] == b"contract_data"
        assert cs["generated"]["spec_bytes"] == b"spec_data"

    def test_clear_generated_resets_to_none(self, mock_session_state):
        """Кнопка 'Сгенерировать заново' очищает generated через clear_generated()."""
        from src.contracts.state import clear_generated, init_contract_state
        init_contract_state()
        mock_session_state["contract"]["generated"] = {
            "contract_bytes": b"x",
            "contract_filename": "a.docx",
            "spec_bytes": b"y",
            "spec_filename": "b.docx",
        }
        clear_generated()
        assert mock_session_state["contract"]["generated"] is None

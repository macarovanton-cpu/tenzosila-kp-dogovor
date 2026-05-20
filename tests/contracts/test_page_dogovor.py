"""Тесты вспомогательной логики страницы договора."""
from __future__ import annotations

from unittest.mock import patch


@patch("src.contracts.state.st")
def test_mode_a_set_specification_makes_form_ready(mock_st):
    """После set_specification is_extracted() возвращает True."""
    state = {}
    mock_st.session_state = state
    from src.contracts.state import init_contract_state, set_specification, is_extracted
    init_contract_state()
    assert not is_extracted()
    set_specification({"СПЕЦ_НДС": "22", "СПЕЦ_ИТОГО": "500000"})
    assert is_extracted()


@patch("src.contracts.state.st")
def test_mode_b_set_extracted_data_makes_form_ready(mock_st):
    """Режим B: set_extracted_data (ai_raw) тоже делает is_extracted True."""
    state = {}
    mock_st.session_state = state
    from src.contracts.state import init_contract_state, set_extracted_data, is_extracted
    init_contract_state()
    set_extracted_data({"requisites": {"ЗАКАЗЧИК_ИНН": "123"}, "specification": {}})
    assert is_extracted()


def test_extract_from_files_legacy_alias_still_importable():
    """Импорт extract_from_files из extractor работает (для pages/2_Договор.py)."""
    from src.contracts.extractor import extract_from_files, extract_kp_data_legacy
    assert extract_from_files is extract_kp_data_legacy


def test_extract_card_data_importable():
    """extract_card_data доступна для импорта в страницу."""
    from src.contracts.extractor import extract_card_data
    assert callable(extract_card_data)


def test_build_specification_importable():
    """build_specification_from_kp_snapshot доступна для импорта."""
    from src.contracts.from_kp import build_specification_from_kp_snapshot
    assert callable(build_specification_from_kp_snapshot)

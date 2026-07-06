"""Тесты вспомогательной логики страницы договора."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
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


class _FakeColumn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


# Универсальный контекстный менеджер для expander, container и т.п.
class _FakeContextManager:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeStreamlitModule:
    session_state: dict = {}

    def set_page_config(self, *args, **kwargs):
        pass

    def title(self, *args, **kwargs):
        pass

    def radio(self, *args, **kwargs):
        return "Из PDF файла (старый КП)"

    def divider(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def success(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def caption(self, *args, **kwargs):
        pass

    def subheader(self, *args, **kwargs):
        pass

    def expander(self, *args, **kwargs):
        return _FakeContextManager()

    def columns(self, spec, *args, **kwargs):
        count = spec if isinstance(spec, int) else len(spec)
        return [_FakeColumn() for _ in range(count)]

    def file_uploader(self, *args, **kwargs):
        return None

    def button(self, *args, **kwargs):
        return False

    def text_input(self, *args, **kwargs):
        return ""

    def text_area(self, *args, **kwargs):
        return ""

    def selectbox(self, *args, **kwargs):
        options = kwargs.get("options", args[1] if len(args) > 1 else [])
        return options[0] if options else None

    def date_input(self, *args, **kwargs):
        return None

    def cache_data(self, *args, **kwargs):
        # @st.cache_data и @st.cache_data(...) → декоратор-проходка (без кэша).
        if args and callable(args[0]):
            return args[0]
        return lambda func: func


def _load_dogovor_page(monkeypatch):
    fake_st = _FakeStreamlitModule()
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    import src.contracts.state as state_module

    monkeypatch.setattr(state_module, "st", fake_st)
    page_path = Path(__file__).parents[2] / "src" / "pages" / "2_Договор.py"
    spec = importlib.util.spec_from_file_location("dogovor_page_for_test", page_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_items_to_rows_uses_russian_bucket_labels(monkeypatch):
    page = _load_dogovor_page(monkeypatch)

    rows = page._items_to_rows(
        [
            {"name": "Весы", "payment_group": "scales", "total": 1},
            {"name": "Фундамент", "payment_group": "foundation", "total": 1},
            {
                "name": "Монтаж и поверка",
                "payment_group": "installation_and_verification",
                "total": 1,
            },
        ]
    )

    assert [row["Бакет"] for row in rows] == [
        "Оборудование",
        "Фундамент",
        "Монтаж и поверка",
    ]


def test_rows_to_items_maps_russian_bucket_labels_to_payment_groups(monkeypatch):
    page = _load_dogovor_page(monkeypatch)

    rows = [
        {"Наименование": "Весы", "Бакет": "Оборудование"},
        {"Наименование": "Фундамент", "Бакет": "Фундамент"},
        {"Наименование": "Монтаж", "Бакет": "Монтаж и поверка"},
        {"Наименование": "Доставка до объекта", "Бакет": "Оборудование"},
    ]
    items = page._rows_to_items(rows, [])

    assert [item["payment_group"] for item in items] == [
        "scales",
        "foundation",
        "installation_and_verification",
        "delivery",
    ]

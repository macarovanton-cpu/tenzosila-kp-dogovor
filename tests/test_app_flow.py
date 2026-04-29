"""Сценарные тесты на базе streamlit.testing.v1.AppTest.

Проверяют что приложение запускается и основные бизнес-сценарии отрабатывают.
Если какой-то widget не виден через AppTest API — сценарий фолбэчит на
прямое чтение session_state + вызов бизнес-функций.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "src" / "app.py")


def _fresh_app() -> AppTest:
    return AppTest.from_file(APP_PATH, default_timeout=30).run()


def test_app_starts_without_exception():
    at = _fresh_app()
    assert not at.exception, f"App raised: {at.exception}"


def test_default_state_has_manager_id():
    at = _fresh_app()
    assert at.session_state["manager_id"] == "makarov_av"


def test_header_has_no_removed_client_fields():
    at = _fresh_app()
    # Убеждаемся, что в state нет client_contact/email/phone/manager_name/deck_mm
    for k in ("client_contact", "client_email", "client_phone", "manager_name", "deck_mm", "client_inn"):
        try:
            _ = at.session_state[k]
            raise AssertionError(f"Ключ {k} должен быть удалён, но присутствует")
        except KeyError:
            pass


def test_cascade_change_resets_overrides():
    """При смене модели spec_items_overrides сбрасываются."""
    at = _fresh_app()
    cur_model_id = at.session_state["model_id"]
    at.session_state["spec_items_overrides"] = {cur_model_id: {"price": 999_999}}
    # Смена max — через селектор (если доступно) или напрямую
    try:
        at.selectbox(key="model_max").select(80).run()
    except Exception:
        # Fallback: прямая симуляция колбэка
        from src.state import on_cascade_change
        at.session_state["model_max"] = 80
        on_cascade_change()
    assert at.session_state["spec_items_overrides"] == {}


def test_construction_fields_populated_after_first_render():
    """После запуска construction_* заполнены defaults для С-60-18."""
    at = _fresh_app()
    assert at.session_state["construction_beam"]
    assert int(at.session_state["construction_beam_count"]) > 0
    # С — сплошная → центральная балка непустая
    assert at.session_state["construction_center_beam"]
    assert at.session_state["construction_deck_mm"] in (6, 8, 10)
    assert at.session_state["construction_underlining_mm"] in (3, 4, 5)


def test_construction_description_for_rail_line():
    """Для Ф (колейная) — описание без центральной балки."""
    from src.data_loader import load_models, get_line_defaults, get_model_by_id
    from src.filters import model_id_from_cascade
    from src.spec_builder import build_construction_description
    from src.ui.construction_section import reset_construction

    models = load_models()
    model_id = model_id_from_cascade("Ф", 60, 18)
    model = get_model_by_id(models, model_id)
    ld = get_line_defaults(models, "Ф")
    state: dict = {}
    reset_construction(state, model, ld)

    text = build_construction_description(state)
    assert "колейная" in text
    assert "Швеллер" not in text


def test_model_price_slider_step_is_10000_for_large_price():
    """Для модели с retail > 1M шаг слайдера = 10_000."""
    from src.data_loader import load_prices
    from src.pricing import get_model_slider_params

    prices = load_prices()
    # vesta-с-60-18 обычно > 1M
    price = prices["models"]["vesta-с-60-18"]
    params = get_model_slider_params(price)
    assert params.step == 10_000
    assert params.min_v % 1000 == 0
    assert params.max_v % 1000 == 0


def test_empty_kp_number_blocks_generate_button():
    """Пустой kp_number → validate возвращает ошибку."""
    from src.data_loader import load_managers, load_models, load_payment_terms, load_prices
    from src.validation import validate

    state = {
        "kp_number": "",
        "manager_id": "makarov_av",
        "client_name": "Тест",
        "model_id": "vesta-с-60-18",
        "model_price": 1_906_000,
        "options": {},
        "payment_preset_id": "v1_prepay_postpay",
        "payment_percents": {},
        "payment_split_state": {},
        "payment_custom_text": "",
        "payment_v1_prepay": 50,
        "payment_days": 5,
    }
    errors, _ = validate(
        state, load_prices(), load_models(), load_payment_terms(), load_managers()
    )
    assert any("КП" in e for e in errors)


def test_app_has_specification_section_in_main():
    """Секция «📊 Спецификация» отрендерена в main area как subheader."""
    at = _fresh_app()
    assert not at.exception
    titles = [h.value for h in at.subheader]
    assert any("Спецификация" in t for t in titles), (
        f"Ожидался subheader со словом 'Спецификация', есть: {titles}"
    )


@pytest.mark.skipif(True, reason="AppTest не поддерживает data_editor в текущей версии Streamlit")
def test_data_editor_price_edit_updates_overrides():
    """Скип до поддержки data_editor в AppTest — проверено юнит-тестами."""
    pass

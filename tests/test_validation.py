"""Тесты validate()."""
from __future__ import annotations

from datetime import date

from src.validation import validate


def _valid_state() -> dict:
    """Полностью валидный state — все проверки должны проходить."""
    return {
        "lead_number": "12345",
        "manager_id": "makarov_av",
        "client_name": "ООО «Тест»",
        "kp_date": date.today(),
        "kp_valid_days": 15,
        "total_term_days": 35,
        "model_id": "vesta-с-60-18",
        "model_line": "С",
        "model_max": 60,
        "model_length": 18,
        "model_price": 1906544,
        "options": {},
        "payment_preset_id": "prepay_50_postpay_50",
        "payment_percents": {"p1": 50, "p2": 50},
        "payment_days": 5,
        "payment_custom_text": "",
        "payment_split_state": {},
    }


def test_empty_lead_blocks(prices, models_json, payment_terms, managers):
    state = _valid_state()
    state["lead_number"] = "   "
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("лида" in e for e in errors)


def test_empty_manager_id_blocks(prices, models_json, payment_terms, managers):
    state = _valid_state()
    state["manager_id"] = ""
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("енеджер" in e for e in errors)


def test_unknown_manager_id_blocks(prices, models_json, payment_terms, managers):
    state = _valid_state()
    state["manager_id"] = "nonexistent_id"
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("енеджер" in e for e in errors)


def test_model_40t_not_in_prices(prices, models_json, payment_terms, managers):
    state = _valid_state()
    state["model_id"] = "vesta-с-40-18"
    state["model_line"] = "С"
    state["model_max"] = 40
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("отсутствует в прайсе" in e for e in errors)


def test_percents_not_100_on_prepay_50_postpay_50(prices, models_json, payment_terms, managers):
    state = _valid_state()
    state["payment_percents"] = {"p1": 50, "p2": 40}
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("не равна 100" in e for e in errors)


def test_valid_state_returns_empty_errors(prices, models_json, payment_terms, managers):
    state = _valid_state()
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert errors == []


def test_on_request_option_blocks(prices, models_json, payment_terms, managers):
    state = _valid_state()
    state["model_length"] = 24
    state["model_id"] = "vesta-с-60-24"  # такой модели нет в prices → ожидаем ещё одну ошибку
    state["model_line"] = "С"
    state["options"] = {
        "canopy_turnkey_24": {
            "enabled": True,
            "is_on_request": True,
            "price": 0,
            "qty": 1,
        }
    }
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("под запрос" in e for e in errors)


def test_data_incomplete_emits_warning(prices, models_json, payment_terms, managers):
    """П-80-18 помечена data_incomplete — должен быть warning."""
    state = _valid_state()
    state["model_id"] = "vesta-п-80-18"
    state["model_line"] = "П"
    state["model_max"] = 80
    state["model_length"] = 18
    # цена из prices для П-80-18
    price = prices["models"]["vesta-п-80-18"]
    state["model_price"] = price["retail"]
    _, warnings = validate(state, prices, models_json, payment_terms, managers)
    assert any("неполные" in w for w in warnings)

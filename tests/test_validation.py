"""Тесты validate()."""
from __future__ import annotations

from datetime import date

from src.validation import validate


def _valid_state() -> dict:
    """Полностью валидный state — все проверки должны проходить."""
    return {
        "kp_number": "12345",
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
        "payment_preset_id": "v1_prepay_postpay",
        "payment_percents": {},
        "payment_days": 5,
        "payment_custom_text": "",
        "payment_split_state": {},
        "payment_v1_prepay": 50,
        "payment_v2_prepay": 30,
        "payment_v2_preship": 40,
        "payment_v3_days": 15,
        "payment_v3_trigger_id": "after_installation",
    }


def test_empty_kp_number_blocks(prices, models_json, payment_terms, managers):
    state = _valid_state()
    state["kp_number"] = "   "
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("КП" in e for e in errors)


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


def test_v1_invalid_prepay_zero(prices, models_json, payment_terms, managers):
    state = _valid_state()
    state["payment_preset_id"] = "v1_prepay_postpay"
    state["payment_v1_prepay"] = 0
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("Предоплата" in e and "1–99" in e for e in errors)


def test_v1_invalid_prepay_100(prices, models_json, payment_terms, managers):
    """V1 не допускает 100% — это уже prepay_100 пресет."""
    state = _valid_state()
    state["payment_preset_id"] = "v1_prepay_postpay"
    state["payment_v1_prepay"] = 100
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("Предоплата" in e and "1–99" in e for e in errors)


def test_v2_invalid_sum_over_99(prices, models_json, payment_terms, managers):
    """V2: prepay+preship>99 → нечего постоплачивать."""
    state = _valid_state()
    state["payment_preset_id"] = "v2_prepay_preship_postpay"
    state["payment_v2_prepay"] = 50
    state["payment_v2_preship"] = 50
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("99" in e and "превышать" in e.lower() for e in errors)


def test_v3_invalid_days_zero(prices, models_json, payment_terms, managers):
    state = _valid_state()
    state["payment_preset_id"] = "v3_postpay_only"
    state["payment_v3_days"] = 0
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("V3" in e or "постоплат" in e.lower() for e in errors)


def test_split_percents_not_100(prices, models_json, payment_terms, managers):
    """split_by_items: prepay+postpay в любой группе должны давать 100."""
    state = _valid_state()
    state["payment_preset_id"] = "split_by_items"
    state["payment_split_state"] = {
        "scales": {"prepay": 50, "postpay": 40},
    }
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


def test_split_foundation_group_active_for_all_foundation_base_variants(
    prices, models_json, payment_terms, managers
):
    """split_by_items валидирует группу foundation для всех 6 вариантов блока."""
    foundation_keys = [
        "foundation_s_f_18",
        "foundation_supervision",
        "construction_works_18",
        "concrete_base_on_frame",
        "road_slabs_18",
        "pag_slabs_18",
    ]

    for key in foundation_keys:
        state = _valid_state()
        state["payment_preset_id"] = "split_by_items"
        state["payment_split_state"] = {
            "foundation": {"prepay": 40, "postpay": 40},
        }
        state["options"] = {
            key: {
                "enabled": True,
                "price": 100_000,
                "qty": 1,
                "customer_side": False,
                "is_on_request": False,
            }
        }

        errors, _ = validate(state, prices, models_json, payment_terms, managers)

        assert any("не равна 100" in e for e in errors), key

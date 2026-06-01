"""Тесты build_kp_snapshot — без сети, без Supabase."""
from __future__ import annotations

from datetime import date

from src.storage.snapshot_builder import build_kp_snapshot


def _base_state() -> dict:
    return {
        "kp_number": "КП-2026-001",
        "kp_date": date(2026, 5, 20),
        "kp_valid_days": 15,
        "warranty_months": 36,
        "client_name": "ООО Ромашка",
        "manager_id": "ivanov",
        "model_line": "С",
        "model_max": 60,
        "model_length": 18,
        "model_id": "vesta-с-60-18",
        "model_price": None,
        "sensor_id": "zemic_dhm9b_30t",
        "indicator_id": "titan_3cs",
        "cable_m": 20,
        "is_dual_range": False,
        "construction_beam": "Двутавр 20Б1",
        "construction_beam_count": 4,
        "construction_center_beam": "",
        "construction_center_beam_count": 0,
        "construction_deck_mm": 6,
        "construction_underlining_mm": 4,
        "options": {},
        "spec_items_overrides": {},
        "payment_preset_id": "split_by_items",
        "payment_days": 5,
        "payment_custom_text": "",
        "payment_split_state": {"scales": {"prepay": 50, "postpay": 50}},
        "payment_v1_prepay": 50,
        "payment_v2_prepay": 30,
        "payment_v2_preship": 40,
        "payment_v3_days": 15,
        "payment_v3_trigger_id": "after_installation",
    }


def test_builds_full_snapshot_from_minimal_state():
    snap = build_kp_snapshot(_base_state())

    assert snap["metadata"]["kp_valid_days"] == 15
    assert snap["metadata"]["warranty_months"] == 36

    assert snap["model"]["line"] == "С"
    assert snap["model"]["max"] == 60
    assert snap["model"]["length"] == 18
    assert snap["model"]["width"] == 3.0
    assert snap["model"]["price"] is None

    assert snap["equipment"]["sensor_id"] == "zemic_dhm9b_30t"
    assert snap["equipment"]["indicator_id"] == "titan_3cs"
    assert snap["equipment"]["cable_m"] == 20

    assert snap["construction"]["beam"] == "Двутавр 20Б1"
    assert snap["construction"]["beam_count"] == 4
    assert snap["construction"]["deck_mm"] == 6

    assert snap["metrology"]["is_dual_range"] is False

    assert snap["options"] == {}
    assert snap["spec_overrides"] == {}

    assert snap["payment"]["preset_id"] == "split_by_items"
    assert snap["payment"]["days"] == 5
    assert snap["payment"]["v1_prepay"] == 50
    assert snap["payment"]["v3_trigger_id"] == "after_installation"


def test_excludes_widget_keys():
    state = _base_state()
    # Виджетные ключи Streamlit — НЕ должны попасть в снапшот
    state["opt_frame_std_с_enabled__vesta-с-60-18"] = True
    state["opt_frame_std_с_price__vesta-с-60-18"] = 85000
    state["split_scales_prepay"] = 50
    snap = build_kp_snapshot(state)
    flat = str(snap)
    assert "opt_" not in flat
    assert "split_scales" not in flat


def test_model_width_defaults_to_standard_when_missing():
    """Старый state без platform_width_m сохраняется как стандартные 3.0 м."""
    state = _base_state()
    state.pop("platform_width_m", None)

    snap = build_kp_snapshot(state)

    assert snap["model"]["width"] == 3.0


def test_model_width_preserves_nonstandard_value():
    """Нестандартная ширина попадает в snapshot модели."""
    state = _base_state()
    state["platform_width_m"] = 3.5

    snap = build_kp_snapshot(state)

    assert snap["model"]["width"] == 3.5


def test_excludes_computed_values():
    state = _base_state()
    # Вычисляемые ключи — не должны попасть в снапшот
    state["spec_items"] = [{"label": "Базовый блок", "price": 2450000}]
    state["total_term_days_user_set"] = True
    state["payment_percents"] = {"p1": 50}
    snap = build_kp_snapshot(state)
    assert "spec_items" not in snap
    assert "total_term_days_user_set" not in snap
    assert "payment_percents" not in snap


def test_handles_missing_optional_keys():
    # Минимальный state без options/overrides/payment_custom_text
    state = {
        "kp_valid_days": 15,
        "warranty_months": 24,
        "model_line": "Ф",
        "model_max": 30,
        "model_length": 12,
        "model_price": None,
        "sensor_id": "s1",
        "indicator_id": "i1",
        "cable_m": 10,
        "is_dual_range": False,
        "construction_beam": "20Б1",
        "construction_beam_count": 2,
        "construction_center_beam": "",
        "construction_center_beam_count": 0,
        "construction_deck_mm": 5,
        "construction_underlining_mm": 3,
        "payment_preset_id": "prepay_100",
        "payment_days": 3,
    }
    snap = build_kp_snapshot(state)
    assert snap["options"] == {}
    assert snap["spec_overrides"] == {}
    assert snap["payment"]["custom_text"] == ""
    assert snap["payment"]["split_state"] == {}


def test_options_preserve_retail_and_dealer_flag():
    state = _base_state()
    state["options"] = {
        "frame_std_с": {
            "enabled": True,
            "price": 85000,
            "qty": 2,
            "customer_side": False,
            "is_on_request": False,
            "retail": 90000,
            "dealer_is_synthetic": True,
            "block": "ramps",
        },
        "lighting": {
            "enabled": False,  # отключена — не должна попасть
            "price": 15000,
            "qty": 1,
            "customer_side": False,
            "is_on_request": False,
            "retail": 15000,
            "dealer_is_synthetic": False,
            "block": "extras",
        },
    }
    snap = build_kp_snapshot(state)
    # Только enabled опции
    assert "frame_std_с" in snap["options"]
    assert "lighting" not in snap["options"]
    # Проверяем поля снапшота
    opt = snap["options"]["frame_std_с"]
    assert opt["price"] == 85000
    assert opt["qty"] == 2
    assert opt["customer_side"] is False
    assert opt["retail"] == 90000
    assert opt["dealer_is_synthetic"] is True
    # Служебные поля прайса не хранятся
    assert "is_on_request" not in opt
    assert "block" not in opt
    assert "enabled" not in opt


# --- Тесты полей контракта snapshot КП→Договор (HANDOFF.md §6) ---

def _state_with_option(option_key: str, line: str = "С", length: int = 18) -> dict:
    """Базовый state с одной включённой опцией."""
    state = _base_state()
    state["model_line"] = line
    state["model_length"] = length
    state["options"] = {
        option_key: {
            "enabled": True,
            "price": 500_000,
            "qty": 1,
            "customer_side": False,
            "is_on_request": False,
            "retail": 500_000,
            "dealer_is_synthetic": False,
            "block": "foundation_and_base",
        }
    }
    return state


def test_foundation_execution_priamok():
    """foundation_s_f_* без UI-выбора → дефолт 'пандусный'."""
    snap = build_kp_snapshot(_state_with_option("foundation_s_f_18"))
    assert snap["foundation_execution"] == "пандусный"


def test_foundation_execution_uses_manager_choice_for_foundation_option():
    """Вариант 1: тип фундамента берётся из UI-выбора менеджера."""
    state = _state_with_option("foundation_s_f_18")
    state["foundation_execution"] = "монолитная_плита"
    snap = build_kp_snapshot(state)
    assert snap["foundation_execution"] == "монолитная_плита"


def test_foundation_execution_uses_manager_choice_for_supervision():
    """Вариант 2: курирование тоже берёт тип из UI-выбора."""
    state = _state_with_option("foundation_supervision")
    state["foundation_execution"] = "приямок"
    snap = build_kp_snapshot(state)
    assert snap["foundation_execution"] == "приямок"


def test_foundation_execution_uses_manager_choice_for_customer_materials():
    """Вариант 3: стройработы с материалами Заказчика берут тип из UI-выбора."""
    state = _state_with_option("construction_works_18")
    state["foundation_execution"] = "пандусный"
    snap = build_kp_snapshot(state)
    assert snap["foundation_execution"] == "пандусный"


def test_foundation_execution_rama_concrete():
    """concrete_base_on_frame → foundation_execution = 'rama_concrete'."""
    snap = build_kp_snapshot(_state_with_option("concrete_base_on_frame"))
    assert snap["foundation_execution"] == "rama_concrete"


def test_foundation_execution_null_when_no_foundation():
    """Нет фундаментных опций → foundation_execution = None."""
    state = _base_state()
    state["options"] = {}
    snap = build_kp_snapshot(state)
    assert snap["foundation_execution"] is None


def test_foundation_execution_null_for_supervision():
    """foundation_supervision без UI-выбора → дефолт 'пандусный'."""
    snap = build_kp_snapshot(_state_with_option("foundation_supervision"))
    assert snap["foundation_execution"] == "пандусный"


def test_foundation_execution_rama_road_slabs():
    """road_slabs_* → foundation_execution = 'rama_road_slabs'."""
    snap = build_kp_snapshot(_state_with_option("road_slabs_18"))
    assert snap["foundation_execution"] == "rama_road_slabs"


def test_foundation_execution_rama_pag_slabs():
    """pag_slabs_* → foundation_execution = 'rama_pag_slabs'."""
    snap = build_kp_snapshot(_state_with_option("pag_slabs_18"))
    assert snap["foundation_execution"] == "rama_pag_slabs"


def test_foundation_sections_18m():
    """Длина 18м → foundation_sections = 3."""
    snap = build_kp_snapshot(_state_with_option("foundation_s_f_18", length=18))
    assert snap["foundation_sections"] == 3


def test_foundation_sections_20m():
    """Длина 20м → foundation_sections = 4."""
    snap = build_kp_snapshot(_state_with_option("foundation_s_f_20", length=20))
    assert snap["foundation_sections"] == 4


def test_foundation_sections_null_when_no_foundation():
    """Нет фундаментных опций → foundation_sections = None."""
    state = _base_state()
    state["options"] = {}
    snap = build_kp_snapshot(state)
    assert snap["foundation_sections"] is None


def test_foundation_sections_null_for_road_and_pag_slabs():
    """Дорожные плиты и ПАГ — одиночные задания, секции не применяются."""
    road = build_kp_snapshot(_state_with_option("road_slabs_18", length=18))
    pag = build_kp_snapshot(_state_with_option("pag_slabs_24", length=24))
    assert road["foundation_sections"] is None
    assert pag["foundation_sections"] is None


def test_model_code_format():
    """model_code = 'ВЕСТА-{line}-{max}-{length}'."""
    state = _base_state()
    state["model_line"] = "С"
    state["model_max"] = 60
    state["model_length"] = 18
    snap = build_kp_snapshot(state)
    assert snap["model_code"] == "ВЕСТА-С-60-18"

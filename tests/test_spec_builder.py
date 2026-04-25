"""Тесты build_spec_items (с overrides) и build_construction_description."""
from __future__ import annotations

from src.spec_builder import (
    build_construction_description,
    build_spec_items,
    resolve_payment_group,
    resolve_term_days,
)


def _base_state() -> dict:
    return {
        "model_id": "vesta-с-60-18",
        "model_line": "С",
        "model_max": 60,
        "model_length": 18,
        "model_price": 1_906_000,
        "options": {},
        "spec_items_overrides": {},
    }


def test_build_spec_items_adds_model_with_item_key(prices, models_json):
    state = _base_state()
    items = build_spec_items(state, prices, models_json)
    assert len(items) == 1
    assert items[0]["item_key"] == "vesta-с-60-18"
    assert items[0]["qty"] == 1
    assert items[0]["price"] == 1_906_000
    assert items[0]["total"] == 1_906_000
    assert items[0]["is_overridden"] is False


def test_build_spec_items_applies_price_override(prices, models_json):
    state = _base_state()
    state["spec_items_overrides"] = {"vesta-с-60-18": {"price": 1_800_000}}
    items = build_spec_items(state, prices, models_json)
    assert items[0]["price"] == 1_800_000
    assert items[0]["total"] == 1_800_000
    assert items[0]["is_overridden"] is True


def test_build_spec_items_applies_qty_override_on_option(prices, models_json):
    state = _base_state()
    state["options"] = {
        "foundation_s_f_18": {
            "enabled": True,
            "price": 500_000,
            "qty": 1,
            "customer_side": False,
            "is_on_request": False,
            "retail": 500_000,
            "dealer_is_synthetic": False,
            "block": "foundations",
        }
    }
    state["spec_items_overrides"] = {"foundation_s_f_18": {"qty": 3}}
    items = build_spec_items(state, prices, models_json)
    # Находим позицию опции
    opt_items = [i for i in items if i["item_key"] == "foundation_s_f_18"]
    assert len(opt_items) == 1
    assert opt_items[0]["qty"] == 3
    assert opt_items[0]["price"] == 500_000
    assert opt_items[0]["total"] == 1_500_000
    assert opt_items[0]["is_overridden"] is True


def test_qty_and_price_overrides_independent(prices, models_json):
    """Override только qty — price остаётся computed, и наоборот."""
    state = _base_state()
    state["spec_items_overrides"] = {"vesta-с-60-18": {"qty": 2}}
    items = build_spec_items(state, prices, models_json)
    assert items[0]["qty"] == 2
    assert items[0]["price"] == 1_906_000  # не трогали
    assert items[0]["total"] == 2 * 1_906_000


def test_both_qty_and_price_overrides_recompute_total(prices, models_json):
    """qty=2, price=1_500_000 → total=3_000_000 (правильный пересчёт)."""
    state = _base_state()
    state["spec_items_overrides"] = {
        "vesta-с-60-18": {"qty": 2, "price": 1_500_000}
    }
    items = build_spec_items(state, prices, models_json)
    assert items[0]["qty"] == 2
    assert items[0]["price"] == 1_500_000
    assert items[0]["total"] == 3_000_000
    assert items[0]["is_overridden"] is True


def test_override_for_unknown_key_ignored(prices, models_json):
    """Override на опцию которой нет в state → молча игнорируется."""
    state = _base_state()
    state["spec_items_overrides"] = {"nonexistent_option": {"qty": 5}}
    items = build_spec_items(state, prices, models_json)
    # Без падения, модель на месте
    assert len(items) == 1
    assert items[0]["item_key"] == "vesta-с-60-18"


def test_resolve_term_days_uses_manual_value():
    state = {"total_term_days": 42}
    items = [{"term_days": 30}, {"term_days": 45}]
    assert resolve_term_days(items, state) == 42


# --- payment_group ---


def test_payment_group_present_in_each_item(prices, models_json):
    """В каждом item должно быть поле payment_group (для render_payment_block)."""
    state = _base_state()
    state["options"] = {
        "foundation_s_f_18": {
            "enabled": True, "price": 500_000, "qty": 1,
            "customer_side": False, "is_on_request": False,
            "retail": 500_000, "dealer_is_synthetic": False,
            "block": "foundations",
        },
        "delivery_default": {
            "enabled": True, "price": 70_000, "qty": 1,
            "customer_side": False, "is_on_request": False,
            "retail": 70_000, "dealer_is_synthetic": False,
            "block": "delivery",
        },
    }
    items = build_spec_items(state, prices, models_json)
    for it in items:
        assert "payment_group" in it, f"Нет payment_group в item {it}"
        assert it["payment_group"] in (
            "scales", "foundation", "delivery", "installation_and_verification"
        )


def test_resolve_payment_group_rules():
    """Правила маппинга item_key → payment_group."""
    # модель → scales
    assert resolve_payment_group("vesta-с-60-18") == "scales"
    # ОРИОН → scales
    assert resolve_payment_group("orion_standard") == "scales"
    assert resolve_payment_group("orion_auto_plus") == "scales"
    # фундамент → foundation
    assert resolve_payment_group("foundation_lite_18") == "foundation"
    assert resolve_payment_group("foundation_s_f_24") == "foundation"
    # доставка → delivery
    assert resolve_payment_group("delivery_default") == "delivery"
    # монтаж и поверка → installation_and_verification
    assert resolve_payment_group("install_default") == "installation_and_verification"
    assert resolve_payment_group("verification_default") == "installation_and_verification"
    # рамы / пандусы / ограждения / навес / люки / конструкционные → scales
    assert resolve_payment_group("frame_standard") == "scales"
    assert resolve_payment_group("ramp_set_1x350") == "scales"
    assert resolve_payment_group("fence_norma") == "scales"
    assert resolve_payment_group("canopy_turnkey_18") == "scales"
    assert resolve_payment_group("hatches_standard") == "scales"


# --- build_construction_description ---


def test_construction_description_solid():
    state = {
        "construction_beam": "Двутавр 25Б1",
        "construction_beam_count": 8,
        "construction_center_beam": "Швеллер №14",
        "construction_center_beam_count": 2,
        "construction_deck_mm": 8,
        "construction_underlining_mm": 4,
    }
    text = build_construction_description(state)
    assert "сплошная" in text
    assert "Двутавр 25Б1" in text
    assert "8 шт." in text
    assert "Швеллер №14" in text
    assert "2 шт." in text
    assert "настила 8 мм" in text
    assert "подшив 4 мм" in text


def test_construction_description_rail():
    state = {
        "construction_beam": "Двутавр 30Б1",
        "construction_beam_count": 4,
        "construction_center_beam": "",
        "construction_center_beam_count": 0,
        "construction_deck_mm": 6,
        "construction_underlining_mm": 3,
    }
    text = build_construction_description(state)
    assert "колейная" in text
    assert "Двутавр 30Б1" in text
    assert "4 шт." in text
    assert "Швеллер" not in text
    assert "настила 6 мм" in text
    assert "подшив 3 мм" in text

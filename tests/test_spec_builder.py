"""Тесты build_spec_items (с overrides) и build_construction_description."""
from __future__ import annotations

from src.spec_builder import (
    build_construction_description,
    build_spec_items,
    resolve_dynamic_option_label,
    resolve_payment_group,
)
from src.term_days import resolve_term_days


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
    """Ручное значение в state переопределяет дефолт по составу."""
    state = {"total_term_days": 42}
    items = [{"item_key": "vesta-с-60-18"}, {"item_key": "install_default"}]
    assert resolve_term_days(items, state) == 42


def test_resolve_term_days_falls_back_to_default():
    """Если total_term_days=None — возвращается дефолт по составу."""
    state = {"total_term_days": None}
    items = [
        {"item_key": "vesta-с-60-18"},
        {"item_key": "install_default"},
        {"item_key": "foundation_s_f_18"},
    ]
    # scales(20) + install(3) + foundation(10) = 33
    assert resolve_term_days(items, state) == 33


# --- resolve_dynamic_option_label ---


def test_dynamic_label_foundation_s_f_substitutes_line_s():
    """foundation_s_f_18 + line=С → 'Фундамент под ВЕСТА-С, 18м'."""
    result = resolve_dynamic_option_label(
        "foundation_s_f_18",
        "Фундамент под ВЕСТА-С/Ф/П, 18м",
        "С",
    )
    assert result == "Фундамент под ВЕСТА-С, 18м"


def test_dynamic_label_foundation_s_f_substitutes_line_f():
    """foundation_s_f_24 + line=Ф → 'Фундамент под ВЕСТА-Ф, 24м'."""
    result = resolve_dynamic_option_label(
        "foundation_s_f_24",
        "Фундамент под ВЕСТА-С/Ф/П, 24м",
        "Ф",
    )
    assert result == "Фундамент под ВЕСТА-Ф, 24м"


def test_dynamic_label_foundation_s_f_substitutes_line_p():
    """foundation_s_f_22 + line=П → 'Фундамент под ВЕСТА-П, 22м'."""
    result = resolve_dynamic_option_label(
        "foundation_s_f_22",
        "Фундамент под ВЕСТА-С/Ф/П, 22м",
        "П",
    )
    assert result == "Фундамент под ВЕСТА-П, 22м"


def test_dynamic_label_foundation_lite_sl_fl():
    """foundation_lite_sl_fl_20 + line=СЛ → 'Фундамент пандусный «ЛАЙТ» под ВЕСТА-СЛ, 20м'."""
    result = resolve_dynamic_option_label(
        "foundation_lite_sl_fl_20",
        "Фундамент пандусный «ЛАЙТ» под ВЕСТА-СЛ/ФЛ, 20м",
        "СЛ",
    )
    assert result == "Фундамент пандусный «ЛАЙТ» под ВЕСТА-СЛ, 20м"


def test_dynamic_label_foundation_std_sl_fl():
    """foundation_std_sl_fl_24 + line=ФЛ → 'Фундамент пандусный «Стандарт» под ВЕСТА-ФЛ, 24м'."""
    result = resolve_dynamic_option_label(
        "foundation_std_sl_fl_24",
        "Фундамент пандусный «Стандарт» под ВЕСТА-СЛ/ФЛ, 24м",
        "ФЛ",
    )
    assert result == "Фундамент пандусный «Стандарт» под ВЕСТА-ФЛ, 24м"


def test_dynamic_label_foundation_supervision_unchanged():
    """foundation_supervision не содержит группового обозначения — без изменений."""
    label = "Курирование строительства фундамента ВЕСТА"
    assert resolve_dynamic_option_label("foundation_supervision", label, "С") == label
    assert resolve_dynamic_option_label("foundation_supervision", label, "СЛ") == label


def test_dynamic_label_non_foundation_unchanged():
    """Не-foundation ключ возвращает label без изменений."""
    assert resolve_dynamic_option_label(
        "frame_18", "Рама стандартная 18м", "С"
    ) == "Рама стандартная 18м"
    assert resolve_dynamic_option_label(
        "orion_standard", "ПАК ОРИОН Стандарт", "Ф"
    ) == "ПАК ОРИОН Стандарт"


def test_dynamic_label_unmatched_line_keeps_label():
    """Линия не подходит к группе — label не меняется (защита от ошибок матчинга)."""
    # foundation_s_f_18 ожидает {С, Ф, П}, а пришла СЛ — не подменяем
    result = resolve_dynamic_option_label(
        "foundation_s_f_18", "Фундамент под ВЕСТА-С/Ф/П, 18м", "СЛ"
    )
    assert result == "Фундамент под ВЕСТА-С/Ф/П, 18м"


# --- Bonus: dynamic labels для frame_* и ramp_* ---


def test_dynamic_label_frame_substitutes_line_s():
    """frame_20 + line=С → 'Рама под весы ВЕСТА-С, 20м'."""
    result = resolve_dynamic_option_label(
        "frame_20",
        "Рама под весы ВЕСТА-С(Ф)/ФЛ(СЛ), 20м",
        "С",
    )
    assert result == "Рама под весы ВЕСТА-С, 20м"


def test_dynamic_label_frame_substitutes_line_fl():
    """frame_18 + line=ФЛ → 'Рама под весы ВЕСТА-ФЛ, 18м'."""
    result = resolve_dynamic_option_label(
        "frame_18",
        "Рама под весы ВЕСТА-С(Ф)/ФЛ(СЛ), 18м",
        "ФЛ",
    )
    assert result == "Рама под весы ВЕСТА-ФЛ, 18м"


def test_dynamic_label_ramp_f_s_substitutes_line():
    """ramp_set_f_s + line=С → подмена Ф/С на С."""
    result = resolve_dynamic_option_label(
        "ramp_set_f_s",
        "Комплект пандусов под весы ВЕСТА-Ф/С (L=3,9м)",
        "С",
    )
    assert result == "Комплект пандусов под весы ВЕСТА-С (L=3,9м)"


def test_dynamic_label_ramp_fl_sl_substitutes_line():
    """ramp_set_fl_sl + line=СЛ → подмена ФЛ/СЛ на СЛ."""
    result = resolve_dynamic_option_label(
        "ramp_set_fl_sl",
        "Комплект пандусов под весы ВЕСТА-ФЛ/СЛ (L=2,9м)",
        "СЛ",
    )
    assert result == "Комплект пандусов под весы ВЕСТА-СЛ (L=2,9м)"


def test_dynamic_label_frame_no_placeholder_unchanged():
    """frame_18 с лейблом без плейсхолдера — возвращается без изменений."""
    assert resolve_dynamic_option_label(
        "frame_18", "Рама стандартная 18м", "С"
    ) == "Рама стандартная 18м"


def test_dynamic_label_ramp_f_s_wrong_line_unchanged():
    """ramp_set_f_s + line=СЛ — линия не в группе, label без изменений."""
    label = "Комплект пандусов под весы ВЕСТА-Ф/С (L=3,9м)"
    assert resolve_dynamic_option_label("ramp_set_f_s", label, "СЛ") == label


# --- Fix 1: ограждение не должно попадать в имя строки весов ---


def test_model_name_excludes_fence(prices, models_json):
    """Имя первой позиции (весы) содержит ровно 3 части: название, датчики, терминал.

    Ограждение — отдельная строка spec_items, НЕ часть имени модели.
    """
    state = _base_state()
    state["options"] = {
        "fence_norma_20": {
            "enabled": True,
            "price": 128_000,
            "qty": 1,
            "customer_side": False,
            "is_on_request": False,
            "retail": 128_000,
            "dealer_is_synthetic": False,
            "block": "fences",
        }
    }
    items = build_spec_items(state, prices, models_json)
    model_name = items[0]["name"]
    parts = model_name.split("\n")
    assert len(parts) == 3, f"Ожидалось 3 части, получено {len(parts)}: {parts}"
    assert "Ограждение" not in model_name
    assert "ВЕСТА" in parts[0]
    assert parts[1].startswith("Датчики:")
    assert parts[2].startswith("Терминал:")


def test_build_spec_items_uses_dynamic_foundation_label(prices, models_json):
    """Имя фундамента включает тип исполнения и полный код модели."""
    state = _base_state()  # line=С, model=vesta-с-60-18
    state["foundation_execution"] = "пандусный"
    state["options"] = {
        "foundation_s_f_18": {
            "enabled": True, "price": 500_000, "qty": 1,
            "customer_side": False, "is_on_request": False,
            "retail": 500_000, "dealer_is_synthetic": False,
            "block": "foundations",
        }
    }
    items = build_spec_items(state, prices, models_json)
    foundation = next(i for i in items if i["item_key"] == "foundation_s_f_18")
    assert foundation["name"] == (
        "Фундамент железобетонный пандусный под весы ВЕСТА-С-60-18, 18м"
    )
    assert "С/Ф/П" not in foundation["name"]


def test_build_spec_items_foundation_name_uses_manager_selected_priamok(
    prices, models_json
):
    """UI-выбор 'приямок' попадает в имя фундаментной позиции КП."""
    state = _base_state()
    state["foundation_execution"] = "приямок"
    state["options"] = {
        "foundation_s_f_18": {
            "enabled": True, "price": 500_000, "qty": 1,
            "customer_side": False, "is_on_request": False,
            "retail": 500_000, "dealer_is_synthetic": False,
            "block": "foundation_and_base",
        }
    }
    items = build_spec_items(state, prices, models_json)
    foundation = next(i for i in items if i["item_key"] == "foundation_s_f_18")
    assert foundation["name"] == (
        "Фундамент железобетонный в приямок под весы ВЕСТА-С-60-18, 18м"
    )


def test_build_spec_items_uses_dynamic_frame_and_ramp_labels(prices, models_json):
    """Для модели С — frame_20 и ramp_set_f_s в spec_items должны иметь
    лейбл с конкретной линией («ВЕСТА-С»), а не дженерик («С(Ф)/ФЛ(СЛ)» / «Ф/С»)."""
    state = _base_state()
    state["model_id"] = "vesta-с-80-20"
    state["model_max"] = 80
    state["model_length"] = 20
    state["options"] = {
        "frame_20": {
            "enabled": True, "price": 160_000, "qty": 1,
            "customer_side": False, "is_on_request": False,
            "retail": 160_000, "dealer_is_synthetic": False,
            "block": "frames",
        },
        "ramp_set_f_s": {
            "enabled": True, "price": 80_000, "qty": 1,
            "customer_side": False, "is_on_request": False,
            "retail": 80_000, "dealer_is_synthetic": False,
            "block": "ramps",
        },
    }
    items = build_spec_items(state, prices, models_json)
    by_key = {i["item_key"]: i for i in items}

    frame_name = by_key["frame_20"]["name"]
    assert "ВЕСТА-С" in frame_name
    assert "С(Ф)/ФЛ(СЛ)" not in frame_name

    ramp_name = by_key["ramp_set_f_s"]["name"]
    assert "ВЕСТА-С" in ramp_name
    assert "Ф/С" not in ramp_name


def test_build_spec_items_includes_term_role(prices, models_json):
    """Каждый item должен иметь поле term_role."""
    state = _base_state()
    state["options"] = {
        "foundation_s_f_18": {
            "enabled": True, "price": 500_000, "qty": 1,
            "customer_side": False, "is_on_request": False,
            "retail": 500_000, "dealer_is_synthetic": False,
            "block": "foundations",
        },
        "frame_18": {
            "enabled": True, "price": 50_000, "qty": 1,
            "customer_side": False, "is_on_request": False,
            "retail": 50_000, "dealer_is_synthetic": False,
            "block": "frames",
        },
    }
    items = build_spec_items(state, prices, models_json)
    by_key = {i["item_key"]: i for i in items}
    assert by_key["vesta-с-60-18"]["term_role"] == "scales"
    assert by_key["foundation_s_f_18"]["term_role"] == "foundation"
    # frame_18 — опция весов, role=None (vMerge с весами)
    assert by_key["frame_18"]["term_role"] is None


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


# --- payment_group для новых ключей блока foundation_and_base ---


def test_resolve_payment_group_construction_works():
    """construction_works_* → payment_group = 'foundation' (раньше было 'scales')."""
    assert resolve_payment_group("construction_works_18") == "foundation"
    assert resolve_payment_group("construction_works_20") == "foundation"
    assert resolve_payment_group("construction_works_24") == "foundation"


def test_resolve_payment_group_concrete_base():
    """concrete_base_on_frame → payment_group = 'foundation'."""
    assert resolve_payment_group("concrete_base_on_frame") == "foundation"


def test_resolve_payment_group_road_and_pag_slabs():
    """road_slabs_* и pag_slabs_* → payment_group = 'foundation'."""
    assert resolve_payment_group("road_slabs_18") == "foundation"
    assert resolve_payment_group("pag_slabs_24") == "foundation"
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


# --- multiline model name (sensors / terminal / fence) ---


def test_model_name_is_multiline_with_sensors_and_terminal(
    prices, models_json
):
    state = _base_state()
    state["sensor_id"] = "zemic_dhm9b_30t"
    state["indicator_id"] = "titan_3cs"
    items = build_spec_items(state, prices, models_json)
    name = items[0]["name"]
    assert "ВЕСТА-С-60-18" in name
    assert "Датчики:" in name
    assert "Zemic DHM9B-30t" in name
    assert "шт." in name
    assert "Терминал: ТИТАН 3ЦС" in name


def test_fence_never_in_model_name(prices, models_json):
    """Ограждение не попадает в имя строки весов — ни НОРМА, ни ЛАЙТ."""
    for fence_key in ("fence_norma_18", "fence_light_18"):
        state = _base_state()
        state["options"] = {
            fence_key: {
                "enabled": True, "price": 100_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 100_000, "dealer_is_synthetic": False,
                "block": "fences",
            }
        }
        items = build_spec_items(state, prices, models_json)
        assert "Ограждение" not in items[0]["name"], (
            f"{fence_key}: ограждение не должно быть в имени весов"
        )

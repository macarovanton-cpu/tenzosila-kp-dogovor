"""Тесты фильтров моделей и опций."""
from __future__ import annotations

from src.filters import (
    available_lengths,
    available_max_loads,
    calc_default_deck_mm,
    get_visible_options,
    model_id_from_cascade,
    model_exists_in_prices,
)


def test_available_max_loads_hides_40t_for_s(models_json, prices):
    """40т-моделей нет в prices.json → фильтр скрывает 40т для линейки С."""
    loads = available_max_loads(models_json, "С", prices)
    assert 40 not in loads
    assert 60 in loads and 80 in loads
    # 120т есть только в 24м, поэтому должно остаться
    assert 120 in loads


def test_available_lengths_sl_60_excludes_24(models_json, prices):
    """Для СЛ-60 в prices доступны только 18/20/22 (нет 24)."""
    lens = available_lengths(models_json, "СЛ", 60, prices)
    assert lens == [18, 20, 22]


def test_visible_options_ramps_for_sl_18(prices):
    """Для СЛ-18 в блоке ramps виден только ramp_set_fl_sl, не ramp_set_f_s."""
    visible = get_visible_options(prices["options"], "СЛ", 18, "ramps")
    keys = [k for k, _ in visible]
    assert "ramp_set_fl_sl" in keys
    assert "ramp_set_f_s" not in keys


def test_visible_options_hatches_for_f_22(prices):
    """Для Ф-22 в блоке hatches — только hatches_f_22 (не hatches_fl_22)."""
    visible = get_visible_options(prices["options"], "Ф", 22, "hatches")
    keys = [k for k, _ in visible]
    assert keys == ["hatches_f_22"]


def test_visible_options_foundation_and_base_for_p_18(prices):
    """Для П-18 в блоке foundation_and_base — foundation_s_f_18, не lite/std."""
    visible = get_visible_options(prices["options"], "П", 18, "foundation_and_base")
    keys = [k for k, _ in visible]
    assert "foundation_s_f_18" in keys
    assert "foundation_lite_sl_fl_18" not in keys
    assert "foundation_std_sl_fl_18" not in keys


def test_visible_options_foundation_and_base_contains_six_variant_families(prices):
    """Единый блок показывает все 6 семейств фундамента/основания для С-18."""
    visible = get_visible_options(prices["options"], "С", 18, "foundation_and_base")
    keys = [k for k, _ in visible]

    assert "foundation_s_f_18" in keys
    assert "foundation_supervision" in keys
    assert "construction_works_18" in keys
    assert "concrete_base_on_frame" in keys
    assert "road_slabs_18" in keys
    assert "pag_slabs_18" in keys


def test_model_id_from_cascade_and_exists(prices):
    mid = model_id_from_cascade("С", 60, 18)
    assert mid == "vesta-с-60-18"
    assert model_exists_in_prices(mid, prices)
    assert not model_exists_in_prices("vesta-с-40-18", prices)


def test_calc_default_deck_mm_boundary_60():
    """≤60 т → 6 мм, >60 т → 8 мм."""
    assert calc_default_deck_mm(40) == 6
    assert calc_default_deck_mm(60) == 6
    assert calc_default_deck_mm(61) == 8
    assert calc_default_deck_mm(80) == 8
    assert calc_default_deck_mm(100) == 8

"""Тесты логики расчёта слайдеров и итогов."""
from __future__ import annotations

from src.pricing import (
    calc_totals,
    color_code,
    get_model_slider_params,
    get_slider_params,
)


def test_slider_params_class_a_ramp_set_f_s(prices):
    """Класс A: min=dealer_ru, max=round(retail*1.4), default=retail."""
    entry = prices["options"]["ramp_set_f_s"]
    params = get_slider_params(entry)
    assert params.kind == "slider"
    assert params.min_v == 349600
    assert params.max_v == round(380000 * 1.4)  # 532000
    assert params.default_v == 380000
    assert params.dealer == 349600
    assert params.is_on_request is False
    assert params.dealer_is_synthetic is False


def test_slider_params_class_b_construction_works_20(prices):
    """Класс B: min=retail*0.6, max=retail*1.4, dealer не показываем."""
    entry = prices["options"]["construction_works_20"]
    retail = int(entry["price_retail"])
    params = get_slider_params(entry)
    assert params.kind == "slider"
    assert params.min_v == round(retail * 0.6)
    assert params.max_v == round(retail * 1.4)
    assert params.default_v == retail
    assert params.dealer is None


def test_slider_params_class_c_verification(prices):
    """Класс C: number_input с range_min/range_max, allow_customer_value=True."""
    entry = prices["options"]["verification_default"]
    params = get_slider_params(entry)
    assert params.kind == "number_input"
    assert params.min_v == 20000
    assert params.max_v == 2000000
    assert params.default_v == 60000
    assert params.allow_customer_value is True


def test_slider_params_unknown_22m_frame_22(prices):
    """UNKNOWN (22м без price_class): dealer = retail*0.92 (synthetic)."""
    entry = prices["options"]["frame_22"]
    retail = int(entry["price_retail"])
    params = get_slider_params(entry)
    assert params.kind == "slider"
    assert params.dealer_is_synthetic is True
    assert params.dealer == round(retail * 0.92)
    assert params.min_v == round(retail * 0.92)
    assert params.max_v == round(retail * 1.4)


def test_slider_params_on_request_canopy_24(prices):
    """canopy_turnkey_24: on_request=True блокирует слайдер."""
    entry = prices["options"]["canopy_turnkey_24"]
    params = get_slider_params(entry)
    assert params.is_on_request is True


def test_model_slider_uses_dealer_as_min(prices):
    price = prices["models"]["vesta-с-60-18"]
    params = get_model_slider_params(price)
    assert params.min_v == price["dealer_ru"]
    assert params.default_v == price["retail"]
    assert params.max_v == round(price["retail"] * 1.4)


def test_color_code_rules():
    assert color_code(1000, 1000, 900) == "🟢"
    assert color_code(950, 1000, 900) == "🟡"
    assert color_code(800, 1000, 900) == "🔴"
    # Без дилера (класс B) — красного не бывает
    assert color_code(500, 1000, None) == "🟡"


def test_calc_totals_extracts_vat_from_inclusive_prices():
    """Цены в prices.json уже с НДС 22%; НДС = total*0.22/1.22."""
    items = [{"total": 1220000}]
    totals = calc_totals(items)
    assert totals["with_vat"] == 1220000
    assert totals["vat"] == round(1220000 * 0.22 / 1.22)  # ≈ 220000
    assert totals["without_vat"] == 1220000 - totals["vat"]

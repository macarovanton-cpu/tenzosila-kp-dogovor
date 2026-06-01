"""Тесты логики расчёта слайдеров и итогов."""
from __future__ import annotations

import pytest

from src.pricing import (
    calc_slider_step,
    calc_totals,
    color_code,
    get_model_slider_params,
    get_slider_params,
    percent_to_retail,
)


# --- Шаг слайдера ---


def test_calc_slider_step_large():
    assert calc_slider_step(2_500_000) == 10_000


def test_calc_slider_step_medium():
    assert calc_slider_step(380_000) == 5_000


def test_calc_slider_step_small():
    assert calc_slider_step(60_000) == 1_000


def test_calc_slider_step_boundaries():
    assert calc_slider_step(100_001) == 5_000
    assert calc_slider_step(100_000) == 1_000
    assert calc_slider_step(1_000_001) == 10_000
    assert calc_slider_step(1_000_000) == 5_000


# --- Границы слайдеров по классам ---


def test_slider_params_class_a_ramp_set_f_s(prices):
    """Класс A: min=ceil(dealer/1000)*1000, max=floor(retail*1.4/1000)*1000,
    default=round(retail/1000)*1000."""
    entry = prices["options"]["ramp_set_f_s"]
    # retail=380_000, dealer=349_600
    params = get_slider_params(entry)
    assert params.kind == "slider"
    assert params.min_v == 350_000       # ceil(349_600/1000)*1000
    assert params.max_v == 532_000       # floor(380_000*1.4/1000)*1000 = floor(532_000)
    assert params.default_v == 380_000   # round(380_000/1000)*1000
    assert params.dealer == 349_600
    assert params.step == 5_000          # max_v=532_000 > 100_000 → 5_000
    assert params.is_on_request is False
    assert params.dealer_is_synthetic is False


def test_slider_params_class_b_construction_works_20(prices):
    """Класс B: min=ceil(retail*0.6/1000)*1000, max=floor(retail*1.4/1000)*1000."""
    entry = prices["options"]["construction_works_20"]
    retail = int(entry["price_retail"])
    params = get_slider_params(entry)
    assert params.kind == "slider"
    assert params.min_v % 1000 == 0
    assert params.max_v % 1000 == 0
    assert params.default_v % 1000 == 0
    assert params.min_v >= retail * 0.6  # ceil — округляем вверх
    assert params.max_v <= retail * 1.4  # floor — округляем вниз
    assert params.dealer is None


def test_slider_params_class_c_verification(prices):
    """Класс C: number_input с округлением range_min/range_max, allow_customer_value=True."""
    entry = prices["options"]["verification_default"]
    # range_min=20_000, range_max=2_000_000
    params = get_slider_params(entry)
    assert params.kind == "number_input"
    assert params.min_v == 20_000
    assert params.max_v == 2_000_000
    assert params.default_v == 60_000   # round(60_000/1000)*1000
    assert params.step == 10_000         # max_v > 1_000_000
    assert params.allow_customer_value is True


def test_slider_params_class_c_bytovka(prices):
    """Бытовка: ручной диапазон 200К–1.5М, дефолт retail."""
    entry = prices["options"]["bytovka_weigh_room"]
    params = get_slider_params(entry)
    assert params.kind == "number_input"
    assert params.min_v == 200_000
    assert params.max_v == 1_500_000
    assert params.default_v == int(entry["price_retail"])
    assert params.step == 10_000


def test_slider_params_unknown_22m_frame_22(prices):
    """UNKNOWN (22м без price_class): min=ceil(retail*0.92/1000), dealer помечен synthetic."""
    entry = prices["options"]["frame_22"]
    params = get_slider_params(entry)
    assert params.kind == "slider"
    assert params.dealer_is_synthetic is True
    assert params.min_v % 1000 == 0
    assert params.max_v % 1000 == 0
    assert params.dealer == params.min_v


def test_slider_params_on_request_canopy_24(prices):
    """canopy_turnkey_24: on_request=True блокирует слайдер."""
    entry = prices["options"]["canopy_turnkey_24"]
    params = get_slider_params(entry)
    assert params.is_on_request is True


# --- Слайдер модели ---


def test_model_slider_rounds_to_thousands(prices):
    """Для vesta-фл-60-18: dealer_ru=1_534_958, retail=1_668_432.

    min=1_535_000, max=2_335_000 (floor(1_668_432*1.4)=floor(2_335_804.8)),
    default=1_668_000.
    """
    price = {"retail": 1_668_432, "dealer_ru": 1_534_958}
    params = get_model_slider_params(price)
    assert params.min_v == 1_535_000
    assert params.max_v == 2_335_000
    assert params.default_v == 1_668_000
    assert params.step == 10_000        # max_v > 1_000_000


def test_model_slider_standard_width_keeps_existing_bounds():
    """Ширина 3.0 м не меняет существующую логику слайдера модели."""
    price = {"retail": 1_668_432, "dealer_ru": 1_534_958}

    default_params = get_model_slider_params(price)
    width_params = get_model_slider_params(price, platform_width_m=3.0)

    assert width_params == default_params


def test_model_slider_nonstandard_width_scales_price_and_expands_max():
    """Для 3.5 м цена масштабируется линейно, max дополнительно расширяется на 20%."""
    price = {"retail": 1_668_432, "dealer_ru": 1_534_958}

    params = get_model_slider_params(price, platform_width_m=3.5)

    scaled_retail = round(1_668_432 * 3.5 / 3.0)
    scaled_dealer = round(1_534_958 * 3.5 / 3.0)
    assert params.retail == scaled_retail
    assert params.dealer == scaled_dealer
    assert params.min_v == 1_791_000
    assert params.default_v == 1_947_000
    assert params.max_v == 3_270_000


def test_model_slider_real_model_s_60_18(prices):
    """На реальной модели vesta-с-60-18 все границы кратны 1000 и default ∈ [min, max]."""
    price = prices["models"]["vesta-с-60-18"]
    params = get_model_slider_params(price)
    assert params.min_v % 1000 == 0
    assert params.max_v % 1000 == 0
    assert params.default_v % 1000 == 0
    assert params.min_v <= params.default_v <= params.max_v
    assert params.dealer == price["dealer_ru"]
    assert params.retail == price["retail"]


# --- Прочее ---


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


def test_percent_to_retail_at_retail():
    assert percent_to_retail(1000, 1000) == 0.0


def test_percent_to_retail_above_retail():
    assert percent_to_retail(1100, 1000) == pytest.approx(10.0)


def test_percent_to_retail_below_retail():
    assert percent_to_retail(900, 1000) == pytest.approx(-10.0)


def test_percent_to_retail_zero_retail():
    assert percent_to_retail(500, 0) == 0.0

"""Логика расчёта цен: диапазоны слайдеров, классы A/B/C/UNKNOWN, итоги."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from src.config import (
    MAX_COEFF,
    MIN_COEFF_B,
    SYNTHETIC_DEALER_FACTOR,
    VAT_RATE,
)


@dataclass(frozen=True)
class SliderParams:
    kind: str                 # "slider" | "number_input"
    min_v: int
    max_v: int
    default_v: int
    step: int
    dealer: int | None        # None — если дилерская не отображается (класс B)
    retail: int
    is_on_request: bool
    dealer_is_synthetic: bool
    allow_customer_value: bool


def calc_slider_step(max_value: int) -> int:
    """Шаг слайдера по верхней границе диапазона.

    > 1 000 000 → 10 000; > 100 000 → 5 000; иначе → 1 000.
    """
    if max_value > 1_000_000:
        return 10_000
    if max_value > 100_000:
        return 5_000
    return 1_000


def _ceil_to_1000(x: float) -> int:
    return int(math.ceil(x / 1000.0) * 1000)


def _floor_to_1000(x: float) -> int:
    return int(math.floor(x / 1000.0) * 1000)


def _round_to_1000(x: float) -> int:
    return int(round(x / 1000.0) * 1000)


def _scale_model_price(value: int, platform_width_m: float) -> int:
    """Линейно масштабировать цену модели относительно стандартной ширины 3.0 м."""
    return int(round(value * platform_width_m / 3.0))


def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


def _as_unknown_params(entry: dict[str, Any]) -> SliderParams:
    retail = int(entry.get("price_retail") or 0)
    synth_dealer_raw = retail * SYNTHETIC_DEALER_FACTOR
    min_v = _ceil_to_1000(synth_dealer_raw)
    max_v = _floor_to_1000(retail * MAX_COEFF)
    default_v = _clamp(_round_to_1000(retail), min_v, max_v)
    return SliderParams(
        kind="slider",
        min_v=min_v,
        max_v=max_v,
        default_v=default_v,
        step=calc_slider_step(max_v),
        dealer=min_v,
        retail=retail,
        is_on_request=False,
        dealer_is_synthetic=True,
        allow_customer_value=False,
    )


def _on_request_params(entry: dict[str, Any]) -> SliderParams:
    return SliderParams(
        kind="slider",
        min_v=0, max_v=0, default_v=0, step=1,
        dealer=None, retail=0,
        is_on_request=True,
        dealer_is_synthetic=False,
        allow_customer_value=False,
    )


def get_slider_params(entry: dict[str, Any]) -> SliderParams:
    """Вернуть параметры виджета для опции из prices.json."""
    if entry.get("on_request"):
        return _on_request_params(entry)

    price_class = entry.get("price_class")
    retail_raw = entry.get("price_retail")
    retail = int(retail_raw) if retail_raw is not None else 0

    # UNKNOWN (нет price_class) — опции для 22м с synthetic dealer
    if price_class is None:
        return _as_unknown_params(entry)

    if price_class == "C_manual_range":
        min_v = _ceil_to_1000(int(entry.get("range_min", 0)))
        max_v = _floor_to_1000(int(entry.get("range_max", 0)))
        default_v = _clamp(_round_to_1000(retail), min_v, max_v)
        return SliderParams(
            kind="number_input",
            min_v=min_v,
            max_v=max_v,
            default_v=default_v,
            step=calc_slider_step(max_v),
            dealer=None,
            retail=retail,
            is_on_request=False,
            dealer_is_synthetic=False,
            allow_customer_value=bool(entry.get("allow_customer_value")),
        )

    if price_class == "A_retail_and_dealer":
        dealer = int(entry.get("price_dealer_ru") or 0)
        min_v = _ceil_to_1000(dealer)
        max_v = _floor_to_1000(retail * MAX_COEFF)
        default_v = _clamp(_round_to_1000(retail), min_v, max_v)
        return SliderParams(
            kind="slider",
            min_v=min_v,
            max_v=max_v,
            default_v=default_v,
            step=calc_slider_step(max_v),
            dealer=dealer,
            retail=retail,
            is_on_request=False,
            dealer_is_synthetic=False,
            allow_customer_value=False,
        )

    if price_class == "B_retail_only":
        min_v = _ceil_to_1000(retail * MIN_COEFF_B)
        max_v = _floor_to_1000(retail * MAX_COEFF)
        default_v = _clamp(_round_to_1000(retail), min_v, max_v)
        return SliderParams(
            kind="slider",
            min_v=min_v,
            max_v=max_v,
            default_v=default_v,
            step=calc_slider_step(max_v),
            dealer=None,
            retail=retail,
            is_on_request=False,
            dealer_is_synthetic=False,
            allow_customer_value=False,
        )

    # Неизвестный класс — трактуем как UNKNOWN
    return _as_unknown_params(entry)


def get_model_slider_params(
    price_entry: dict[str, Any], *, platform_width_m: float = 3.0
) -> SliderParams:
    """Параметры слайдера цены самой модели (логика класса A)."""
    width = float(platform_width_m or 3.0)
    retail = _scale_model_price(int(price_entry.get("retail", 0)), width)
    dealer = _scale_model_price(int(price_entry.get("dealer_ru", 0)), width)
    max_coeff = MAX_COEFF * (1.2 if width != 3.0 else 1.0)
    min_v = _ceil_to_1000(dealer)
    max_v = _floor_to_1000(retail * max_coeff)
    default_v = _clamp(_round_to_1000(retail), min_v, max_v)
    return SliderParams(
        kind="slider",
        min_v=min_v,
        max_v=max_v,
        default_v=default_v,
        step=calc_slider_step(max_v),
        dealer=dealer,
        retail=retail,
        is_on_request=False,
        dealer_is_synthetic=False,
        allow_customer_value=False,
    )


def color_code(chosen: int, retail: int, dealer: int | None) -> str:
    """🟢 ≥ retail, 🟡 [dealer..retail), 🔴 < dealer (только если dealer задан)."""
    if chosen >= retail:
        return "🟢"
    if dealer is not None and chosen < dealer:
        return "🔴"
    return "🟡"


def percent_to_retail(chosen: int, retail: int) -> float:
    if not retail:
        return 0.0
    return (chosen - retail) / retail * 100.0


def calc_totals(
    spec_items: list[dict[str, Any]], vat_rate: float = VAT_RATE
) -> dict[str, int]:
    """Цены в прайсе включают НДС 22%. Извлекаем НДС из общей суммы."""
    with_vat = sum(int(item.get("total", 0)) for item in spec_items)
    vat = round(with_vat * vat_rate / (1.0 + vat_rate))
    without_vat = with_vat - vat
    return {
        "with_vat": with_vat,
        "vat": vat,
        "without_vat": without_vat,
    }

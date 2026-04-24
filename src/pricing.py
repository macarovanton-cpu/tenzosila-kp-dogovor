"""Логика расчёта цен: диапазоны слайдеров, классы A/B/C/UNKNOWN, итоги."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config import (
    MAX_COEFF,
    MIN_COEFF_B,
    SLIDER_STEP_LARGE,
    SLIDER_STEP_SMALL,
    SLIDER_THRESHOLD,
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


def _step_for(retail: int) -> int:
    return SLIDER_STEP_LARGE if retail >= SLIDER_THRESHOLD else SLIDER_STEP_SMALL


def _as_unknown_params(entry: dict[str, Any]) -> SliderParams:
    retail = int(entry.get("price_retail") or 0)
    synth_dealer = round(retail * SYNTHETIC_DEALER_FACTOR)
    return SliderParams(
        kind="slider",
        min_v=synth_dealer,
        max_v=round(retail * MAX_COEFF),
        default_v=retail,
        step=_step_for(retail),
        dealer=synth_dealer,
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
        return SliderParams(
            kind="number_input",
            min_v=int(entry.get("range_min", 0)),
            max_v=int(entry.get("range_max", 0)),
            default_v=retail,
            step=SLIDER_STEP_LARGE,
            dealer=None,
            retail=retail,
            is_on_request=False,
            dealer_is_synthetic=False,
            allow_customer_value=bool(entry.get("allow_customer_value")),
        )

    if price_class == "A_retail_and_dealer":
        dealer = int(entry.get("price_dealer_ru") or 0)
        return SliderParams(
            kind="slider",
            min_v=dealer,
            max_v=round(retail * MAX_COEFF),
            default_v=retail,
            step=_step_for(retail),
            dealer=dealer,
            retail=retail,
            is_on_request=False,
            dealer_is_synthetic=False,
            allow_customer_value=False,
        )

    if price_class == "B_retail_only":
        return SliderParams(
            kind="slider",
            min_v=round(retail * MIN_COEFF_B),
            max_v=round(retail * MAX_COEFF),
            default_v=retail,
            step=_step_for(retail),
            dealer=None,
            retail=retail,
            is_on_request=False,
            dealer_is_synthetic=False,
            allow_customer_value=False,
        )

    # Неизвестный класс — трактуем как UNKNOWN
    return _as_unknown_params(entry)


def get_model_slider_params(price_entry: dict[str, Any]) -> SliderParams:
    """Параметры слайдера цены самой модели (логика класса A)."""
    retail = int(price_entry.get("retail", 0))
    dealer = int(price_entry.get("dealer_ru", 0))
    return SliderParams(
        kind="slider",
        min_v=dealer,
        max_v=round(retail * MAX_COEFF),
        default_v=retail,
        step=_step_for(retail),
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

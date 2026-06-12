"""Canonical-модели для локальных admin-инструментов прайса."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


PriceItemType = Literal["model", "option"]

UNKNOWN_PRICE_CLASS = "UNKNOWN"
MODEL_PRICE_CLASS = "A_retail_and_dealer"


@dataclass(frozen=True)
class PriceItem:
    """Плоская запись цены модели или опции из `data/prices.json`."""

    item_type: PriceItemType
    key: str
    label: str
    price_retail: int | None
    price_dealer_ru: int | None
    discount_pct: int | float | None
    price_class: str
    on_request: bool
    allow_customer_value: bool
    range_min: int | None
    range_max: int | None
    applies_to_lines: list[str]
    applies_to_lengths: list[int]
    raw_payload: dict[str, Any]

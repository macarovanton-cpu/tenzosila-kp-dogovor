"""Нормализация `data/prices.json` в плоский список price items."""
from __future__ import annotations

from typing import Any

from src.admin.price_models import (
    MODEL_PRICE_CLASS,
    UNKNOWN_PRICE_CLASS,
    PriceItem,
)


def normalize_prices(prices: dict[str, Any]) -> list[PriceItem]:
    """Вернуть модели и опции прайса в едином плоском формате."""

    items: list[PriceItem] = []
    for key, entry in prices.get("models", {}).items():
        items.append(_normalize_model(str(key), entry))
    for key, entry in prices.get("options", {}).items():
        items.append(_normalize_option(str(key), entry))
    return items


def _normalize_model(key: str, entry: dict[str, Any]) -> PriceItem:
    return PriceItem(
        item_type="model",
        key=key,
        label=str(entry.get("label") or key),
        price_retail=_optional_int(entry.get("retail")),
        price_dealer_ru=_optional_int(entry.get("dealer_ru")),
        discount_pct=entry.get("dealer_discount_pct"),
        price_class=MODEL_PRICE_CLASS,
        on_request=False,
        allow_customer_value=False,
        range_min=None,
        range_max=None,
        applies_to_lines=[],
        applies_to_lengths=[],
        raw_payload=dict(entry),
    )


def _normalize_option(key: str, entry: dict[str, Any]) -> PriceItem:
    price_class = entry.get("price_class")
    if price_class is None:
        price_class = UNKNOWN_PRICE_CLASS

    return PriceItem(
        item_type="option",
        key=key,
        label=str(entry.get("label") or key),
        price_retail=_optional_int(entry.get("price_retail")),
        price_dealer_ru=_optional_int(entry.get("price_dealer_ru")),
        discount_pct=entry.get("discount_pct"),
        price_class=str(price_class),
        on_request=bool(entry.get("on_request")),
        allow_customer_value=bool(entry.get("allow_customer_value")),
        range_min=_optional_int(entry.get("range_min")),
        range_max=_optional_int(entry.get("range_max")),
        applies_to_lines=_string_list(entry.get("applies_to_lines")),
        applies_to_lengths=_int_list(entry.get("applies_to_lengths")),
        raw_payload=dict(entry),
    )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _string_list(value: Any) -> list[str]:
    if not value:
        return []
    return [str(item) for item in value]


def _int_list(value: Any) -> list[int]:
    if not value:
        return []
    return [int(item) for item in value]

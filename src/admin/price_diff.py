"""Diff двух наборов canonical price items."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.admin.price_models import PriceItem


SIGNIFICANT_FIELDS: tuple[str, ...] = (
    "price_retail",
    "price_dealer_ru",
    "price_class",
    "range_min",
    "range_max",
    "on_request",
)


@dataclass(frozen=True)
class FieldChange:
    """Изменение одного значимого поля."""

    field: str
    old_value: Any
    new_value: Any


@dataclass(frozen=True)
class ChangedPriceItem:
    """Изменения одной позиции прайса."""

    item_type: str
    item_key: str
    changes: list[FieldChange]


@dataclass(frozen=True)
class PriceDiff:
    """Результат сравнения двух нормализованных прайсов."""

    added: list[PriceItem]
    removed: list[PriceItem]
    changed: list[ChangedPriceItem]


def diff_prices(
    old_items: list[PriceItem],
    new_items: list[PriceItem],
) -> PriceDiff:
    """Сравнить два списка price items по `(item_type, key)`."""

    old_index = {_identity(item): item for item in old_items}
    new_index = {_identity(item): item for item in new_items}

    old_keys = set(old_index)
    new_keys = set(new_index)

    added = [new_index[key] for key in sorted(new_keys - old_keys)]
    removed = [old_index[key] for key in sorted(old_keys - new_keys)]
    changed = [
        _diff_item(old_index[key], new_index[key])
        for key in sorted(old_keys & new_keys)
    ]

    return PriceDiff(
        added=added,
        removed=removed,
        changed=[item for item in changed if item.changes],
    )


def _identity(item: PriceItem) -> tuple[str, str]:
    return (item.item_type, item.key)


def _diff_item(old_item: PriceItem, new_item: PriceItem) -> ChangedPriceItem:
    changes = []
    for field in SIGNIFICANT_FIELDS:
        old_value = getattr(old_item, field)
        new_value = getattr(new_item, field)
        if old_value != new_value:
            changes.append(
                FieldChange(
                    field=field,
                    old_value=old_value,
                    new_value=new_value,
                )
            )
    return ChangedPriceItem(
        item_type=old_item.item_type,
        item_key=old_item.key,
        changes=changes,
    )

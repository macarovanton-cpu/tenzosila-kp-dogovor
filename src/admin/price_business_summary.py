"""Бизнес-сводка изменений прайса для менеджера/РОПа."""
from __future__ import annotations

from dataclasses import dataclass

from src.admin.price_diff import diff_prices
from src.admin.price_models import PriceItem

_ROUNDING_TOLERANCE = 1  # руб — допуск округления (п.1a)


@dataclass(frozen=True)
class PriceChangeEntry:
    """Одна позиция в группе сводки."""

    key: str
    label: str
    item_type: str
    old_value: int | None
    new_value: int | None
    delta_pct: float | None  # None если нельзя рассчитать


@dataclass(frozen=True)
class BusinessSummary:
    """Сгруппированный diff для отображения в UI."""

    price_up: list[PriceChangeEntry]
    price_down: list[PriceChangeEntry]
    added: list[PriceChangeEntry]
    removed: list[PriceChangeEntry]
    to_on_request: list[PriceChangeEntry]


def build_business_summary(
    old_items: list[PriceItem],
    new_items: list[PriceItem],
) -> BusinessSummary:
    """Построить бизнес-сводку изменений поверх diff_prices."""
    diff = diff_prices(old_items, new_items)

    old_index = {(item.item_type, item.key): item for item in old_items}
    new_index = {(item.item_type, item.key): item for item in new_items}

    price_up: list[PriceChangeEntry] = []
    price_down: list[PriceChangeEntry] = []
    to_on_request: list[PriceChangeEntry] = []

    for changed_item in diff.changed:
        key = changed_item.item_key
        itype = changed_item.item_type
        old = old_index[(itype, key)]
        new = new_index[(itype, key)]

        # Переход в «по запросу» — приоритет над сравнением цены
        if not old.on_request and new.on_request:
            to_on_request.append(
                PriceChangeEntry(
                    key=key,
                    label=old.label,
                    item_type=itype,
                    old_value=old.price_retail,
                    new_value=None,
                    delta_pct=None,
                )
            )
            continue

        old_retail = old.price_retail
        new_retail = new.price_retail

        if old_retail is None or new_retail is None:
            continue  # нет цены для сравнения

        delta_abs = new_retail - old_retail
        if abs(delta_abs) <= _ROUNDING_TOLERANCE:
            continue  # шум округления — игнорируем

        delta_pct: float | None = None
        if old_retail != 0:
            delta_pct = delta_abs / old_retail * 100

        entry = PriceChangeEntry(
            key=key,
            label=old.label,
            item_type=itype,
            old_value=old_retail,
            new_value=new_retail,
            delta_pct=delta_pct,
        )
        if delta_abs > 0:
            price_up.append(entry)
        else:
            price_down.append(entry)

    added = [
        PriceChangeEntry(
            key=item.key,
            label=item.label,
            item_type=item.item_type,
            old_value=None,
            new_value=item.price_retail,
            delta_pct=None,
        )
        for item in diff.added
    ]

    removed = [
        PriceChangeEntry(
            key=item.key,
            label=item.label,
            item_type=item.item_type,
            old_value=item.price_retail,
            new_value=None,
            delta_pct=None,
        )
        for item in diff.removed
    ]

    return BusinessSummary(
        price_up=price_up,
        price_down=price_down,
        added=added,
        removed=removed,
        to_on_request=to_on_request,
    )

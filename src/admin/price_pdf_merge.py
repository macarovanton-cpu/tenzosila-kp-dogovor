"""Сборка единого list[PriceItem] из результатов двух парсеров PDF.

Дилерский источник приоритетен при совпадении ключей.
source ('dealer' | 'retail') сохраняется в raw_payload каждого PriceItem.
applies_to_lines / applies_to_lengths берутся из data/prices.json (только метаданные).
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from src.admin.price_models import PriceItem

_PRICES_JSON = Path(__file__).parent.parent.parent / "data" / "prices.json"


def merge_price_items(
    dealer_items: list[PriceItem],
    retail_items: list[PriceItem],
) -> list[PriceItem]:
    """Объединяет два списка PriceItem; при совпадении ключа побеждает дилерский."""
    lookup = _load_applies_to_lookup()

    merged: dict[str, PriceItem] = {}
    for item in dealer_items:
        enriched = _enrich(_tag_source(item, "dealer"), lookup)
        merged[enriched.key] = enriched

    for item in retail_items:
        if item.key not in merged:
            enriched = _enrich(_tag_source(item, "retail"), lookup)
            merged[enriched.key] = enriched

    return list(merged.values())


# ──────────────────── вспомогательные ────────────────────

def _load_applies_to_lookup() -> dict[str, tuple[list[str], list[int]]]:
    """Читает options из prices.json → {key: (applies_to_lines, applies_to_lengths)}."""
    data = json.loads(_PRICES_JSON.read_text(encoding="utf-8"))
    result: dict[str, tuple[list[str], list[int]]] = {}
    for key, opt in data.get("options", {}).items():
        lines: list[str] = opt.get("applies_to_lines", [])
        lengths: list[int] = opt.get("applies_to_lengths", [])
        if lines or lengths:
            result[key] = (lines, lengths)
    return result


def _tag_source(item: PriceItem, source: str) -> PriceItem:
    return dataclasses.replace(item, raw_payload={**item.raw_payload, "source": source})


def _enrich(
    item: PriceItem,
    lookup: dict[str, tuple[list[str], list[int]]],
) -> PriceItem:
    """Заполняет applies_to_* из lookup, если поля пусты."""
    if item.applies_to_lines or item.applies_to_lengths:
        return item
    if item.key not in lookup:
        return item
    lines, lengths = lookup[item.key]
    return dataclasses.replace(item, applies_to_lines=lines, applies_to_lengths=lengths)

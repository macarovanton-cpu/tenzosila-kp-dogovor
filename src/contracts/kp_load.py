"""Атомарная сборка данных КП для загрузки в state страницы Договор."""
from __future__ import annotations

from typing import Any

from src.contracts.from_kp import (
    build_specification_from_kp_snapshot,
    build_specification_items,
)


def build_kp_payload(
    kp_row: dict[str, Any],
    prices: dict[str, Any],
    models_json: dict[str, Any],
    payment_terms: dict[str, Any],
) -> dict[str, Any]:
    """Собрать всё для загрузки КП в state: spec, items, snapshot, payment.

    Кидает при кривом снапшоте — вызывающий обязан не коммитить state частично
    (атомарность страницы держится на этом контракте).
    """
    spec = build_specification_from_kp_snapshot(
        kp_row, prices, models_json, payment_terms
    )
    items = build_specification_items(kp_row, prices)
    snap = kp_row.get("data") or {}
    return {
        "spec": spec,
        "items": items,
        "snapshot": snap,
        "payment": snap.get("payment") or {},
    }

"""SpecItem — единица спецификации договора."""
from __future__ import annotations

import uuid
from typing import Literal, TypedDict


class SpecItem(TypedDict):
    id: str
    name: str
    unit: str
    quantity: float
    price_per_unit: float
    total: float
    payment_group: int | None
    is_custom: bool
    source: Literal["preset", "custom"]
    metadata: dict


def make_custom_item(
    name: str = "",
    unit: str = "шт",
    quantity: float = 1.0,
    price_per_unit: float = 0.0,
) -> SpecItem:
    """Создать пустую кастомную позицию."""
    total = quantity * price_per_unit
    return {  # type: ignore[return-value]
        "id": f"custom_{uuid.uuid4().hex[:8]}",
        "name": name,
        "unit": unit,
        "quantity": quantity,
        "price_per_unit": price_per_unit,
        "total": total,
        "payment_group": None,
        "is_custom": True,
        "source": "custom",
        "metadata": {},
    }


def recalculate_totals(items: list[dict]) -> list[dict]:
    """Пересчитать total = quantity * price_per_unit для каждой позиции."""
    for item in items:
        item["total"] = item["quantity"] * item["price_per_unit"]
    return items


def _option_key_to_spec_id(key: str) -> str | None:
    """Вернуть canonical id позиции для ключа опции или None (→ custom)."""
    if key == "delivery_default":
        return "delivery"
    if key == "install_default":
        return "installation"
    if key == "verification_default":
        return "verification"
    if key.startswith("foundation_"):
        return "foundation"
    if "orion_install" in key:
        return "orion_install"
    if key.startswith("orion"):
        return "orion"
    if key.startswith("fence"):
        return "fence"
    if key.startswith("bytovka"):
        return "bytovka"
    if key.startswith("rama"):
        return "rama"
    if key.startswith("pandus"):
        return "pandus"
    return None

"""Сборка spec_items — списка позиций для раздела спецификации КП."""
from __future__ import annotations

from typing import Any

from src.config import (
    DEFAULT_MODEL_TERM_DAYS,
    OPTION_BLOCKS_ORDER,
    TERM_DAYS_BY_BLOCK,
    UNIT_BY_BLOCK,
)
from src.data_loader import get_model_by_id, get_price_by_model_id
from src.filters import get_visible_options


def _format_model_name(model: dict | None, model_id: str) -> str:
    if model and model.get("full_name"):
        return f"Весы автомобильные {model['full_name']}"
    return f"Весы автомобильные {model_id}"


def _option_name(entry: dict, opt_state: dict) -> str:
    name = entry.get("label", "")
    if opt_state.get("customer_side"):
        name = f"{name} (силами Заказчика)"
    return name


def build_spec_items(
    state: dict[str, Any], prices: dict, models_json: dict
) -> list[dict]:
    """Собрать упорядоченный список позиций: модель + включённые опции."""
    items: list[dict] = []

    model_id = state.get("model_id", "")
    price_entry = get_price_by_model_id(prices, model_id)
    model = get_model_by_id(models_json, model_id)
    model_price = state.get("model_price")
    if price_entry is not None:
        if model_price is None:
            model_price = int(price_entry.get("retail", 0))
        items.append({
            "num": 1,
            "name": _format_model_name(model, model_id),
            "qty": 1,
            "unit": "шт",
            "price": int(model_price),
            "total": int(model_price),
            "term_days": DEFAULT_MODEL_TERM_DAYS,
        })

    line = state.get("model_line", "")
    length = int(state.get("model_length", 18))
    prices_options = prices.get("options", {})
    options_state = state.get("options", {})

    for block_id in OPTION_BLOCKS_ORDER:
        for key, entry in get_visible_options(prices_options, line, length, block_id):
            opt = options_state.get(key)
            if not opt or not opt.get("enabled"):
                continue
            qty = int(opt.get("qty", 1))
            if opt.get("customer_side"):
                price = 0
            else:
                price = int(opt.get("price", 0))
            items.append({
                "num": len(items) + 1,
                "name": _option_name(entry, opt),
                "qty": qty,
                "unit": UNIT_BY_BLOCK.get(block_id, "шт"),
                "price": price,
                "total": price * qty,
                "term_days": TERM_DAYS_BY_BLOCK.get(block_id, DEFAULT_MODEL_TERM_DAYS),
            })

    return items


def resolve_term_days(spec_items: list[dict], state: dict) -> int:
    """Общий срок исполнения: ручной из state (если задан), иначе max из позиций."""
    manual = state.get("total_term_days")
    if manual:
        return int(manual)
    if not spec_items:
        return DEFAULT_MODEL_TERM_DAYS
    return max(int(it.get("term_days", 0)) for it in spec_items)

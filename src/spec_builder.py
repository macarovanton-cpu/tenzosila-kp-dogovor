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


def _apply_override(
    computed_qty: int,
    computed_price: int,
    override: dict | None,
) -> tuple[int, int, bool]:
    """Применить override поверх вычисленных qty/price. Возвращает (qty, price, is_overridden)."""
    if not override:
        return computed_qty, computed_price, False
    ov_qty = override.get("qty")
    ov_price = override.get("price")
    qty = int(ov_qty) if ov_qty is not None else computed_qty
    price = int(ov_price) if ov_price is not None else computed_price
    is_ov = (ov_qty is not None) or (ov_price is not None)
    return qty, price, is_ov


def build_spec_items(
    state: dict[str, Any], prices: dict, models_json: dict
) -> list[dict]:
    """Собрать упорядоченный список позиций: модель + включённые опции.

    Если в state["spec_items_overrides"][item_key] есть qty/price — применяем.
    """
    items: list[dict] = []
    overrides: dict = state.get("spec_items_overrides", {}) or {}

    model_id = state.get("model_id", "")
    price_entry = get_price_by_model_id(prices, model_id)
    model = get_model_by_id(models_json, model_id)
    model_price = state.get("model_price")
    if price_entry is not None:
        if model_price is None:
            model_price = int(price_entry.get("retail", 0))
        qty, price, is_ov = _apply_override(
            1, int(model_price), overrides.get(model_id)
        )
        items.append({
            "num": 1,
            "item_key": model_id,
            "name": _format_model_name(model, model_id),
            "qty": qty,
            "unit": "шт",
            "price": price,
            "total": price * qty,
            "term_days": DEFAULT_MODEL_TERM_DAYS,
            "is_overridden": is_ov,
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
            computed_qty = int(opt.get("qty", 1))
            if opt.get("customer_side"):
                computed_price = 0
            else:
                computed_price = int(opt.get("price", 0))
            qty, price, is_ov = _apply_override(
                computed_qty, computed_price, overrides.get(key)
            )
            items.append({
                "num": len(items) + 1,
                "item_key": key,
                "name": _option_name(entry, opt),
                "qty": qty,
                "unit": UNIT_BY_BLOCK.get(block_id, "шт"),
                "price": price,
                "total": price * qty,
                "term_days": TERM_DAYS_BY_BLOCK.get(block_id, DEFAULT_MODEL_TERM_DAYS),
                "is_overridden": is_ov,
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


def build_construction_description(state: dict) -> str:
    """Готовый русский текст описания конструкции для поля ТХ в DOCX.

    Формат совпадает с UI-превью, но plain text (без Markdown-блока цитаты).
    """
    beam = state.get("construction_beam", "") or "—"
    beam_cnt = state.get("construction_beam_count", 0) or 0
    deck = state.get("construction_deck_mm", 0) or 0
    under = state.get("construction_underlining_mm", 0) or 0
    center_beam = state.get("construction_center_beam", "") or ""
    center_beam_count = state.get("construction_center_beam_count", 0) or 0
    is_rail = not center_beam

    if is_rail:
        return (
            f"Конструкция колейная: {beam} {beam_cnt} шт., "
            f"лист настила {deck} мм рифлёный, "
            f"нижний подшив {under} мм"
        )
    return (
        f"Конструкция сплошная: {beam} {beam_cnt} шт., "
        f"{center_beam} {center_beam_count} шт., "
        f"лист настила {deck} мм рифлёный, "
        f"нижний подшив {under} мм"
    )

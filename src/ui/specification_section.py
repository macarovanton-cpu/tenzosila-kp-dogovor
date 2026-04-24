"""Full-width секция редактируемой спецификации в main area."""
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render_specification_section(state: dict, spec_items: list[dict]) -> None:
    """Секция спецификации под основными колонками, full-width.

    5 колонок: №, Позиция, Кол-во, Цена, Сумма. item_key скрыта.
    Редактируемые: qty и price. Правка молча пишет в spec_items_overrides.
    """
    st.subheader("📊 Спецификация")
    st.caption(
        "Итоговый состав КП с возможностью ручной корректировки перед генерацией"
    )

    if not spec_items:
        st.info("Выберите модель и опции — позиции появятся здесь.")
        return

    rows = []
    for it in spec_items:
        mark = " ✏️" if it.get("is_overridden") else ""
        rows.append(
            {
                "num": it["num"],
                "item_key": it["item_key"],
                "name": it["name"] + mark,
                "qty": int(it["qty"]),
                "price": int(it["price"]),
                "total": int(it["total"]),
            }
        )
    df = pd.DataFrame(rows)
    height = min(500, 50 + 40 * len(rows))

    edited = st.data_editor(
        df,
        hide_index=True,
        width="stretch",
        height=height,
        num_rows="fixed",
        disabled=["num", "name", "total"],
        column_config={
            "num": st.column_config.NumberColumn("№", width="small"),
            "item_key": None,
            "name": st.column_config.TextColumn("Позиция", width="large"),
            "qty": st.column_config.NumberColumn(
                "Кол-во", min_value=1, step=1
            ),
            "price": st.column_config.NumberColumn(
                "Цена, ₽", min_value=0, step=1000, format="%d ₽"
            ),
            "total": st.column_config.NumberColumn(
                "Сумма, ₽", format="%d ₽"
            ),
        },
        key="spec_editor",
    )
    if _sync_overrides(state, spec_items, edited):
        st.rerun()


def _sync_overrides(state: dict, spec_items: list[dict], edited: Any) -> bool:
    """Сравнить edited DataFrame с spec_items и записать изменения в overrides.

    Возвращает True, если словарь overrides изменился — тогда вызывающий
    код должен инициировать st.rerun(), чтобы build_spec_items применил
    override и пересчитал total/totals.
    """
    overrides: dict = state.setdefault("spec_items_overrides", {})
    prev_snapshot = {k: dict(v) for k, v in overrides.items()}

    edited_rows = (
        edited.to_dict("records") if hasattr(edited, "to_dict") else list(edited)
    )
    by_key = {row["item_key"]: row for row in edited_rows}

    for it in spec_items:
        key = it["item_key"]
        row = by_key.get(key)
        if row is None:
            continue
        new_qty = int(row["qty"])
        new_price = int(row["price"])
        cur_ov = overrides.get(key, {}) or {}

        qty_ov = cur_ov.get("qty")
        price_ov = cur_ov.get("price")

        if new_qty != int(it["qty"]):
            qty_ov = new_qty
        if new_price != int(it["price"]):
            price_ov = new_price

        new_ov: dict = {}
        if qty_ov is not None:
            new_ov["qty"] = int(qty_ov)
        if price_ov is not None:
            new_ov["price"] = int(price_ov)

        if new_ov:
            overrides[key] = new_ov
        else:
            overrides.pop(key, None)

    return prev_snapshot != overrides

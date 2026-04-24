"""Sticky-sidebar: редактируемая таблица spec_items, Итого, кнопка генерации."""
from __future__ import annotations

from typing import Any

import streamlit as st


def _fmt_rub(n: int) -> str:
    """Формат '1 234 567 ₽' с пробелами как разделителями тысяч."""
    return f"{int(n):,} ₽".replace(",", " ")


def render_sidebar(
    state: dict,
    spec_items: list[dict],
    errors: list[str],
    warnings: list[str],
    totals: dict,
    payment_preview: str,
    term_days: int,
) -> None:
    with st.sidebar:
        st.header("📋 Превью КП")

        if not spec_items:
            st.info("Выберите модель, чтобы увидеть спецификацию.")
        else:
            _render_spec_editor(state, spec_items)

        st.divider()
        st.markdown("**Итого**")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Без НДС", _fmt_rub(totals["without_vat"]))
            st.metric("НДС 22%", _fmt_rub(totals["vat"]))
        with c2:
            st.metric("С НДС", _fmt_rub(totals["with_vat"]))
            st.metric("Срок исполнения", f"{term_days} дн.")

        st.caption(
            f"Срок действия КП: **{state['kp_valid_days']} дн.** "
            f"от {state['kp_date'].strftime('%d.%m.%Y')}"
        )

        if payment_preview:
            with st.expander("💸 Условия оплаты (превью)", expanded=False):
                st.markdown(payment_preview)

        _render_override_conflict(state)

        st.divider()

        for w in warnings:
            st.warning(w)
        for e in errors:
            st.error(e)

        disabled = bool(errors)
        if st.button(
            "🚀 Сгенерировать КП",
            disabled=disabled,
            width="stretch",
            type="primary",
        ):
            st.success("Готово к генерации (заглушка шага 1.2)")
            with st.expander("spec_items JSON", expanded=True):
                st.json(
                    {
                        "meta": {
                            "client_name": state["client_name"],
                            "lead_number": state["lead_number"],
                            "manager_id": state.get("manager_id", ""),
                            "model_id": state["model_id"],
                            "total_term_days": term_days,
                            "payment_preset_id": state["payment_preset_id"],
                        },
                        "spec_items": spec_items,
                        "totals": totals,
                    }
                )


def _render_spec_editor(state: dict, spec_items: list[dict]) -> None:
    """Редактируемая таблица spec_items (Streamlit data_editor).

    - qty и price: NumberColumn, редактируемые. Формат без пробелов
      (NumberColumn не поддерживает кастомный разделитель тысяч —
      осознанный trade-off для MVP).
    - total: TextColumn, read-only, строка '1 234 567 ₽' с пробелами.
    - num, name: read-only.
    """
    import pandas as pd

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
                "total": _fmt_rub(it["total"]),
            }
        )
    df = pd.DataFrame(rows)

    edited = st.data_editor(
        df,
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        disabled=["num", "item_key", "name", "total"],
        column_config={
            "num": st.column_config.NumberColumn("№", width="small"),
            "item_key": None,  # скрываем техническую колонку
            "name": st.column_config.TextColumn("Позиция", width="large"),
            "qty": st.column_config.NumberColumn("Кол-во", min_value=1, step=1),
            "price": st.column_config.NumberColumn("Цена, ₽", min_value=0, step=1000),
            "total": st.column_config.TextColumn("Сумма, ₽"),
        },
        key="spec_editor",
    )
    # Если пользователь правил qty/price — обновляем overrides и инициируем rerun.
    # Без повторного прохода data_editor показал бы обновлённые qty/price,
    # но total (disabled TextColumn) и Итого остались бы stale: build_spec_items
    # применяет overrides только на следующий rerun.
    if _sync_overrides(state, spec_items, edited):
        st.rerun()


def _sync_overrides(state: dict, spec_items: list[dict], edited: Any) -> bool:
    """Сравнить edited DataFrame с spec_items и записать изменения в overrides.

    Возвращает True, если словарь overrides изменился в этом проходе — тогда
    вызывающий код должен инициировать st.rerun(), чтобы build_spec_items
    применил override и пересчитал total/totals.
    """
    overrides: dict = state.setdefault("spec_items_overrides", {})
    prev_snapshot = {k: dict(v) for k, v in overrides.items()}

    edited_rows = edited.to_dict("records") if hasattr(edited, "to_dict") else list(edited)
    by_key = {row["item_key"]: row for row in edited_rows}

    # Базовая цена/кол-во без overrides — из computed-значений,
    # хранящихся в самом spec_item (price/qty в нём уже могут быть с оверрайдом).
    # Чтобы отличить «user поменял» от «осталось как computed», сравниваем с
    # текущим spec_item — это снимок, полученный из того же источника, что
    # отображается в data_editor до правки.
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

        # qty
        if new_qty != int(it["qty"]):
            qty_ov = new_qty
        # price
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


def _render_override_conflict(state: dict) -> None:
    """Warning, если слайдер цены разошёлся с ручным override."""
    conflict_key = state.get("spec_override_conflict")
    if not conflict_key:
        return
    st.warning(
        "Вы изменили цену этой позиции вручную. "
        "Продолжить со значения слайдера?"
    )
    if st.button("Да, обнулить ручную правку", key="btn_reset_override"):
        overrides = state.setdefault("spec_items_overrides", {})
        ov = overrides.get(conflict_key)
        if ov:
            ov.pop("price", None)
            if not ov:
                overrides.pop(conflict_key, None)
        state.pop("spec_override_conflict", None)
        st.rerun()

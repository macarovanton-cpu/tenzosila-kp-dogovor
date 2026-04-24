"""Sticky-sidebar: превью spec_items, Итого, кнопка генерации."""
from __future__ import annotations

import streamlit as st


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
            table_rows = []
            for it in spec_items:
                table_rows.append(
                    {
                        "№": it["num"],
                        "Позиция": it["name"],
                        "Кол-во": f"{it['qty']} {it['unit']}",
                        "Цена, ₽": f"{int(it['price']):,}".replace(",", " "),
                        "Сумма, ₽": f"{int(it['total']):,}".replace(",", " "),
                    }
                )
            st.dataframe(table_rows, hide_index=True, width="stretch")

        st.divider()
        st.markdown("**Итого**")
        c1, c2 = st.columns(2)
        with c1:
            st.metric(
                "Без НДС",
                f"{totals['without_vat']:,} ₽".replace(",", " "),
            )
            st.metric(
                "НДС 22%",
                f"{totals['vat']:,} ₽".replace(",", " "),
            )
        with c2:
            st.metric(
                "С НДС",
                f"{totals['with_vat']:,} ₽".replace(",", " "),
            )
            st.metric("Срок исполнения", f"{term_days} дн.")

        st.caption(
            f"Срок действия КП: **{state['kp_valid_days']} дн.** "
            f"от {state['kp_date'].strftime('%d.%m.%Y')}"
        )

        if payment_preview:
            with st.expander("💸 Условия оплаты (превью)", expanded=False):
                st.markdown(payment_preview)

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
                            "model_id": state["model_id"],
                            "total_term_days": term_days,
                            "payment_preset_id": state["payment_preset_id"],
                        },
                        "spec_items": spec_items,
                        "totals": totals,
                    }
                )

"""Sticky-sidebar: итоги, сроки, валидация, кнопка генерации."""
from __future__ import annotations

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
        st.header("📋 Итоги КП")

        with st.container(border=True):
            st.metric("ИТОГО с НДС", _fmt_rub(totals["with_vat"]))
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Без НДС", _fmt_rub(totals["without_vat"]))
        with c2:
            st.metric("НДС 22%", _fmt_rub(totals["vat"]))

        st.divider()
        st.markdown("**Сроки**")
        c3, c4 = st.columns(2)
        with c3:
            st.metric("Срок исполнения", f"{term_days} дн.")
        with c4:
            st.metric("КП действует", f"{state['kp_valid_days']} дн.")
        st.caption(f"от {state['kp_date'].strftime('%d.%m.%Y')}")

        if payment_preview:
            with st.expander("💸 Условия оплаты", expanded=False):
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
                            "manager_id": state.get("manager_id", ""),
                            "model_id": state["model_id"],
                            "total_term_days": term_days,
                            "payment_preset_id": state["payment_preset_id"],
                        },
                        "spec_items": spec_items,
                        "totals": totals,
                    }
                )

        if errors:
            st.caption(f"⚠️ {len(errors)} ошибок валидации")
        else:
            st.caption("✅ Готово к генерации")

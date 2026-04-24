"""Sticky-sidebar: итоги, сроки, валидация, кнопка генерации, брендовый футер."""
from __future__ import annotations

import streamlit as st

from src.utils.format import fmt_rub


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
        st.subheader("📋 Итоги")

        with st.container(border=True):
            st.metric("ИТОГО с НДС", fmt_rub(totals["with_vat"]))
        st.caption(
            f"Без НДС: {fmt_rub(totals['without_vat'])}  ·  "
            f"НДС 22%: {fmt_rub(totals['vat'])}"
        )

        st.divider()

        c3, c4 = st.columns(2)
        with c3:
            st.metric("🔨 Исполнение", f"{term_days} дн.")
        with c4:
            st.metric("📅 Действует", f"{state['kp_valid_days']} дн.")
        st.caption(f"от {state['kp_date'].strftime('%d.%m.%Y')}")

        if payment_preview:
            with st.expander("💸 Условия оплаты", expanded=False):
                st.markdown(payment_preview)

        st.divider()

        # Статус валидации
        if errors:
            with st.container(border=True):
                st.markdown(f"**🔴 Ошибки валидации ({len(errors)})**")
                for e in errors:
                    st.markdown(f"- {e}")
        if warnings:
            with st.container(border=True):
                st.markdown(f"**🟡 Предупреждения ({len(warnings)})**")
                for w in warnings:
                    st.markdown(f"- {w}")
        if not errors and not warnings:
            st.success("✅ Готово к генерации КП")

        if st.button(
            "🚀 Сгенерировать КП",
            disabled=bool(errors),
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

        st.divider()
        st.image("assets/tenzosila_logo_small.png", width=120)
        st.caption("© ООО «ТПК «Тензосила», Воронеж")

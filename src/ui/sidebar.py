"""Sticky-sidebar: итоги, сроки, валидация, кнопка генерации, брендовый футер."""
from __future__ import annotations

import streamlit as st

from src.generators.kp_generator import build_filename, generate_kp
from src.utils.format import fmt_rub


def render_sidebar(
    state: dict,
    spec_items: list[dict],
    errors: list[str],
    warnings: list[str],
    totals: dict,
    payment_preview: str,
    term_days: int,
    prices: dict,
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

        # Кнопка генерации DOCX
        _render_generate_button(state, spec_items, errors, prices)

        st.divider()
        st.image("assets/tenzosila_logo_small.png", width=120)
        st.caption("© ООО «ТПК «Тензосила», Воронеж")


def _render_generate_button(
    state: dict, spec_items: list[dict], errors: list[str], prices: dict
) -> None:
    """Кнопка «Сгенерировать КП» → реальный download_button с DOCX-байтами."""
    label = "📄 Сгенерировать КП"
    mime = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    if errors:
        st.button(
            label,
            disabled=True,
            help="Сначала устраните ошибки валидации",
            width="stretch",
            type="primary",
        )
        return

    if not spec_items:
        st.button(
            label,
            disabled=True,
            help="Спецификация пуста — выберите модель",
            width="stretch",
            type="primary",
        )
        return

    try:
        docx_bytes = generate_kp(dict(state), prices)
        st.download_button(
            label,
            data=docx_bytes,
            file_name=build_filename(dict(state)),
            mime=mime,
            width="stretch",
            type="primary",
        )
    except Exception as e:  # noqa: BLE001 — UI должен показать ошибку, не падать
        st.button(
            label,
            disabled=True,
            help=f"Ошибка генерации: {e}",
            width="stretch",
            type="primary",
        )
        st.error(f"Ошибка генерации DOCX: {e}")

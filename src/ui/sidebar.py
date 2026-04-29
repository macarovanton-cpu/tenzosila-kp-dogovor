"""Sticky-sidebar: итоги, сроки, валидация, кнопка генерации, брендовый футер."""
from __future__ import annotations

from datetime import timedelta

import streamlit as st

from src.config import VAT_RATE
from src.generators.kp_generator import build_filename, generate_kp
from src.term_days import TermDaysTooSmallError
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
        st.subheader(":material/receipt_long: Итоги")

        with st.container(border=True):
            st.metric("ИТОГО с НДС", fmt_rub(totals["with_vat"]))
            st.markdown(
                "<div style='font-size: 1.4rem; font-weight: 400; "
                "margin-top: -10px; opacity: 0.85;'>"
                f"Без НДС: <strong>{fmt_rub(totals['without_vat'])}</strong></div>",
                unsafe_allow_html=True,
            )
        st.caption(
            f"в т.ч. НДС {int(VAT_RATE * 100)}%: {fmt_rub(totals['vat'])}",
            help="Текущая ставка НДС в РФ с 01.01.2026 — 22%. "
                 "Задаётся через VAT_RATE в src/config.py.",
        )

        st.divider()

        valid_until = state["kp_date"] + timedelta(
            days=int(state["kp_valid_days"])
        )
        st.markdown(
            f":material/event_available: **Действует до:** "
            f"{valid_until.strftime('%d.%m.%Y')}"
        )
        st.markdown(
            f":material/build: **Срок изготовления:** {term_days} раб. дн."
        )

        st.divider()

        # Статус валидации — наверху, чтобы менеджер сразу видел незаполненное
        if errors:
            with st.container(border=True):
                st.markdown(
                    f"**:material/error: Ошибки валидации ({len(errors)})**"
                )
                for e in errors:
                    st.markdown(f"- {e}")
        if warnings:
            with st.container(border=True):
                st.markdown(
                    f"**:material/warning: Предупреждения ({len(warnings)})**"
                )
                for w in warnings:
                    st.markdown(f"- {w}")
        if not errors and not warnings:
            st.success(
                "Готово к генерации КП",
                icon=":material/check_circle:",
            )

        st.divider()

        if payment_preview:
            with st.expander(
                "Условия оплаты",
                icon=":material/credit_card:",
                expanded=False,
            ):
                st.markdown(payment_preview)

        # Кнопка генерации DOCX
        _render_generate_button(state, spec_items, errors, prices)

        st.divider()
        st.image("assets/tenzosila_logo_small.png", width=120)
        st.caption("© ООО «ТПК «Тензосила», Воронеж")


def _render_generate_button(
    state: dict, spec_items: list[dict], errors: list[str], prices: dict
) -> None:
    """Кнопка «Сгенерировать КП» → реальный download_button с DOCX-байтами."""
    label = ":material/description: Сгенерировать КП"
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
    except TermDaysTooSmallError as exc:
        d = exc.details
        msg = (
            f"Общий срок {d['total']} дн. меньше минимума {d['min']} дн. "
            f"(фикс {d['fixed_total']} = монтаж {d['install']} + "
            f"доставка {d['delivery']} + поверка {d['verification']}; "
            f"плюс по 1 дню на каждую вариативную роль: {d['variable_count']}). "
            "Увеличьте срок проекта в шапке."
        )
        st.button(
            label,
            disabled=True,
            help=msg,
            width="stretch",
            type="primary",
        )
        st.error(msg)
    except Exception as e:  # noqa: BLE001 — UI должен показать ошибку, не падать
        st.button(
            label,
            disabled=True,
            help=f"Ошибка генерации: {e}",
            width="stretch",
            type="primary",
        )
        st.error(f"Ошибка генерации DOCX: {e}")

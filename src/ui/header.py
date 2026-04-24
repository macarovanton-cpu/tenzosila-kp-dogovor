"""Шапка КП: клиент, лид, дата, сроки."""
from __future__ import annotations

from datetime import timedelta

import streamlit as st


def render_header(state: dict) -> None:
    st.subheader("Клиент и параметры КП")

    row1 = st.columns([2, 1, 1, 1])
    with row1[0]:
        st.text_input("Клиент (полное наименование)", key="client_name")
    with row1[1]:
        st.text_input("ИНН", key="client_inn")
    with row1[2]:
        st.text_input("Номер лида Битрикс", key="lead_number")
    with row1[3]:
        st.text_input("Менеджер", key="manager_name")

    row2 = st.columns([2, 1, 1, 1])
    with row2[0]:
        st.text_input("Контактное лицо", key="client_contact")
    with row2[1]:
        st.text_input("E-mail", key="client_email")
    with row2[2]:
        st.text_input("Телефон", key="client_phone")
    with row2[3]:
        st.date_input("Дата КП", key="kp_date")

    row3 = st.columns([1, 1, 1, 3])
    with row3[0]:
        st.number_input(
            "Срок действия КП, дней",
            min_value=1, max_value=90,
            step=1,
            key="kp_valid_days",
        )
    with row3[1]:
        st.number_input(
            "Срок исполнения, дней",
            min_value=1, max_value=180,
            step=1,
            key="total_term_days",
        )
    with row3[2]:
        valid_until = state["kp_date"] + timedelta(days=int(state["kp_valid_days"]))
        st.caption(f"Действует до: **{valid_until.strftime('%d.%m.%Y')}**")

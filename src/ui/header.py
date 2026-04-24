"""Шапка КП: клиент, менеджер, лид, дата, сроки."""
from __future__ import annotations

from datetime import timedelta

import streamlit as st

from src.data_loader import get_default_manager_id, get_manager_by_id


def render_header(state: dict, managers: dict) -> None:
    st.subheader("Клиент и параметры КП")

    # Дефолт менеджера при первом запуске
    if not state.get("manager_id"):
        state["manager_id"] = get_default_manager_id(managers)

    row1 = st.columns([2, 1, 1, 1])
    with row1[0]:
        st.text_input("Клиент (полное наименование)", key="client_name")
    with row1[1]:
        st.text_input("ИНН", key="client_inn")
    with row1[2]:
        st.text_input("Номер лида Битрикс", key="lead_number")
    with row1[3]:
        st.date_input("Дата КП", key="kp_date")

    row2 = st.columns([2, 3])
    with row2[0]:
        manager_ids = [m["id"] for m in managers.get("managers", [])]
        manager_labels = {m["id"]: m.get("full_name", m["id"]) for m in managers.get("managers", [])}
        st.selectbox(
            "Менеджер",
            manager_ids,
            format_func=lambda mid: manager_labels.get(mid, mid),
            key="manager_id",
        )
        mgr = get_manager_by_id(managers, state["manager_id"])
        if mgr:
            st.caption(
                f"{mgr.get('position', '')} · 📞 {mgr.get('phone', '')} · "
                f"✉️ {mgr.get('email', '')}"
            )

    with row2[1]:
        sub = st.columns(3)
        with sub[0]:
            st.number_input(
                "Срок действия КП, дней",
                min_value=1, max_value=90,
                step=1,
                key="kp_valid_days",
            )
        with sub[1]:
            st.number_input(
                "Срок исполнения, дней",
                min_value=1, max_value=180,
                step=1,
                key="total_term_days",
            )
        with sub[2]:
            valid_until = state["kp_date"] + timedelta(days=int(state["kp_valid_days"]))
            st.caption(f"Действует до: **{valid_until.strftime('%d.%m.%Y')}**")

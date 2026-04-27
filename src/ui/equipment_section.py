"""Оборудование: датчик, индикатор, кабель, гарантия. Настил/подшивка — в секции «Конструкция»."""
from __future__ import annotations

import streamlit as st

from src.data_loader import (
    get_indicator_alternatives,
    get_line_defaults,
    get_sensor_alternatives,
)


def render_equipment_section(state: dict, models_json: dict) -> None:
    st.subheader(":material/cable: Оборудование")
    st.caption("Датчики, индикатор, гарантия")

    line = state.get("model_line", "С")
    ld = get_line_defaults(models_json, line)

    # Гарантия
    default_warr = int(ld.get("default_warranty_months", 36))
    warr_opts = [12, 18, 24, 36, 48, 60]
    if state.get("warranty_months") not in warr_opts:
        state["warranty_months"] = default_warr

    cols = st.columns(2)
    with cols[0]:
        st.selectbox(
            "Гарантия, мес.",
            warr_opts,
            key="warranty_months",
        )

    # Кабель
    with cols[1]:
        st.number_input(
            "Длина кабеля, м",
            min_value=5, max_value=100, step=5,
            key="cable_m",
        )

    # Датчик
    sensors = get_sensor_alternatives(models_json)
    sensor_ids = [s["id"] for s in sensors]
    sensor_labels = {s["id"]: s["label"] for s in sensors}
    if state.get("sensor_id") not in sensor_ids:
        default = next((s["id"] for s in sensors if s.get("is_default")), sensor_ids[0])
        state["sensor_id"] = default

    cols2 = st.columns(2)
    with cols2[0]:
        st.selectbox(
            "Датчики",
            sensor_ids,
            format_func=lambda sid: sensor_labels.get(sid, sid),
            key="sensor_id",
        )

    # Индикатор
    indicators = get_indicator_alternatives(models_json)
    ind_ids = [i["id"] for i in indicators]
    ind_labels = {i["id"]: i["label"] for i in indicators}
    if state.get("indicator_id") not in ind_ids:
        default = next((i["id"] for i in indicators if i.get("is_default")), ind_ids[0])
        state["indicator_id"] = default

    with cols2[1]:
        st.selectbox(
            "Индикатор",
            ind_ids,
            format_func=lambda iid: ind_labels.get(iid, iid),
            key="indicator_id",
        )

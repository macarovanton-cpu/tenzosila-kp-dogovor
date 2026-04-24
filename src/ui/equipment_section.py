"""Оборудование: настил, датчик, индикатор, кабель, гарантия."""
from __future__ import annotations

import streamlit as st

from src.data_loader import (
    get_indicator_alternatives,
    get_line_defaults,
    get_sensor_alternatives,
)


def render_equipment_section(state: dict, models_json: dict) -> None:
    st.subheader("2. Оборудование и гарантия")

    line = state.get("model_line", "С")
    ld = get_line_defaults(models_json, line)

    cols = st.columns(2)

    # Настил
    with cols[0]:
        deck_min = int(ld.get("underlining_mm_min", 3))
        deck_max = int(ld.get("underlining_mm_max", 6))
        deck_default = int(ld.get("underlining_mm", deck_min))
        if state.get("deck_mm") is None or not (deck_min <= state["deck_mm"] <= deck_max):
            state["deck_mm"] = deck_default
        st.slider(
            "Толщина настила, мм",
            min_value=deck_min,
            max_value=deck_max,
            step=1,
            key="deck_mm",
        )

    # Гарантия
    with cols[1]:
        default_warr = int(ld.get("default_warranty_months", 36))
        warr_opts = [12, 18, 24, 36, 48, 60]
        if state.get("warranty_months") not in warr_opts:
            state["warranty_months"] = default_warr
        st.selectbox(
            "Гарантия, мес.",
            warr_opts,
            key="warranty_months",
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

    # Кабель
    st.number_input(
        "Длина кабеля, м",
        min_value=5, max_value=100, step=5,
        key="cable_m",
    )

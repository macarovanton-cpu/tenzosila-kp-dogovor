"""Секция «Конструкция весов»: балки, центральные балки, настил, подшивка."""
from __future__ import annotations

import streamlit as st

from src.data_loader import get_line_defaults, get_model_by_id
from src.filters import calc_default_deck_mm


def render_construction_section(state: dict, models_json: dict) -> None:
    """Expander «⚙️ Конструкция».

    Автогенерируемое описание (read-only) + 6 редактируемых полей.
    На цену не влияет — только для DOCX-спецификации.
    """
    line = state.get("model_line", "С")
    ld = get_line_defaults(models_json, line)
    model = get_model_by_id(models_json, state.get("model_id", ""))
    is_rail = ld.get("default_construction_type") == "Колейная"

    # Первичная инициализация при пустом state (а также fallback после сброса)
    _ensure_construction_defaults(state, model, ld)

    with st.expander("⚙️ Конструкция", expanded=False):
        st.markdown(_build_description_md(state, is_rail))

        cols = st.columns(2)
        with cols[0]:
            st.text_input("Профиль", key="construction_beam")
            st.text_input(
                "Центральная балка",
                key="construction_center_beam",
                disabled=is_rail,
            )
            st.selectbox(
                "Настил, мм",
                [6, 8, 10],
                key="construction_deck_mm",
                help="Верхний рифлёный лист для проезда машин. 6 мм для ≤60 т, 8 мм для >60 т",
            )
        with cols[1]:
            st.number_input(
                "Кол-во профилей",
                min_value=1, max_value=20, step=1,
                key="construction_beam_count",
            )
            st.number_input(
                "Кол-во центральных балок",
                min_value=0, max_value=10, step=1,
                key="construction_center_beam_count",
                disabled=is_rail,
            )
            st.selectbox(
                "Подшивка, мм",
                [3, 4, 5],
                key="construction_underlining_mm",
                help="Нижний гладкий лист, защита снизу от коррозии",
            )


def _ensure_construction_defaults(state: dict, model: dict | None, ld: dict) -> None:
    """Если construction_* ещё пустые — заполнить из defaults текущей модели/линейки."""
    if not state.get("construction_beam"):
        reset_construction(state, model, ld)


def reset_construction(state: dict, model: dict | None, ld: dict) -> None:
    """Выставить construction_* из defaults текущих (модель + линейка)."""
    is_rail = ld.get("default_construction_type") == "Колейная"
    state["construction_beam"] = str(
        (model or {}).get("beam_profile") or "Двутавр 25Б1"
    )
    state["construction_beam_count"] = int(ld.get("longitudinal_beams_count") or 4)
    state["construction_center_beam"] = "" if is_rail else str(
        ld.get("center_reinforcement") or ""
    )
    state["construction_center_beam_count"] = 0 if is_rail else int(
        ld.get("default_center_beam_count") or 0
    )
    max_t = int((model or {}).get("max_load_t") or 60)
    state["construction_deck_mm"] = calc_default_deck_mm(max_t)
    state["construction_underlining_mm"] = int(ld.get("underlining_mm") or 4)


def _build_description_md(state: dict, is_rail: bool) -> str:
    """Markdown-описание конструкции. Без center_beam-части для Ф/ФЛ."""
    beam = state.get("construction_beam", "") or "—"
    beam_cnt = state.get("construction_beam_count", 0) or 0
    deck = state.get("construction_deck_mm", 0) or 0
    under = state.get("construction_underlining_mm", 0) or 0
    if is_rail:
        return (
            f"> **Конструкция колейная:** {beam} {beam_cnt} шт., "
            f"лист настила {deck} мм рифлёный, "
            f"нижний подшив {under} мм"
        )
    cbeam = state.get("construction_center_beam", "") or "—"
    cbeam_cnt = state.get("construction_center_beam_count", 0) or 0
    return (
        f"> **Конструкция сплошная:** {beam} {beam_cnt} шт., "
        f"{cbeam} {cbeam_cnt} шт., "
        f"лист настила {deck} мм рифлёный, "
        f"нижний подшив {under} мм"
    )

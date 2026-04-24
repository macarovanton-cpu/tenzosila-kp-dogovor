"""Каскад выбора модели: линейка → нагрузка → длина + карточка ТХ + слайдер цены."""
from __future__ import annotations

import streamlit as st

from src.config import LINES
from src.data_loader import (
    get_line_defaults,
    get_model_by_id,
    get_price_by_model_id,
)
from src.filters import (
    available_lengths,
    available_max_loads,
    model_id_from_cascade,
)
from src.pricing import (
    color_code,
    get_model_slider_params,
    percent_to_retail,
)
from src.state import on_cascade_change


def render_model_section(state: dict, models_json: dict, prices: dict) -> None:
    st.subheader("1. Модель автовесов")

    # Линейка
    cols = st.columns(3)
    with cols[0]:
        st.selectbox(
            "Линейка",
            LINES,
            key="model_line",
            on_change=on_cascade_change,
        )
    line = state["model_line"]

    # Максимальная нагрузка — фильтр по наличию в prices
    max_opts = available_max_loads(models_json, line, prices)
    if not max_opts:
        st.error(f"Для линейки {line} нет моделей в прайсе.")
        return
    if state.get("model_max") not in max_opts:
        st.session_state["model_max"] = max_opts[0]
    with cols[1]:
        st.selectbox(
            "Макс. нагрузка, т",
            max_opts,
            key="model_max",
            on_change=on_cascade_change,
        )

    # Длина
    len_opts = available_lengths(models_json, line, int(state["model_max"]), prices)
    if not len_opts:
        st.error("Для выбранной комбинации нет доступных длин в прайсе.")
        return
    if state.get("model_length") not in len_opts:
        st.session_state["model_length"] = len_opts[0]
    with cols[2]:
        st.selectbox(
            "Длина платформы, м",
            len_opts,
            key="model_length",
            on_change=on_cascade_change,
        )

    # Синхронизируем model_id (на случай, если колбэк не сработал)
    state["model_id"] = model_id_from_cascade(
        state["model_line"], int(state["model_max"]), int(state["model_length"])
    )

    price = get_price_by_model_id(prices, state["model_id"])
    if price is None:
        st.error(
            f"Модель «{state['model_id']}» отсутствует в прайсе. "
            "Запросите цены у производства."
        )
        return

    model = get_model_by_id(models_json, state["model_id"])
    _render_model_card(model, models_json, line)

    _render_model_price_slider(state, price)


def _render_model_card(model: dict | None, models_json: dict, line: str) -> None:
    if model is None:
        st.warning("Характеристики модели не найдены в справочнике.")
        return
    ld = get_line_defaults(models_json, line)
    al = model.get("axle_loads_t", {})
    md = (
        f"**{model.get('full_name', '')}** — {ld.get('description', '')}\n\n"
        f"| Параметр | Значение |\n|---|---|\n"
        f"| Тип платформы | {ld.get('platform_type', '—')} |\n"
        f"| Секций | {model.get('sections', '—')} |\n"
        f"| Датчиков | {model.get('sensors_count', '—')} |\n"
        f"| Масса весов, кг | {model.get('mass_kg', '—')} |\n"
        f"| Балка | {model.get('beam_profile', '—')} |\n"
        f"| Настил по умолчанию, мм | {model.get('deck_default_mm', '—')} |\n"
        f"| Мин. нагрузка, т | {model.get('min_load_t', '—')} |\n"
        f"| Цена поверки, кг | {model.get('verification_division_kg', '—')} |\n"
        f"\n**Осевые нагрузки:** 1-ось {al.get('single', '—')} т · "
        f"2 оси {al.get('double', '—')} т · "
        f"3 оси {al.get('triple', '—')} т · "
        f"4 оси {al.get('quad', '—')} т"
    )
    st.info(md)
    if model.get("data_incomplete"):
        st.warning(
            "⚠️ Данные модели неполные (`data_incomplete: true`) — "
            "уточните ТХ у производства."
        )


def _render_model_price_slider(state: dict, price: dict) -> None:
    params = get_model_slider_params(price)
    current = state.get("model_price") or params.default_v
    value = st.slider(
        "Цена модели, ₽ (с НДС 22%)",
        min_value=params.min_v,
        max_value=params.max_v,
        value=int(current),
        step=params.step,
        key=f"model_price_slider__{state['model_id']}",
    )
    state["model_price"] = int(value)

    # Конфликт со spec-таблицей: пользователь руками правил цену позиции,
    # но дёрнул слайдер — покажем warning + кнопку сброса в sidebar.
    model_id = state["model_id"]
    ov = state.get("spec_items_overrides", {}).get(model_id, {})
    if ov.get("price") is not None and int(ov["price"]) != int(value):
        state["spec_override_conflict"] = model_id
    elif state.get("spec_override_conflict") == model_id:
        state.pop("spec_override_conflict", None)

    tag = color_code(int(value), params.retail, params.dealer)
    pct = percent_to_retail(int(value), params.retail)
    sign = "+" if pct >= 0 else ""
    st.caption(
        f"{tag} Дилер: {params.dealer:,} ₽ · Розница: {params.retail:,} ₽ · "
        f"Выбрано: {int(value):,} ₽ ({sign}{pct:.1f}% к рознице)".replace(",", " ")
    )

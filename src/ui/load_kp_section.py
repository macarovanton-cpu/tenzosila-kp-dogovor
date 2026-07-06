"""Блок «Открыть прошлый КП»: загрузка сохранённого снапшота обратно в конфигуратор.

Сеть дёргается ТОЛЬКО по кнопке (иначе каждый rerun страницы КП бил бы в Supabase
и висел при недоступности базы). Все пути догружают полную строку через
get_kp_by_number — list_recent_kps/search_kps_by_contractor не содержат data JSONB.
"""
from __future__ import annotations

import streamlit as st

from src.storage.supabase_client import (
    StorageError,
    get_kp_by_number,
    list_recent_kps,
    search_kps_by_contractor,
)

_SPACER = "<div style='height: 1.75rem'></div>"


def _label(row: dict) -> str:
    price = f"{row.get('total_price', 0):,}".replace(",", " ")
    return (
        f"{row.get('kp_number', '')} — {row.get('client_name', '')} — "
        f"{row.get('model_id', '')} — {price} ₽"
    )


def _stage_restore(kp_number: str) -> None:
    """Догрузить полную строку по номеру и поставить снапшот в очередь на применение."""
    try:
        row = get_kp_by_number(kp_number.strip())
    except StorageError as e:
        st.warning(f"Ошибка загрузки КП: {e}")
        return
    if row is None:
        st.warning(f"КП «{kp_number}» не найден в базе.")
        return
    # Применяется на следующем run в consume-точке main() ДО виджетов конфигуратора.
    st.session_state["_kp_restore_row"] = row
    st.session_state["_kp_restore_pending"] = True
    st.rerun()


def _fetch_list(contractor: str) -> None:
    """Сетевой запрос списка КП (по кнопке) → в session_state."""
    try:
        rows = (
            search_kps_by_contractor(contractor)
            if contractor
            else list_recent_kps(limit=50)
        )
        st.session_state["_load_kp_rows"] = rows
        if not rows:
            st.info("Ничего не найдено.")
    except StorageError as e:
        st.session_state["_load_kp_rows"] = []
        st.warning(f"Не удалось загрузить список КП: {e}")


def _render_overwrite_warning() -> None:
    """Предупреждение: текущий номер совпадает с загруженным → перезапись оригинала."""
    loaded = st.session_state.get("_kp_loaded_number")
    if loaded and st.session_state.get("kp_number") == loaded:
        st.warning(
            f"Загружен КП «{loaded}». Смените номер (например «{loaded}.1»), "
            "иначе при сохранении оригинал будет перезаписан.",
            icon=":material/warning:",
        )


def render_load_kp_section() -> None:
    _render_overwrite_warning()

    with st.expander(
        "Открыть прошлый КП для редактирования",
        icon=":material/folder_open:",
        expanded=False,
    ):
        st.caption(
            "Восстановит состояние конфигуратора из сохранённого КП. "
            "Сохраняйте под НОВЫМ номером (напр. 123.1), чтобы не перезаписать оригинал."
        )

        # Список по кнопке (без сети на каждом ререндере страницы).
        c1, c2 = st.columns([3, 1])
        with c1:
            contractor = st.text_input(
                "Поиск по контрагенту (пусто — последние 50)",
                key="load_kp_contractor", placeholder="Ромашка",
            )
        with c2:
            st.markdown(_SPACER, unsafe_allow_html=True)
            if st.button("Показать", key="load_kp_list_btn", width="stretch"):
                _fetch_list(contractor.strip())

        rows = st.session_state.get("_load_kp_rows", [])
        if rows:
            by_label = {_label(r): r for r in rows}
            chosen = st.selectbox(
                "КП из базы", ["— выбрать —", *by_label.keys()], key="load_kp_select"
            )
            if st.button(
                "Загрузить выбранный", key="load_kp_pick_btn",
                disabled=chosen == "— выбрать —", width="stretch", type="primary",
            ):
                _stage_restore(by_label[chosen]["kp_number"])

        st.divider()
        # Прямой ввод номера (сеть только по «Найти»).
        m1, m2 = st.columns([3, 1])
        with m1:
            manual = st.text_input(
                "…или номер вручную", key="load_kp_num", placeholder="КП-2026-001",
            )
        with m2:
            st.markdown(_SPACER, unsafe_allow_html=True)
            if st.button("Найти", key="load_kp_find_btn", width="stretch"):
                if manual.strip():
                    _stage_restore(manual.strip())
                else:
                    st.warning("Введите номер КП.")

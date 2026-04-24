"""Инициализация st.session_state и колбэки каскада модели."""
from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from src.config import (
    DEFAULT_KP_VALID_DAYS,
    DEFAULT_TOTAL_TERM_DAYS,
)
from src.data_loader import get_line_defaults, get_model_by_id, load_models
from src.filters import model_id_from_cascade
from src.ui.construction_section import reset_construction


def initial_state() -> dict[str, Any]:
    """Построить dict с дефолтными значениями для session_state."""
    return {
        # Метаданные КП
        "kp_date": date.today(),
        "kp_valid_days": DEFAULT_KP_VALID_DAYS,
        "total_term_days": DEFAULT_TOTAL_TERM_DAYS,
        "lead_number": "",
        # Менеджер — дефолт проставит header.py через get_default_manager_id
        "manager_id": "",
        # Клиент
        "client_name": "",
        # Модель (каскад)
        "model_line": "С",
        "model_max": 60,
        "model_length": 18,
        "model_id": "vesta-с-60-18",
        "model_price": None,
        # Оборудование
        "sensor_id": "zemic_dhm9b_30t",
        "indicator_id": "titan_3cs",
        "cable_m": 20,
        "warranty_months": 36,
        # Конструкция весов (заполняется при первом рендере construction_section)
        "construction_beam": "",
        "construction_beam_count": 0,
        "construction_center_beam": "",
        "construction_center_beam_count": 0,
        "construction_deck_mm": 6,
        "construction_underlining_mm": 4,
        # Опции:
        # {option_key: {"enabled": bool, "price": int, "qty": int,
        #               "customer_side": bool, "is_on_request": bool,
        #               "retail": int, "dealer_is_synthetic": bool, "block": str}}
        "options": {},
        # Ручные правки позиций спецификации (spec_items):
        # {item_key: {"qty": int|None, "price": int|None}}
        # item_key = model_id для базовой модели, option_key для опций.
        "spec_items_overrides": {},
        # Оплата
        "payment_preset_id": "split_by_items",
        "payment_percents": {},
        "payment_days": 5,
        "payment_custom_text": "",
        # Для split_by_items: {group_id: {"prepay": int, "postpay": int}}
        "payment_split_state": {},
    }


def init_state() -> None:
    """Выставить дефолты для всех ключей, не трогая уже существующие."""
    for k, v in initial_state().items():
        st.session_state.setdefault(k, v)


def reset_options() -> None:
    """Очистить все выбранные опции (вызывается при смене модели)."""
    st.session_state["options"] = {}


def reset_spec_overrides() -> None:
    """Очистить ручные правки qty/price в spec-таблице (при смене модели)."""
    st.session_state["spec_items_overrides"] = {}


def on_cascade_change() -> None:
    """Колбэк для 3-х selectbox каскада (линейка/нагрузка/длина).

    Пересобирает model_id; если он изменился — сбрасывает опции, цену модели,
    конструкцию и ручные правки спецификации.
    """
    line = st.session_state.get("model_line", "С")
    mx = st.session_state.get("model_max", 60)
    ln = st.session_state.get("model_length", 18)
    new_id = model_id_from_cascade(line, int(mx), int(ln))
    if new_id != st.session_state.get("model_id"):
        st.session_state["model_id"] = new_id
        st.session_state["model_price"] = None
        reset_options()
        reset_spec_overrides()
        # Сброс конструкции на defaults новой модели
        models_json = load_models()
        model = get_model_by_id(models_json, new_id)
        ld = get_line_defaults(models_json, line)
        reset_construction(st.session_state, model, ld)

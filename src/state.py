"""Инициализация st.session_state и колбэки каскада модели."""
from __future__ import annotations

import os
from datetime import date
from typing import Any

import streamlit as st

from src.config import DEFAULT_KP_VALID_DAYS
from src.data_loader import get_line_defaults, get_model_by_id, load_models
from src.filters import model_id_from_cascade
from src.ui.construction_section import reset_construction


def _default_kp_date() -> date:
    # Только для e2e/visual-regression: фиксируем дату через env-vars,
    # чтобы baseline-снимки DOCX были детерминированными.
    fake = os.getenv("TENZOSILA_FAKE_DATE")
    if fake:
        try:
            return date.fromisoformat(fake)
        except ValueError:
            pass
    return date.today()


def initial_state() -> dict[str, Any]:
    """Построить dict с дефолтными значениями для session_state."""
    return {
        # Метаданные КП
        "kp_date": _default_kp_date(),
        "kp_valid_days": DEFAULT_KP_VALID_DAYS,
        # Срок проекта: дефолт пересчитывается в header по составу spec_items.
        "total_term_days": None,
        "kp_number": "",
        # Менеджер — дефолт проставит header.py через get_default_manager_id
        "manager_id": "",
        # Клиент
        "client_name": "",
        # Модель (каскад)
        "model_line": "С",
        "model_max": 60,
        "model_length": 18,
        "platform_width_m": 3.0,
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
        # Метрология
        "is_dual_range": False,  # чекбокс UI: одно/двухдиапазонный режим
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
        # Параметры новых вариантов оплаты (v0.4 payment_terms.json).
        # postpay у V1/V2 derived (st.metric), не хранится в state.
        "payment_v1_prepay": 50,
        "payment_v2_prepay": 30,
        "payment_v2_preship": 40,
        # У V3 семантика days другая (срок постоплаты, не аванса) — отдельный ключ.
        "payment_v3_days": 15,
        "payment_v3_trigger_id": "after_installation",
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


def on_platform_width_change() -> None:
    """Колбэк смены ширины: пересчитать цену модели без сброса опций."""
    model_id = st.session_state.get("model_id")
    st.session_state["model_price"] = None
    if not model_id:
        return

    overrides = st.session_state.setdefault("spec_items_overrides", {})
    ov = overrides.get(model_id, {}) or {}
    ov.pop("price", None)
    if ov:
        overrides[model_id] = ov
    else:
        overrides.pop(model_id, None)


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
        # Сброс режима диапазона: менеджер сам решит, включать ли заново
        st.session_state["is_dual_range"] = False
        # Сброс ручного срока — следуем за дефолтом по новому составу
        st.session_state.pop("total_term_days_user_set", None)
        st.session_state["total_term_days"] = None
        # Сброс конструкции на defaults новой модели
        models_json = load_models()
        model = get_model_by_id(models_json, new_id)
        ld = get_line_defaults(models_json, line)
        reset_construction(st.session_state, model, ld)

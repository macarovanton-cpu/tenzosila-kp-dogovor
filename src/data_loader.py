"""Загрузчики справочников с кэшированием через @st.cache_data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from src.config import (
    MANAGERS_JSON,
    MODELS_JSON,
    OPTIONS_META_JSON,
    PAYMENT_TERMS_JSON,
    PRICES_JSON,
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(ttl=3600)
def load_models() -> dict[str, Any]:
    """Загрузить models.json: _meta, equipment_defaults, line_defaults, models[]."""
    return _read_json(MODELS_JSON)


@st.cache_data(ttl=3600)
def load_prices() -> dict[str, Any]:
    """Загрузить prices.json: _meta, models{}, options{}."""
    return _read_json(PRICES_JSON)


@st.cache_data(ttl=3600)
def load_payment_terms() -> dict[str, Any]:
    """Загрузить payment_terms.json: _meta, default_preset_id, presets[]."""
    return _read_json(PAYMENT_TERMS_JSON)


@st.cache_data(ttl=3600)
def load_options_meta() -> dict[str, Any]:
    """Загрузить options.json — текстовые описания пакетов ОРИОН, фундаментов и пр."""
    return _read_json(OPTIONS_META_JSON)


@st.cache_data(ttl=3600)
def load_managers() -> dict[str, Any]:
    """Загрузить managers.json: _meta, default_manager_id, managers[]."""
    return _read_json(MANAGERS_JSON)


# --- Хелперы доступа ---


def get_model_by_id(models_json: dict, model_id: str) -> dict | None:
    """Найти модель в models.json по id (учитывает кириллицу)."""
    for m in models_json.get("models", []):
        if m.get("id") == model_id:
            return m
    return None


def get_dual_range(models_json: dict, model_id: str) -> dict | None:
    """Вернуть блок dual_range модели или None, если модель не поддерживает
    двухдиапазонный режим (или не найдена)."""
    model = get_model_by_id(models_json, model_id)
    return model.get("dual_range") if model else None


def get_price_by_model_id(prices: dict, model_id: str) -> dict | None:
    """Вернуть запись цен модели: {retail, dealer_ru, dealer_discount_pct}."""
    return prices.get("models", {}).get(model_id)


def get_option_price(prices: dict, option_key: str) -> dict | None:
    """Вернуть запись опции из prices.options."""
    return prices.get("options", {}).get(option_key)


def get_line_defaults(models_json: dict, line: str) -> dict:
    """Вернуть line_defaults[line] или пустой dict."""
    return models_json.get("line_defaults", {}).get(line, {})


def get_sensor_alternatives(models_json: dict) -> list[dict]:
    return (
        models_json.get("equipment_defaults", {})
        .get("sensor", {})
        .get("alternatives", [])
    )


def get_indicator_alternatives(models_json: dict) -> list[dict]:
    return (
        models_json.get("equipment_defaults", {})
        .get("indicator", {})
        .get("alternatives", [])
    )


def get_manager_by_id(managers: dict, manager_id: str) -> dict | None:
    """Найти менеджера в managers.json по id."""
    for m in managers.get("managers", []):
        if m.get("id") == manager_id:
            return m
    return None


def get_default_manager_id(managers: dict) -> str:
    """Вернуть id менеджера по умолчанию (из поля default_manager_id)."""
    default_id = managers.get("default_manager_id", "")
    if default_id:
        return str(default_id)
    # Фолбэк: первый менеджер с is_default=true, иначе первый в списке.
    lst = managers.get("managers", [])
    for m in lst:
        if m.get("is_default"):
            return str(m.get("id", ""))
    if lst:
        return str(lst[0].get("id", ""))
    return ""

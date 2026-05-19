"""Инициализация и хелперы session_state для страницы Договор."""
from __future__ import annotations

from typing import Any

import streamlit as st


_CONTRACT_DEFAULTS: dict[str, Any] = {
    "requisites": {},
    "specification": {},
    "manual": {
        "contract_number": "",
        "contract_date": None,
        "object_address": "",
        "spec_number": "1",
    },
    "uploads": {
        "kp": None,
        "card": None,
    },
    "ai_raw": None,
}


def init_contract_state() -> None:
    """Идемпотентно создать namespace ``st.session_state["contract"]``."""
    st.session_state.setdefault("contract", {})
    cs = st.session_state["contract"]
    for key, default in _CONTRACT_DEFAULTS.items():
        if isinstance(default, dict):
            cs.setdefault(key, default.copy())
        else:
            cs.setdefault(key, default)


def set_extracted_data(raw: dict) -> None:
    """Записать результат AI-extraction в namespace и обновить widget-ключи."""
    cs = st.session_state["contract"]
    cs["requisites"] = {k: (v or "") for k, v in raw.get("requisites", {}).items()}
    cs["specification"] = {k: (v or "") for k, v in raw.get("specification", {}).items()}
    cs["ai_raw"] = raw
    for key, val in cs["requisites"].items():
        st.session_state[f"w_{key}"] = val
    for key, val in cs["specification"].items():
        st.session_state[f"w_{key}"] = val


def sync_field(section: str, key: str) -> None:
    """on_change callback: widget -> namespace."""
    wkey = f"w_{key}"
    st.session_state["contract"][section][key] = st.session_state.get(wkey, "")


def sync_manual_field(key: str) -> None:
    """on_change callback для manual-полей."""
    wkey = f"w_{key}"
    st.session_state["contract"]["manual"][key] = st.session_state.get(wkey, "")


def collect_for_template() -> dict[str, str]:
    """Собрать плоский dict для docxtpl из namespace (requisites + specification)."""
    cs = st.session_state["contract"]
    data: dict[str, str] = {}
    data.update(cs.get("requisites", {}))
    data.update(cs.get("specification", {}))
    return data


def is_extracted() -> bool:
    """Есть ли данные AI-извлечения."""
    return bool(st.session_state.get("contract", {}).get("ai_raw"))

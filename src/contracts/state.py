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
    "generated": None,
    "kp_snapshot": {},
    "payment_lines": [],
    "kp_payment_snapshot": {},
    "attachments": {
        "build_task_path": "",
        "build_task_source": "auto",
        "control_sheet_path": "",
        "include_control_sheet": False,
    },
    "flags": {
        "winter_concrete": False,
        "winter_surcharge": False,
        "winter_surcharge_amount": 200000,
    },
    "scope_overrides": {
        "foundation_scope": None,
        "installation_scope": None,
        "verification_scope": None,
        "orion_poles_scope": None,
    },
}


def init_contract_state() -> None:
    """Идемпотентно создать namespace ``st.session_state["contract"]``."""
    st.session_state.setdefault("contract", {})
    cs = st.session_state["contract"]
    for key, default in _CONTRACT_DEFAULTS.items():
        if isinstance(default, dict):
            cs.setdefault(key, default.copy())
        elif isinstance(default, list):
            cs.setdefault(key, default.copy())
        else:
            cs.setdefault(key, default)
    flags = cs.setdefault("flags", {})
    flags.setdefault("winter_concrete", False)
    flags.setdefault("winter_surcharge", bool(flags.get("winter_concrete", False)))
    flags.setdefault("winter_surcharge_amount", 200000)


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
    spec = cs.get("specification", {})
    data.update({k: v for k, v in spec.items() if k != "items"})
    return data


def set_specification(spec: dict[str, str]) -> None:
    """Записать данные спецификации из КП снапшота (режим A)."""
    cs = st.session_state["contract"]
    cs["specification"] = {k: (v or "") for k, v in spec.items()}
    for key, val in cs["specification"].items():
        st.session_state[f"w_{key}"] = val


def set_spec_items(items: list) -> None:
    """Записать список SpecItem в specification['items']."""
    cs = st.session_state["contract"]
    cs.setdefault("specification", {})["items"] = items


def get_spec_items() -> list:
    """Получить список SpecItem из specification['items']."""
    cs = st.session_state.get("contract", {})
    return cs.get("specification", {}).get("items", [])


def set_payment_lines(rows: list[dict]) -> None:
    """Записать строки редактора условий оплаты."""
    st.session_state["contract"]["payment_lines"] = rows


def get_payment_lines() -> list[dict]:
    """Получить строки редактора условий оплаты."""
    cs = st.session_state.get("contract", {})
    return cs.get("payment_lines", [])


def set_requisites(requisites: dict[str, str]) -> None:
    """Записать реквизиты из карточки контрагента (режим A)."""
    cs = st.session_state["contract"]
    cs["requisites"] = {k: (v or "") for k, v in requisites.items()}
    for key, val in cs["requisites"].items():
        st.session_state[f"w_{key}"] = val


def merge_requisites(values: dict[str, str]) -> None:
    """Слить переданные поля в requisites namespace и в widget-ключи.

    В отличие от set_requisites НЕ заменяет весь dict — обновляет только
    переданные ключи (parsed/derived), сохраняя ручной ввод остальных полей.
    """
    cs = st.session_state["contract"]
    req = cs.setdefault("requisites", {})
    for key, val in values.items():
        v = val or ""
        req[key] = v
        st.session_state[f"w_{key}"] = v


def clear_generated() -> None:
    """Очистить сгенерированные файлы — вернуть страницу к форме генерации."""
    st.session_state["contract"]["generated"] = None


def is_extracted() -> bool:
    """True если данные готовы для отображения формы.
    Режим A: specification заполнена из КП снапшота.
    Режим B: ai_raw установлен после AI-extraction.
    """
    cs = st.session_state.get("contract", {})
    spec = cs.get("specification", {})
    has_spec_fields = any(k != "items" for k in spec)
    return bool(cs.get("ai_raw")) or has_spec_fields

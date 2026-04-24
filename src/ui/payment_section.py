"""Условия оплаты: 7 пресетов + split_by_items с динамическими группами."""
from __future__ import annotations

from typing import Any

import streamlit as st

from src.validation import _split_group_active


def _get_preset(payment_terms: dict, preset_id: str) -> dict | None:
    for p in payment_terms.get("presets", []):
        if p.get("id") == preset_id:
            return p
    return None


def render_payment_section(
    state: dict, payment_terms: dict, spec_items: list[dict]
) -> str:
    """Отрисовать секцию оплаты. Вернуть готовый текст (markdown) для sidebar."""
    st.subheader("4. Условия оплаты")

    presets = payment_terms.get("presets", [])
    preset_ids = [p["id"] for p in presets]
    preset_labels = {p["id"]: p["name"] for p in presets}

    if state.get("payment_preset_id") not in preset_ids:
        state["payment_preset_id"] = payment_terms.get(
            "default_preset_id", preset_ids[0]
        )

    st.selectbox(
        "Пресет",
        preset_ids,
        format_func=lambda pid: preset_labels.get(pid, pid),
        key="payment_preset_id",
    )

    preset = _get_preset(payment_terms, state["payment_preset_id"])
    if preset is None:
        return ""

    st.caption(preset.get("description", ""))

    if preset.get("is_split"):
        preview = _render_split(state, preset)
    elif preset.get("id") == "custom":
        preview = _render_custom(state, preset)
    else:
        preview = _render_simple(state, preset)

    st.markdown("**Превью условий оплаты:**")
    st.markdown(preview or "_(не определено)_")
    return preview


def _render_simple(state: dict, preset: dict) -> str:
    keys = preset.get("editable_percent_keys", [])
    defaults = preset.get("default_percents", {})
    # Инициализируем payment_percents при первом заходе или при смене пресета
    current = state.get("payment_percents", {}) or {}
    if set(current.keys()) != set(keys):
        state["payment_percents"] = {k: int(defaults.get(k, 0)) for k in keys}

    if keys:
        cols = st.columns(len(keys) + 1)
        for idx, k in enumerate(keys):
            with cols[idx]:
                val = st.number_input(
                    f"{k}, %",
                    min_value=0, max_value=100, step=1,
                    value=int(state["payment_percents"].get(k, defaults.get(k, 0))),
                    key=f"pay_pct_{k}",
                )
                state["payment_percents"][k] = int(val)
        with cols[-1]:
            if preset.get("editable_days"):
                st.number_input(
                    "Срок, банк. дней",
                    min_value=0, max_value=90, step=1,
                    key="payment_days",
                )
    fmt: dict[str, Any] = {**state["payment_percents"], "days": state["payment_days"]}
    try:
        return preset.get("body_template", "").format(**fmt)
    except KeyError:
        return preset.get("body_template", "")


def _render_split(state: dict, preset: dict) -> str:
    # Убеждаемся, что payment_split_state заполнено дефолтами
    split = state.setdefault("payment_split_state", {})
    groups = preset.get("groups", [])

    st.caption(
        "Группы, не включённые в спецификацию, "
        "автоматически скрываются (как на КП)."
    )
    active_lines: list[str] = []
    for group in groups:
        group_id = group["id"]
        active = _split_group_active(group_id, state)
        if not active:
            continue
        defaults = group["default_percents"]
        if group_id not in split:
            split[group_id] = {k: int(defaults[k]) for k in defaults}

        with st.container(border=True):
            st.markdown(f"**{group['label']}**")
            cols = st.columns(2)
            for idx, k in enumerate(group["editable_percent_keys"]):
                with cols[idx]:
                    val = st.number_input(
                        f"{k}, %",
                        min_value=0, max_value=100, step=1,
                        value=int(split[group_id].get(k, defaults.get(k, 0))),
                        key=f"split_{group_id}_{k}",
                    )
                    split[group_id][k] = int(val)
            trig = group.get("postpay_trigger", "")
            prepay = int(split[group_id].get("prepay", 0))
            postpay = int(split[group_id].get("postpay", 0))
            line = (
                f"— {group['label']}: предоплата {prepay}%, "
                f"доплата {postpay}% ({trig})."
            )
            active_lines.append(line)

    # Срок авансового платежа
    st.number_input(
        "Срок предоплаты, банк. дней", min_value=0, max_value=90,
        step=1, key="payment_days",
    )
    active_lines.append(
        f"— Предоплата перечисляется в течение {state['payment_days']} "
        "банковских дней с момента подписания договора."
    )
    return "\n\n".join(active_lines)


def _render_custom(state: dict, preset: dict) -> str:
    st.text_area(
        "Текст условий оплаты",
        key="payment_custom_text",
        placeholder=preset.get(
            "freeform_placeholder",
            "Опишите условия поставки в свободной форме...",
        ),
        height=150,
    )
    return state.get("payment_custom_text", "") or ""

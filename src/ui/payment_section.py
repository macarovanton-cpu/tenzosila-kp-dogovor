"""Условия оплаты: 6 вариантов (v1/v2/v3 + prepay_100 + split_by_items + custom)."""
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
    st.subheader(":material/credit_card: Условия оплаты")
    st.caption("Условия и процентные платежи")

    presets = payment_terms.get("presets", [])
    preset_ids = [p["id"] for p in presets]
    preset_labels = {p["id"]: p["name"] for p in presets}

    if state.get("payment_preset_id") not in preset_ids:
        state["payment_preset_id"] = payment_terms.get(
            "default_preset_id", preset_ids[0]
        )

    st.radio(
        "Пресет",
        preset_ids,
        format_func=lambda pid: preset_labels.get(pid, pid),
        key="payment_preset_id",
    )

    preset = _get_preset(payment_terms, state["payment_preset_id"])
    if preset is None:
        return ""

    st.caption(preset.get("description", ""))

    variant = preset.get("variant")
    if preset.get("is_split"):
        preview = _render_split(state, preset)
    elif preset.get("id") == "custom":
        preview = _render_custom(state, preset)
    elif variant == "v1":
        preview = _render_v1(state, preset)
    elif variant == "v2":
        preview = _render_v2(state, preset)
    elif variant == "v3":
        preview = _render_v3(state, preset)
    elif preset.get("id") == "prepay_100":
        preview = _render_prepay_100(state, preset)
    else:
        preview = ""

    st.markdown("**Превью условий оплаты:**")
    st.markdown(preview or "_(не определено)_")
    return preview


def _render_v1(state: dict, preset: dict) -> str:
    """Variant 1 — Аванс + Постоплата. Postpay = 100 - prepay (derived)."""
    cols = st.columns(3)
    with cols[0]:
        prepay = st.number_input(
            "Предоплата, %",
            min_value=1, max_value=99, step=1,
            value=int(st.session_state.get("payment_v1_prepay", 50)),
            key="payment_v1_prepay",
        )
    postpay = 100 - int(prepay)
    with cols[1]:
        st.metric("Постоплата, %", postpay)
    with cols[2]:
        st.number_input(
            "Срок аванса, банк. дней",
            min_value=1, max_value=90, step=1,
            key="payment_days",
        )
    return preset.get("body_template", "").format(
        prepay=int(prepay), postpay=postpay, days=int(state["payment_days"])
    )


def _render_v2(state: dict, preset: dict) -> str:
    """Variant 2 — Аванс + Перед отгрузкой + Постоплата. Postpay = 100 − prepay − preship."""
    cols = st.columns(4)
    with cols[0]:
        prepay = st.number_input(
            "Предоплата, %",
            min_value=1, max_value=98, step=1,
            value=int(st.session_state.get("payment_v2_prepay", 30)),
            key="payment_v2_prepay",
        )
    with cols[1]:
        preship = st.number_input(
            "Перед отгрузкой, %",
            min_value=0, max_value=99, step=1,
            value=int(st.session_state.get("payment_v2_preship", 40)),
            key="payment_v2_preship",
        )
    postpay = 100 - int(prepay) - int(preship)
    with cols[2]:
        st.metric("Постоплата, %", postpay)
    with cols[3]:
        st.number_input(
            "Срок аванса, банк. дней",
            min_value=1, max_value=90, step=1,
            key="payment_days",
        )
    if postpay < 1:
        st.warning(
            "Сумма «Предоплата + Перед отгрузкой» должна быть ≤ 99%, "
            "иначе нечего постоплачивать."
        )
    return preset.get("body_template", "").format(
        prepay=int(prepay), preship=int(preship), postpay=postpay,
        days=int(state["payment_days"]),
    )


def _render_v3(state: dict, preset: dict) -> str:
    """Variant 3 — 100% постоплата с настраиваемой точкой отсчёта."""
    triggers = preset.get("trigger_options", [])
    trigger_ids = [t["id"] for t in triggers]
    trigger_labels = {t["id"]: t["label"] for t in triggers}

    if state.get("payment_v3_trigger_id") not in trigger_ids and trigger_ids:
        state["payment_v3_trigger_id"] = preset.get(
            "default_trigger_id", trigger_ids[0]
        )

    cols = st.columns(2)
    with cols[0]:
        days = st.number_input(
            "Срок постоплаты, банк. дней",
            min_value=1, max_value=90, step=1,
            key="payment_v3_days",
        )
    with cols[1]:
        trigger_id = st.selectbox(
            "Точка отсчёта",
            trigger_ids,
            format_func=lambda i: trigger_labels.get(i, i),
            key="payment_v3_trigger_id",
        )

    trigger_text = next(
        (t["text"] for t in triggers if t["id"] == trigger_id), ""
    )
    return preset.get("body_template", "").format(
        days=int(days), trigger_text=trigger_text
    )


def _render_prepay_100(state: dict, preset: dict) -> str:
    """100% предоплата — единственное editable поле: срок."""
    cols = st.columns(2)
    with cols[0]:
        st.metric("Предоплата, %", 100)
    with cols[1]:
        st.number_input(
            "Срок, банк. дней",
            min_value=1, max_value=90, step=1,
            key="payment_days",
        )
    return preset.get("body_template", "").format(
        p1=100, days=int(state["payment_days"])
    )


def _render_split(state: dict, preset: dict) -> str:
    # Убеждаемся, что payment_split_state заполнено дефолтами
    split = state.setdefault("payment_split_state", {})
    groups = preset.get("groups", [])

    st.caption(
        "Группы, не включённые в спецификацию, "
        "автоматически скрываются (как на КП)."
    )
    active_lines: list[str] = []
    active_group_ids: list[str] = []
    for group in groups:
        group_id = group["id"]
        active = _split_group_active(group_id, state)
        if not active:
            continue
        active_group_ids.append(group_id)
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

    # Кнопка «Применить ко всем группам»: копирует scales-проценты в остальные.
    # Показываем только когда есть что копировать (есть не-scales активная группа).
    has_other_active = any(gid != "scales" for gid in active_group_ids)
    if has_other_active and "scales" in split:
        if st.button(
            "Применить ко всем группам",
            help=(
                "Скопировать prepay/postpay из «Весы» в остальные активные "
                "группы. Закрывает кейс ручной правки 50→30/70 в четырёх "
                "местах подряд."
            ),
            key="payment_split_apply_all",
        ):
            scales_vals = split["scales"]
            for gid in active_group_ids:
                if gid == "scales":
                    continue
                split[gid] = dict(scales_vals)
                # Синхронизируем widget-keys, чтобы number_input после rerun
                # подхватил новые значения (st.number_input управляется ключом).
                for k, v in scales_vals.items():
                    st.session_state[f"split_{gid}_{k}"] = int(v)
            st.rerun()

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

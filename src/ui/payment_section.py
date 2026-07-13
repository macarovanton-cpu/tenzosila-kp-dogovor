"""Условия оплаты: 6 вариантов (v1/v2/v3 + prepay_100 + split_by_items + custom)."""
from __future__ import annotations

import streamlit as st

from src.contracts.utils import due_days_phrase
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
            min_value=1, max_value=30, step=1,
            key="payment_days",
        )
    return preset.get("body_template", "").format(
        prepay=int(prepay), postpay=postpay,
        days_phrase=due_days_phrase(int(state["payment_days"]), with_words=False),
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
            min_value=1, max_value=30, step=1,
            key="payment_days",
        )
    if postpay < 1:
        st.warning(
            "Сумма «Предоплата + Перед отгрузкой» должна быть ≤ 99%, "
            "иначе нечего постоплачивать."
        )
    return preset.get("body_template", "").format(
        prepay=int(prepay), preship=int(preship), postpay=postpay,
        days_phrase=due_days_phrase(int(state["payment_days"]), with_words=False),
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
        days_phrase=due_days_phrase(int(days), with_words=False), trigger_text=trigger_text
    )


def _render_prepay_100(state: dict, preset: dict) -> str:
    """100% предоплата — единственное editable поле: срок."""
    cols = st.columns(2)
    with cols[0]:
        st.metric("Предоплата, %", 100)
    with cols[1]:
        st.number_input(
            "Срок, банк. дней",
            min_value=1, max_value=30, step=1,
            key="payment_days",
        )
    return preset.get("body_template", "").format(
        p1=100, days_phrase=due_days_phrase(int(state["payment_days"]), with_words=False)
    )


# W11: русские подписи полей процентов; внутренние ключи prepay/postpay не трогаем.
_PCT_LABELS = {"prepay": "предоплата, %", "postpay": "постоплата, %"}


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
                    # Доставка платится целиком по факту отгрузки — предоплаты нет.
                    # delivery.prepay — фантом (build_lines_from_snapshot его не
                    # читает), любое ненулевое значение молча занижает график.
                    # Держим read-only 0; пишем 0 в split напрямую, чтобы залипшее
                    # значение виджета из прошлой сессии не утекло в генерацию.
                    frozen = group_id == "delivery" and k == "prepay"
                    val = st.number_input(
                        _PCT_LABELS.get(k, f"{k}, %"),
                        min_value=0, max_value=100, step=1,
                        value=0 if frozen else int(split[group_id].get(k, defaults.get(k, 0))),
                        disabled=frozen,
                        help="Доставка оплачивается целиком по факту отгрузки" if frozen else None,
                        key=f"split_{group_id}_{k}",
                    )
                    split[group_id][k] = 0 if frozen else int(val)
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
        "Срок предоплаты, банк. дней", min_value=1, max_value=30,
        step=1, key="payment_days",
    )
    active_lines.append(
        f"— Предоплата перечисляется в течение "
        f"{due_days_phrase(int(state['payment_days']), with_words=False)} "
        "с момента подписания договора."
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

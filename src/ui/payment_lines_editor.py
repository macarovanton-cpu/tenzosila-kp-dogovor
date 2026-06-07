"""Редактор строк оплаты для страницы Договор."""
from __future__ import annotations

from math import isnan
from typing import Any

import pandas as pd
import streamlit as st

from src.contracts.payment_line import (
    PaymentLine,
    PaymentTrigger,
    build_lines_from_snapshot,
    format_payment_line,
)
from src.contracts.state import get_payment_lines, get_spec_items, set_payment_lines

_TRIGGER_LABELS: dict[str, PaymentTrigger] = {
    "Подписание спецификации": PaymentTrigger.SPEC_SIGNED,
    "Акт фундамента": PaymentTrigger.FOUNDATION_ACT,
    "Готовность к отгрузке": PaymentTrigger.SHIPMENT_READY,
    "Готовность принять бригаду": PaymentTrigger.BRIGADE_READY,
    "Акт выполненных работ": PaymentTrigger.WORK_ACT,
    "Поставка заказчику": PaymentTrigger.DELIVERED,
}
_TRIGGER_BY_LABEL = {v: k for k, v in _TRIGGER_LABELS.items()}

_COLUMNS = ["Тип", "%", "Основа", "Объект", "Сумма, ₽", "Событие", "Дней", "Ед."]
_KINDS = ["предоплата", "доплата"]
_PREPS = ["от стоимости", "за", "—"]
_DUE_UNITS = ["банковских", "рабочих", "календарных"]


def _is_blank(value: Any) -> bool:
    return value is None or value == "" or isinstance(value, float) and isnan(value)


def _line_to_row(line: PaymentLine) -> dict:
    """PaymentLine -> dict-строка редактора."""
    return {
        "Тип": line.kind,
        "%": line.share_pct,
        "Основа": line.share_prep or "—",
        "Объект": line.share_object,
        "Сумма, ₽": line.amount,
        "Событие": _TRIGGER_BY_LABEL[line.trigger],
        "Дней": line.due,
        "Ед.": line.due_unit,
    }


def _row_to_line(row: dict) -> PaymentLine:
    """dict-строка редактора -> PaymentLine."""
    share_pct = None if _is_blank(row.get("%")) else float(row.get("%"))
    prep = row.get("Основа")
    share_prep = prep if prep in ("от стоимости", "за") else None
    if share_pct is None:
        share_prep = None

    trigger_label = row.get("Событие") or "Подписание спецификации"
    due_unit = row.get("Ед.") or "банковских"
    return PaymentLine(
        kind=row.get("Тип") if row.get("Тип") in _KINDS else "предоплата",
        share_pct=share_pct,
        share_prep=share_prep,
        share_object=str(row.get("Объект") or ""),
        amount=0 if _is_blank(row.get("Сумма, ₽")) else int(row.get("Сумма, ₽")),
        trigger=_TRIGGER_LABELS.get(trigger_label, PaymentTrigger.SPEC_SIGNED),
        due=5 if _is_blank(row.get("Дней")) else int(row.get("Дней")),
        due_unit=due_unit if due_unit in _DUE_UNITS else "банковских",
    )


def _normalize_rows(rows: Any) -> list[dict]:
    rows_list = rows.to_dict("records") if hasattr(rows, "to_dict") else list(rows or [])
    return [
        {col: row.get(col) for col in _COLUMNS}
        for row in rows_list
        if any(not _is_blank(row.get(col)) for col in _COLUMNS)
    ]


def _rows_amount_total(rows: list[dict]) -> int:
    return sum(int(row.get("Сумма, ₽") or 0) for row in rows)


def render_payment_lines_editor() -> None:
    st.subheader("Условия оплаты")

    if st.button("Заполнить по умолчанию"):
        payment = st.session_state["contract"].get("kp_payment_snapshot") or {}
        lines = build_lines_from_snapshot(payment, get_spec_items())
        if not lines:
            st.warning(
                "Пресет оплаты из КП не поддерживает автозаполнение. "
                "Заполните строки вручную."
            )
        set_payment_lines([_line_to_row(line) for line in lines])
        if "payment_editor" in st.session_state:
            del st.session_state["payment_editor"]
        st.rerun()

    rows = get_payment_lines()
    edited_rows = st.data_editor(
        pd.DataFrame(rows, columns=_COLUMNS),
        num_rows="dynamic",
        column_config={
            "Тип": st.column_config.SelectboxColumn("Тип", options=_KINDS),
            "%": st.column_config.NumberColumn("%", min_value=0, max_value=100),
            "Основа": st.column_config.SelectboxColumn("Основа", options=_PREPS),
            "Объект": st.column_config.TextColumn("Объект"),
            "Сумма, ₽": st.column_config.NumberColumn("Сумма, ₽", min_value=0, format="%d"),
            "Событие": st.column_config.SelectboxColumn("Событие", options=list(_TRIGGER_LABELS)),
            "Дней": st.column_config.NumberColumn("Дней", min_value=0, max_value=90),
            "Ед.": st.column_config.SelectboxColumn("Ед.", options=_DUE_UNITS),
        },
        key="payment_editor",
        use_container_width=True,
        hide_index=True,
    )
    synced_rows = _normalize_rows(edited_rows)
    set_payment_lines(synced_rows)

    spec_total = sum(int(item.get("total") or 0) for item in get_spec_items())
    editor_sum = _rows_amount_total(synced_rows)
    delta = editor_sum - spec_total
    if not synced_rows:
        st.info(
            "Строки оплаты не заполнены. Нажмите «Заполнить по умолчанию» "
            "или добавьте строки вручную."
        )
    elif delta != 0:
        delta_text = f"{abs(delta):,}".replace(",", " ")
        st.error(f"Расхождение: {delta_text} ₽ между строками оплаты и итогом.")

    if synced_rows:
        st.caption("Текст договора:")
        for i, row in enumerate(synced_rows, start=1):
            st.text(format_payment_line(_row_to_line(row), f"2.{i}"))

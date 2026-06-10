"""Редактор строк оплаты для страницы Договор.

Модель «процент — истина, сумма производная»: менеджер правит `%` и `База, ₽`,
а `Сумма, ₽` вычисляется (`amount = round(% / 100 × база)`) и read-only в таблице.
Последняя строка с данной базой добирает остаток, если Σ% по базе == 100.
"""
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

_COLUMNS = ["Тип", "%", "Основа", "Объект", "База, ₽", "Сумма, ₽", "Событие", "Дней", "Ед."]
_KINDS = ["предоплата", "доплата", "оплата"]
_PREPS = ["от стоимости", "за", "от", "—"]
_DUE_UNITS = ["банковских", "рабочих", "календарных"]


def _is_blank(value: Any) -> bool:
    """None / "" / NaN (в т.ч. numpy/pandas) → True."""
    if value is None or value == "":
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return isinstance(value, float) and isnan(value)


def _to_int(value: Any) -> int | None:
    """numpy/NaN/пусто → None; иначе строгий python int."""
    if _is_blank(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    """numpy/NaN/пусто → None; иначе строгий python float."""
    if _is_blank(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _line_to_row(line: PaymentLine) -> dict:
    """PaymentLine -> dict-строка редактора."""
    return {
        "Тип": line.kind,
        "%": line.share_pct,
        "Основа": line.share_prep or "—",
        "Объект": line.share_object,
        "База, ₽": line.base_amount,
        "Сумма, ₽": line.amount,
        "Событие": _TRIGGER_BY_LABEL[line.trigger],
        "Дней": line.due,
        "Ед.": line.due_unit,
    }


def _row_to_line(row: dict) -> PaymentLine:
    """dict-строка редактора -> PaymentLine."""
    share_pct = _to_float(row.get("%"))
    prep = row.get("Основа")
    share_prep = prep if prep in ("от стоимости", "за", "от") else None
    if share_pct is None:
        share_prep = None
    elif share_prep is None:
        # Ручной % без выбранной «Основы» → дефолт, чтобы текст не печатал «50% None …».
        share_prep = "от стоимости"

    trigger_label = row.get("Событие") or "Подписание спецификации"
    due_unit = row.get("Ед.") or "банковских"
    base = _to_int(row.get("База, ₽"))
    amount = _to_int(row.get("Сумма, ₽"))
    due = _to_int(row.get("Дней"))
    return PaymentLine(
        kind=row.get("Тип") if row.get("Тип") in _KINDS else "предоплата",  # type: ignore[arg-type]
        share_pct=share_pct,
        share_prep=share_prep,
        share_object=str(row.get("Объект") or ""),
        amount=0 if amount is None else amount,
        trigger=_TRIGGER_LABELS.get(trigger_label, PaymentTrigger.SPEC_SIGNED),
        due=5 if due is None else due,
        due_unit=due_unit if due_unit in _DUE_UNITS else "банковских",
        base_amount=base,
    )


def _coerce_row(row: dict) -> dict:
    """Привести строку к строго python-типам (без numpy/NaN) — стабильное равенство."""
    kind = row.get("Тип")
    prep = row.get("Основа")
    trigger = row.get("Событие")
    unit = row.get("Ед.")
    days = _to_int(row.get("Дней"))
    amount = _to_int(row.get("Сумма, ₽"))
    return {
        "Тип": str(kind) if kind in _KINDS else "предоплата",
        "%": _to_float(row.get("%")),
        "Основа": str(prep) if prep in _PREPS else "—",
        "Объект": "" if _is_blank(row.get("Объект")) else str(row.get("Объект")),
        "База, ₽": _to_int(row.get("База, ₽")),
        "Сумма, ₽": 0 if amount is None else amount,
        "Событие": str(trigger) if trigger in _TRIGGER_LABELS else "Подписание спецификации",
        "Дней": 5 if days is None else days,
        "Ед.": str(unit) if unit in _DUE_UNITS else "банковских",
    }


def _normalize_rows(rows: Any) -> list[dict]:
    """DataFrame/список -> список строго-типизированных dict; пустые строки дропаются."""
    rows_list = rows.to_dict("records") if hasattr(rows, "to_dict") else list(rows or [])
    return [
        _coerce_row(row)
        for row in rows_list
        if any(not _is_blank(row.get(col)) for col in _COLUMNS)
    ]


def _recompute_amounts(rows: list[dict], spec_total: int) -> list[dict]:
    """Пересчитать «Сумма, ₽» из «%» и «База, ₽».

    Пустая база → ИТОГО. amount = round(% / 100 × база). Строки без процента
    (share_pct=None) не пересчитываются. В группе строк с одинаковой базой, если
    Σ% == 100, последняя добирает остаток (Σ группы == база точно).
    """
    rows = [dict(r) for r in rows]
    for r in rows:
        if r.get("База, ₽") is None:
            r["База, ₽"] = int(spec_total)
        pct = r.get("%")
        if pct is not None:
            r["Сумма, ₽"] = int(round(pct / 100 * r["База, ₽"]))

    groups: dict[int, list[dict]] = {}
    for r in rows:
        if r.get("%") is not None:
            groups.setdefault(r["База, ₽"], []).append(r)
    for base, grp in groups.items():
        if round(sum(r["%"] for r in grp)) == 100:
            assigned = sum(r["Сумма, ₽"] for r in grp[:-1])
            grp[-1]["Сумма, ₽"] = int(base) - assigned
    return rows


def _rows_amount_total(rows: list[dict]) -> int:
    return sum(int(row.get("Сумма, ₽") or 0) for row in rows)


def _validate_rows(rows: list[dict], spec_total: int) -> tuple[str | None, list[str]]:
    """Вернуть (error, warnings). error блокирует (перебор по базе)."""
    if not rows:
        return None, []

    pct_by_base: dict[int, float] = {}
    for r in rows:
        pct = r.get("%")
        base = r.get("База, ₽")
        if pct is None or base is None:
            continue
        pct_by_base[base] = pct_by_base.get(base, 0.0) + pct
    error = None
    if any(round(total) > 100 for total in pct_by_base.values()):
        error = "Σ процентов по одной базе превышает 100%. Проверьте проценты."

    warnings: list[str] = []
    if any((r.get("База, ₽") or 0) > spec_total for r in rows):
        warnings.append(
            "База строки больше ИТОГО спецификации — возможно, авто-база сломана."
        )
    missing = spec_total - _rows_amount_total(rows)
    if missing > max(len(rows), 1):  # допуск округления ~рубль на строку
        miss_text = f"{missing:,}".replace(",", " ")
        warnings.append(
            f"Суммы покрывают не весь ИТОГО — не хватает {miss_text} ₽. "
            "Возможно, какой-то платёж распределён не полностью."
        )
    return error, warnings


def render_payment_lines_editor() -> None:
    st.subheader("Условия оплаты")

    spec_items = get_spec_items()
    spec_total = sum(int(item.get("total") or 0) for item in spec_items)

    if st.button("Заполнить по умолчанию"):
        payment = st.session_state["contract"].get("kp_payment_snapshot") or {}
        lines = build_lines_from_snapshot(payment, spec_items)
        if not lines:
            st.warning(
                "Пресет оплаты из КП не поддерживает автозаполнение. "
                "Заполните строки вручную."
            )
        new_rows = _recompute_amounts(
            _normalize_rows([_line_to_row(line) for line in lines]), spec_total
        )
        set_payment_lines(new_rows)
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
            "База, ₽": st.column_config.NumberColumn("База, ₽", min_value=0, format="%d"),
            "Сумма, ₽": st.column_config.NumberColumn(
                "Сумма, ₽", min_value=0, format="%d", disabled=True
            ),
            "Событие": st.column_config.SelectboxColumn("Событие", options=list(_TRIGGER_LABELS)),
            "Дней": st.column_config.NumberColumn("Дней", min_value=0, max_value=90),
            "Ед.": st.column_config.SelectboxColumn("Ед.", options=_DUE_UNITS),
        },
        key="payment_editor",
        use_container_width=True,
        hide_index=True,
    )
    synced_rows = _recompute_amounts(_normalize_rows(edited_rows), spec_total)
    set_payment_lines(synced_rows)
    if synced_rows != rows:
        # Вход data_editor обновился (пересчёт суммы) → один rerun до сходимости.
        # Пересчёт идемпотентен, поэтому цикл не зациклится.
        st.rerun()

    if not synced_rows:
        st.info(
            "Строки оплаты не заполнены. Нажмите «Заполнить по умолчанию» "
            "или добавьте строки вручную."
        )
        return

    error, warnings = _validate_rows(synced_rows, spec_total)
    if error:
        st.error(error)
    for warning in warnings:
        st.warning(warning)
    if not error and not warnings:
        st.caption("✓ Суммы сходятся с ИТОГО спецификации.")

    st.caption("Текст договора:")
    for i, row in enumerate(synced_rows, start=1):
        st.text(format_payment_line(_row_to_line(row), f"2.{i}"))

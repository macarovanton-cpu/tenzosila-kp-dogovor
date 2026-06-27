"""Streamlit-вью обновления прайса из PDF: загрузка → таблица → проверка → применение.

Тонкий UI-слой над готовым backend трека прайса (только использование, без правок):
parse_dealer_pdf / parse_retail_pdf → merge_price_items → split_validation →
build_business_summary → write_prices.

Конверсия таблица ↔ PriceItem: полный list[PriceItem] (источник правды) живёт в
session_state; data_editor правит человеко-представление, а сборка обратно идёт через
editing-state delta (edited_rows/added_rows/deleted_rows). Ключи распознанных строк
неизменяемы — служебные поля (price_class, applies_to_*, range_*, raw_payload) не теряются.
"""
from __future__ import annotations

import dataclasses
import os
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.admin import price_write_service
from src.admin.price_business_summary import BusinessSummary, build_business_summary
from src.admin.price_models import (
    MODEL_PRICE_CLASS,
    UNKNOWN_PRICE_CLASS,
    PriceItem,
)
from src.admin.price_normalizer import normalize_prices
from src.admin.price_pdf_dealer import parse_dealer_pdf
from src.admin.price_pdf_merge import merge_price_items
from src.admin.price_pdf_retail import parse_retail_pdf
from src.admin.price_validation_split import ValidationSplit, split_validation
from src.data_loader import load_prices

# Человеческие колонки рабочей таблицы (+ «Ключ» последней — Вариант 1).
_COL_NAME = "Наименование"
_COL_TYPE = "Тип"
_COL_RETAIL = "Розница"
_COL_DEALER = "Дилер"
_COL_FLAG = "Признак"
_COL_SOURCE = "Источник"
_COL_KEY = "Ключ"
_COLUMNS = [_COL_NAME, _COL_TYPE, _COL_RETAIL, _COL_DEALER, _COL_FLAG, _COL_SOURCE, _COL_KEY]

_TYPE_MODEL = "Модель"
_TYPE_OPTION = "Опция"
_FLAG_ON_REQUEST = "по запросу"
_FLAG_NORMAL = "обычная"

_EDITOR_KEY = "price_update_editor"
_MIN_MODELS = 30  # меньше — похоже на не тот файл / сбой парсера

_KEY_HELP = (
    "как в прайсе: frame_18, vesta-с-100-24; "
    "для новой позиции — уникальный, без пробелов"
)


# ──────────────────── чистые хелперы (тестируются без Streamlit) ────────────────────

def items_to_dataframe(items: list[PriceItem]) -> pd.DataFrame:
    """list[PriceItem] → человеко-читаемый DataFrame со стабильным RangeIndex."""
    rows = [
        {
            _COL_NAME: item.label,
            _COL_TYPE: _TYPE_MODEL if item.item_type == "model" else _TYPE_OPTION,
            _COL_RETAIL: item.price_retail,
            _COL_DEALER: item.price_dealer_ru,
            _COL_FLAG: _FLAG_ON_REQUEST if item.on_request else _FLAG_NORMAL,
            _COL_SOURCE: item.raw_payload.get("source", ""),
            _COL_KEY: item.key,
        }
        for item in items
    ]
    return pd.DataFrame(rows, columns=_COLUMNS)


def apply_editor_delta(
    working_items: list[PriceItem],
    editor_state: dict[str, Any],
) -> list[PriceItem]:
    """Собрать итоговый list[PriceItem] из источника правды и delta data_editor.

    editor_state: {"edited_rows": {pos: {col: val}}, "added_rows": [...], "deleted_rows": [pos]}.
    Ключ распознанной строки НЕ меняется (берётся из working_items) — служебные поля целы.
    Свободный ввод ключа разрешён только для добавленных строк.
    """
    edited_rows = editor_state.get("edited_rows", {}) or {}
    added_rows = editor_state.get("added_rows", []) or []
    deleted_rows = set(editor_state.get("deleted_rows", []) or [])

    result: list[PriceItem] = []
    for pos, base in enumerate(working_items):
        if pos in deleted_rows:
            continue
        changes = edited_rows.get(pos) or edited_rows.get(str(pos)) or {}
        result.append(_apply_existing_changes(base, changes))

    for row in added_rows:
        result.append(_new_item_from_row(row))

    return result


def _apply_existing_changes(base: PriceItem, changes: dict[str, Any]) -> PriceItem:
    """Наложить человеческие правки на распознанную строку. Ключ игнорируется."""
    if not changes:
        return base

    label = str(changes[_COL_NAME]) if _COL_NAME in changes else base.label
    item_type = (
        ("model" if changes[_COL_TYPE] == _TYPE_MODEL else "option")
        if _COL_TYPE in changes
        else base.item_type
    )
    price_retail = _to_opt_int(changes[_COL_RETAIL]) if _COL_RETAIL in changes else base.price_retail
    price_dealer = _to_opt_int(changes[_COL_DEALER]) if _COL_DEALER in changes else base.price_dealer_ru
    on_request = (changes[_COL_FLAG] == _FLAG_ON_REQUEST) if _COL_FLAG in changes else base.on_request

    return dataclasses.replace(
        base,
        label=label,
        item_type=item_type,  # type: ignore[arg-type]
        price_retail=price_retail,
        price_dealer_ru=price_dealer,
        on_request=on_request,
    )


def _new_item_from_row(row: dict[str, Any]) -> PriceItem:
    """Добавленная менеджером строка → свежий PriceItem без служебных метаданных."""
    item_type = "model" if row.get(_COL_TYPE) == _TYPE_MODEL else "option"
    on_request = row.get(_COL_FLAG) == _FLAG_ON_REQUEST
    price_class = MODEL_PRICE_CLASS if item_type == "model" else UNKNOWN_PRICE_CLASS
    key = str(row.get(_COL_KEY) or "").strip()
    return PriceItem(
        item_type=item_type,  # type: ignore[arg-type]
        key=key,
        label=str(row.get(_COL_NAME) or key),
        price_retail=_to_opt_int(row.get(_COL_RETAIL)),
        price_dealer_ru=_to_opt_int(row.get(_COL_DEALER)),
        discount_pct=None,
        price_class=price_class,
        on_request=on_request,
        allow_customer_value=False,
        range_min=None,
        range_max=None,
        applies_to_lines=[],
        applies_to_lengths=[],
        raw_payload={},
    )


def _to_opt_int(value: Any) -> int | None:
    """Пусто / NaN / нечисловое → None; иначе int."""
    if value is None or value == "":
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ──────────────────── вью ────────────────────

def render_update_view() -> None:
    """Поток обновления прайса: выбор источника → таблица → проверка → применение."""
    st.header("Обновление прайса")

    stage = st.session_state.get("price_update_stage", "source")
    if stage == "table":
        _render_table()
    elif stage == "result":
        _render_result()
    else:
        _render_source_select()


def _render_source_select() -> None:
    st.caption("Загрузите два PDF или отредактируйте текущий прайс.")

    col_pdf, col_current = st.columns(2)
    with col_pdf:
        load_pdf = st.button("Загрузить из PDF", key="price_update_pick_pdf")
    with col_current:
        edit_current = st.button("Редактировать текущий", key="price_update_pick_current")

    if load_pdf:
        st.session_state["price_update_source"] = "pdf"
    if edit_current:
        _enter_table(normalize_prices(load_prices()))
        return

    if st.session_state.get("price_update_source") != "pdf":
        return

    dealer_file = st.file_uploader(
        "Дилерский прайс (PDF)", type=["pdf"], key="price_update_dealer_pdf"
    )
    retail_file = st.file_uploader(
        "Розничный прайс (PDF)", type=["pdf"], key="price_update_retail_pdf"
    )

    if not st.button(
        "Прочитать прайс",
        key="price_update_parse",
        disabled=dealer_file is None or retail_file is None,
    ):
        return

    with st.spinner("Читаю прайс…"):
        items = _parse_uploaded(dealer_file, retail_file)
    if items is None:
        return

    model_count = sum(1 for item in items if item.item_type == "model")
    if model_count < _MIN_MODELS:
        st.warning(
            f"Распознано мало моделей ({model_count}). Похоже, файл не тот или парсер не "
            "справился — проверьте таблицу ниже вручную."
        )
    _enter_table(items)


def _parse_uploaded(dealer_file: Any, retail_file: Any) -> list[PriceItem] | None:
    """Спарсить оба PDF в list[PriceItem]. При ошибке — st.error и None."""
    dealer_items = _parse_single(dealer_file, parse_dealer_pdf, "дилерский")
    if dealer_items is None:
        return None
    retail_items = _parse_single(retail_file, parse_retail_pdf, "розничный")
    if retail_items is None:
        return None
    try:
        return merge_price_items(dealer_items, retail_items)
    except Exception:  # noqa: BLE001 - дружелюбное сообщение вместо трейсбека
        st.error("Не удалось объединить прайсы из PDF. Проверьте оба файла.")
        return None


def _parse_single(uploaded: Any, parser: Any, label: str) -> list[PriceItem] | None:
    tmp_path: str | None = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(fd, "wb") as handle:
            handle.write(uploaded.getvalue())
        return parser(Path(tmp_path))
    except Exception:  # noqa: BLE001 - дружелюбное сообщение вместо трейсбека
        st.error(
            f"Не удалось прочитать {label} PDF. Проверьте, что это правильный файл прайса."
        )
        return None
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _enter_table(items: list[PriceItem]) -> None:
    st.session_state["price_update_working_items"] = items
    st.session_state["price_update_stage"] = "table"
    st.session_state.pop("price_update_checked", None)
    st.session_state.pop(_EDITOR_KEY, None)
    st.rerun()


def _render_table() -> None:
    working_items: list[PriceItem] = st.session_state.get("price_update_working_items", [])
    old_items = normalize_prices(load_prices())

    st.data_editor(
        items_to_dataframe(working_items),
        num_rows="dynamic",
        key=_EDITOR_KEY,
        use_container_width=True,
        column_config={
            _COL_TYPE: st.column_config.SelectboxColumn(
                _COL_TYPE, options=[_TYPE_MODEL, _TYPE_OPTION]
            ),
            _COL_RETAIL: st.column_config.NumberColumn(_COL_RETAIL, min_value=0),
            _COL_DEALER: st.column_config.NumberColumn(_COL_DEALER, min_value=0),
            _COL_FLAG: st.column_config.SelectboxColumn(
                _COL_FLAG, options=[_FLAG_NORMAL, _FLAG_ON_REQUEST]
            ),
            _COL_SOURCE: st.column_config.TextColumn(_COL_SOURCE, disabled=True),
            _COL_KEY: st.column_config.TextColumn(_COL_KEY, help=_KEY_HELP),
        },
    )
    st.caption(f"Колонка «Ключ»: {_KEY_HELP}.")

    editor_state = st.session_state.get(_EDITOR_KEY, {})
    items = apply_editor_delta(working_items, editor_state)
    deleted_count = len(editor_state.get("deleted_rows", []) or [])

    col_check, col_cancel = st.columns(2)
    with col_check:
        if st.button("Проверить", key="price_update_check", type="primary"):
            st.session_state["price_update_checked"] = True
    with col_cancel:
        if st.button("Отмена", key="price_update_cancel"):
            _reset()
            st.rerun()

    if st.session_state.get("price_update_checked"):
        _render_review(items, old_items, deleted_count)


def _render_review(
    items: list[PriceItem],
    old_items: list[PriceItem],
    deleted_count: int,
) -> None:
    # Блокеры/предупреждения — на результате редактора (сохраняет детект дублей и пустых
    # ключей до three-way merge, где dict-ключи схлопнулись бы).
    split = split_validation(items, old_items=old_items)
    _render_issues(split)

    # Сводка — на ИТОГОВОМ датасете three-way merge (ровно то, что запишет write_prices):
    # позиции вне PDF-снимка переносятся из текущего прайса, ложного «Удалено» нет.
    final_items = normalize_prices(
        price_write_service.build_merged_prices(items, load_prices())
    )
    if deleted_count:
        st.warning(
            f"Удаление строк ({deleted_count}) не применяется: позиции, отсутствующие в "
            "снимке, переносятся из текущего прайса. Чтобы убрать позицию из прайса — "
            "правьте JSON вручную (в этой версии не поддерживается)."
        )
    _render_summary(build_business_summary(old_items, final_items))

    col_apply, col_back = st.columns(2)
    with col_apply:
        if st.button(
            "Применить новый прайс",
            key="price_update_apply",
            type="primary",
            disabled=split.has_blockers,
        ):
            _apply(items)
    with col_back:
        if st.button("Вернуться к правке", key="price_update_back"):
            st.session_state.pop("price_update_checked", None)
            st.rerun()


def _render_issues(split: ValidationSplit) -> None:
    with st.container(border=True):
        st.subheader("Проверка")
        if split.blockers:
            st.error(f"Блокеры: {len(split.blockers)} (применение недоступно)")
            st.table(_issue_rows(split.blockers))
        else:
            st.success("Блокеров нет.")
        if split.warnings:
            st.warning(f"Предупреждения: {len(split.warnings)}")
            st.table(_issue_rows(split.warnings))


def _render_summary(summary: BusinessSummary) -> None:
    with st.container(border=True):
        st.subheader("Что изменится")
        empty = not any(
            (
                summary.price_up,
                summary.price_down,
                summary.added,
                summary.removed,
                summary.to_on_request,
            )
        )
        if empty:
            st.info("Изменений нет.")
            return

        if summary.price_up:
            st.markdown("**Подорожало**")
            st.table(_change_rows(summary.price_up))
        if summary.price_down:
            st.markdown("**Подешевело**")
            st.table(_change_rows(summary.price_down))
        if summary.added:
            st.markdown("**Добавлено**")
            st.table(_change_rows(summary.added))
        # «Удалено» — всегда отдельным подсвеченным блоком: ловит случайную смену ключа.
        if summary.removed:
            st.error(f"Удалено позиций: {len(summary.removed)} — проверьте, не потерян ли ключ.")
            st.table(_change_rows(summary.removed))
        if summary.to_on_request:
            st.markdown("**Стало «по запросу»**")
            st.table(_change_rows(summary.to_on_request))


def _apply(items: list[PriceItem]) -> None:
    try:
        result = price_write_service.write_prices(items)
    except Exception:  # noqa: BLE001 - дружелюбное сообщение вместо трейсбека
        st.error("Не удалось записать прайс. Текущий прайс не изменён.")
        return
    st.session_state["price_update_backup_path"] = str(result.backup_path)
    st.session_state["price_update_stage"] = "result"
    st.session_state.pop("price_update_checked", None)
    st.rerun()


def _render_result() -> None:
    st.success("Прайс обновлён, предыдущая версия сохранена.")
    backup = st.session_state.get("price_update_backup_path")
    if backup:
        st.caption(f"Бэкап: {backup}")
    if st.button("К началу", key="price_update_restart"):
        _reset()
        st.rerun()


def _reset() -> None:
    for key in (
        "price_update_stage",
        "price_update_source",
        "price_update_working_items",
        "price_update_checked",
        "price_update_backup_path",
        _EDITOR_KEY,
    ):
        st.session_state.pop(key, None)


def _issue_rows(issues: list[Any]) -> list[dict[str, str]]:
    return [
        {"Позиция": issue.item_key, "Поле": issue.field, "Сообщение": issue.message}
        for issue in issues
    ]


def _change_rows(entries: list[Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in entries:
        rows.append(
            {
                "Позиция": entry.label,
                "Было": "—" if entry.old_value is None else str(entry.old_value),
                "Стало": "—" if entry.new_value is None else str(entry.new_value),
                "%": "" if entry.delta_pct is None else f"{entry.delta_pct:+.1f}%",
            }
        )
    return rows

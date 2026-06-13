"""Streamlit-view проверки загруженного JSON-прайса."""
from __future__ import annotations

from typing import Any

import streamlit as st

from src.admin.price_upload_service import (
    PriceUploadAnalysis,
    analyze_uploaded_price_json,
)


def render_price_upload(current_prices: dict[str, Any]) -> None:
    """Показать semi-manual сценарий validate + diff + download."""

    st.header("Проверка загруженного прайса")
    st.info(
        "Файл не сохраняется автоматически и не записывается в БД. "
        "Чтобы применить проверенный прайс, человек вручную заменяет "
        "`data/prices.json` через git."
    )

    uploaded = st.file_uploader(
        "Загрузить подготовленный `prices.json`",
        type=["json"],
        key="admin_price_upload_json",
        help="Проверка выполняется в памяти: data/prices.json не изменяется.",
    )
    if uploaded is None:
        st.caption("Загрузите JSON-файл, чтобы увидеть валидацию и diff.")
        return

    result = analyze_uploaded_price_json(
        uploaded.getvalue(),
        current_prices=current_prices,
    )
    if result.parse_error:
        st.error(result.parse_error)
        return

    _render_validation(result)
    if not result.can_download:
        st.warning("Скачивание заблокировано, пока в прайсе есть errors.")
        return

    _render_diff(result)
    st.download_button(
        "Скачать проверенный JSON",
        data=result.download_json or "",
        file_name="prices.validated.json",
        mime="application/json",
        disabled=not result.can_download,
        key="admin_price_download_json",
    )

def _render_validation(result: PriceUploadAnalysis) -> None:
    with st.container(border=True):
        st.subheader("Валидация")
        if result.errors:
            st.error(f"Errors: {result.error_count}")
            st.table(_issue_rows(result.errors))
        else:
            st.success("Errors не найдены. Download разрешён.")

        if result.warnings:
            st.warning(f"Warnings: {result.warning_count}")
            st.table(_issue_rows(result.warnings))


def _render_diff(result: PriceUploadAnalysis) -> None:
    with st.container(border=True):
        st.subheader("Diff с текущим `data/prices.json`")
        cols = st.columns(3)
        cols[0].metric("Добавлено", result.diff_summary["added"])
        cols[1].metric("Удалено", result.diff_summary["removed"])
        cols[2].metric("Изменено", result.diff_summary["changed"])

        if result.diff is None:
            return
        if result.diff_summary == {"added": 0, "removed": 0, "changed": 0}:
            st.success("Diff пустой: загруженный прайс совпадает с текущим.")
            return

        if result.diff.added:
            st.table(_item_rows(result.diff.added))
        if result.diff.removed:
            st.table(_item_rows(result.diff.removed))
        if result.diff.changed:
            st.table(_change_rows(result.diff.changed))


def _issue_rows(issues: list[Any]) -> list[dict[str, str]]:
    return [
        {
            "Позиция": issue.item_key,
            "Поле": issue.field,
            "Сообщение": issue.message,
        }
        for issue in issues
    ]


def _item_rows(items: list[Any]) -> list[dict[str, str]]:
    return [
        {
            "Тип": item.item_type,
            "Позиция": item.key,
            "Класс": item.price_class,
        }
        for item in items
    ]


def _change_rows(items: list[Any]) -> list[dict[str, str]]:
    rows = []
    for item in items:
        for change in item.changes:
            rows.append(
                {
                    "Тип": item.item_type,
                    "Позиция": item.item_key,
                    "Поле": change.field,
                    "Было": str(change.old_value),
                    "Стало": str(change.new_value),
                }
            )
    return rows

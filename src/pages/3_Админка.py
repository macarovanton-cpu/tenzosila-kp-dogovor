"""Read-only страница админки прайса."""
from __future__ import annotations

import streamlit as st

from src.admin.price_diagnostics import diagnose_prices, load_prices_file


st.title("Админка")
st.info(
    "Страница read-only: сейчас она только показывает диагностику текущего "
    "прайса. Изменение данных, роли и права доступа появятся позже; пока "
    "страница видна всем пользователям приложения."
)

try:
    prices = load_prices_file()
    diagnostics = diagnose_prices(prices)
except Exception as exc:  # pragma: no cover - защита UI от битого локального файла.
    st.error(f"Не удалось прочитать или проверить текущий прайс: {exc}")
    st.stop()

meta = prices.get("_meta", {})
meta = meta if isinstance(meta, dict) else {}
errors = [
    issue for issue in diagnostics.validation_issues if issue.level == "error"
]
warnings = [
    issue for issue in diagnostics.validation_issues if issue.level == "warning"
]

st.header("Диагностика текущего прайса")

metric_cols = st.columns(4)
metric_cols[0].metric("Модели", diagnostics.model_count)
metric_cols[1].metric("Опции", diagnostics.option_count)
metric_cols[2].metric("Errors", diagnostics.error_count)
metric_cols[3].metric("Warnings", diagnostics.warning_count)

if diagnostics.is_expired:
    st.error("Прайс просрочен: дата valid_until уже прошла.")
elif errors:
    st.error("В прайсе есть ошибки. Перед использованием нужен разбор.")
elif warnings:
    st.warning("Критических ошибок нет, но есть warnings по качеству данных.")
else:
    st.success("Критических проблем в текущем прайсе не найдено.")

with st.container(border=True):
    st.subheader("Метаданные прайса")
    metadata_rows = [
        ("Версия", meta.get("version", "не указана")),
        ("Валюта", meta.get("currency", "не указана")),
        ("Действует с", diagnostics.valid_from or "не указано"),
        ("Действует до", diagnostics.valid_until or "не указано"),
        ("Обновлен", meta.get("updated_at", "не указано")),
        ("Источник розницы", meta.get("source_retail", "не указан")),
        ("Источник дилера", meta.get("source_dealer", "не указан")),
        ("НДС", meta.get("vat_note", "не указан")),
    ]
    st.table([{"Поле": key, "Значение": value} for key, value in metadata_rows])

with st.container(border=True):
    st.subheader("Структура")
    st.table(
        [
            {"Показатель": "Опции по запросу", "Значение": diagnostics.on_request_count},
            {
                "Показатель": "Позиции с пустой или нулевой ценой",
                "Значение": len(diagnostics.zero_price_items),
            },
            {
                "Показатель": "Модели без полной цены",
                "Значение": len(diagnostics.models_without_price),
            },
            *[
                {"Показатель": f"Класс {price_class}", "Значение": count}
                for price_class, count in sorted(diagnostics.class_counts.items())
            ],
        ]
    )

with st.container(border=True):
    st.subheader("Errors")
    if errors:
        st.error(f"Найдено ошибок: {len(errors)}")
        st.table(
            [
                {
                    "Позиция": issue.item_key,
                    "Поле": issue.field,
                    "Сообщение": issue.message,
                }
                for issue in errors
            ]
        )
    else:
        st.success("Errors не найдены.")

with st.container(border=True):
    st.subheader("Warnings")
    if warnings:
        st.warning(f"Найдено предупреждений: {len(warnings)}")
        st.table(
            [
                {
                    "Позиция": issue.item_key,
                    "Поле": issue.field,
                    "Сообщение": issue.message,
                }
                for issue in warnings
            ]
        )
    else:
        st.success("Warnings не найдены.")

with st.container(border=True):
    st.subheader("Проблемы цен")
    if diagnostics.zero_price_items:
        st.warning("Есть позиции с пустой или нулевой розничной ценой.")
        st.table(
            [
                {
                    "Тип": item.item_type,
                    "Позиция": item.item_key,
                    "Поле": item.field,
                    "Сообщение": item.message,
                }
                for item in diagnostics.zero_price_items
            ]
        )
    else:
        st.success("Пустые или нулевые цены не найдены.")

    if diagnostics.models_without_price:
        st.warning("Есть модели без полной розничной или дилерской цены.")
        st.table([{"Модель": key} for key in diagnostics.models_without_price])
    else:
        st.success("Все модели имеют розничную и дилерскую цену.")

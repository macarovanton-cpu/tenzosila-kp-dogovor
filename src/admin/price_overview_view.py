"""Read-only UI-панель диагностики прайса и ценовых правил."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from src.admin.price_diagnostics import PriceDiagnostics, diagnose_prices
from src.config import (
    MAX_COEFF,
    MIN_COEFF_B,
    SYNTHETIC_DEALER_FACTOR,
    VAT_RATE,
)


@dataclass(frozen=True)
class PriceRuleRow:
    """Строка справки по одному ценовому классу."""

    price_class: str
    meaning: str
    lower_bound: str
    default_value: str
    upper_bound: str


@dataclass(frozen=True)
class PriceOverviewViewModel:
    """Данные read-only панели прайса."""

    diagnostics: PriceDiagnostics
    vat_rate: float
    vat_percent: int
    max_coeff: float
    min_coeff_b: float
    synthetic_dealer_factor: float
    rule_rows: list[PriceRuleRow]
    readonly_note: str
    rules_note: str


def build_price_overview_view_model(
    prices: dict[str, Any],
) -> PriceOverviewViewModel:
    """Собрать данные для панели без записи в прайс или БД."""

    return PriceOverviewViewModel(
        diagnostics=diagnose_prices(prices),
        vat_rate=VAT_RATE,
        vat_percent=round(VAT_RATE * 100),
        max_coeff=MAX_COEFF,
        min_coeff_b=MIN_COEFF_B,
        synthetic_dealer_factor=SYNTHETIC_DEALER_FACTOR,
        rule_rows=_price_rule_rows(),
        readonly_note=(
            "Панель read-only: она показывает текущий прайс и правила, "
            "но не изменяет data/prices.json и ничего не пишет в БД."
        ),
        rules_note=(
            "Правила пока зафиксированы в коде. Редактирование правил "
            "запланировано отдельно в Фазе 4."
        ),
    )


def render_price_overview(prices: dict[str, Any]) -> None:
    """Показать бизнес-карточку текущего прайса и технические детали (свёрнуты)."""

    view_model = build_price_overview_view_model(prices)
    diagnostics = view_model.diagnostics
    errors = [
        issue for issue in diagnostics.validation_issues if issue.level == "error"
    ]
    warnings = [
        issue for issue in diagnostics.validation_issues if issue.level == "warning"
    ]

    # Бизнес-карточка
    st.header("Состояние прайса")

    meta = prices.get("_meta", {}) or {}
    valid_from = diagnostics.valid_from or "не указана"
    sources = [s for s in (meta.get("source_dealer"), meta.get("source_retail")) if s]
    source_str = ", ".join(sources) if sources else "не указан"
    st.caption(f"Дата: {valid_from}  ·  Источник: {source_str}")

    orion_count = sum(
        1 for v in prices.get("options", {}).values() if v.get("individual_calc")
    )
    metric_cols = st.columns(4)
    metric_cols[0].metric("Модели", diagnostics.model_count)
    metric_cols[1].metric("Опции", diagnostics.option_count - orion_count)
    metric_cols[2].metric("ОРИОН", orion_count)
    metric_cols[3].metric("Предупреждений", diagnostics.warning_count)

    if diagnostics.is_expired:
        st.error("Прайс просрочен: дата valid_until уже прошла.")
    elif errors:
        st.error(f"Ошибки в прайсе: {len(errors)}. Перед использованием нужен разбор.")
    elif warnings:
        st.warning("Есть предупреждения, критических ошибок нет.")
    else:
        st.success("Прайс актуален.")

    # Технические детали (свёрнуты по умолчанию)
    with st.expander("Технические детали", expanded=False):
        st.info(view_model.readonly_note)
        _render_metadata(prices, diagnostics)
        _render_structure(diagnostics)
        _render_issues("Errors", errors, "Errors не найдены.")
        _render_issues("Warnings", warnings, "Warnings не найдены.")
        _render_price_problems(diagnostics)
        _render_price_rules(view_model)


def _price_rule_rows() -> list[PriceRuleRow]:
    return [
        PriceRuleRow(
            price_class="A_retail_and_dealer",
            meaning="Модели и дилерские позиции с розницей и дилером РФ.",
            lower_bound="dealer_ru из прайса",
            default_value="retail из прайса",
            upper_bound=f"retail x {MAX_COEFF:g}",
        ),
        PriceRuleRow(
            price_class="B_retail_only",
            meaning="Розничные опции без отдельной дилерской цены.",
            lower_bound=f"retail x {MIN_COEFF_B:g}",
            default_value="retail из прайса",
            upper_bound=f"retail x {MAX_COEFF:g}",
        ),
        PriceRuleRow(
            price_class="C_manual_range",
            meaning="Ручной диапазон цены для сложных позиций.",
            lower_bound="range_min из прайса",
            default_value="price_retail из прайса",
            upper_bound="range_max из прайса",
        ),
        PriceRuleRow(
            price_class="UNKNOWN",
            meaning="Старые опции без price_class, совместимость с JSON.",
            lower_bound=f"retail x {SYNTHETIC_DEALER_FACTOR:g}",
            default_value="retail из прайса",
            upper_bound=f"retail x {MAX_COEFF:g}",
        ),
        PriceRuleRow(
            price_class="on_request",
            meaning="Позиции по запросу без автоматической цены.",
            lower_bound="не применяется",
            default_value="по запросу",
            upper_bound="не применяется",
        ),
    ]


def _render_metadata(
    prices: dict[str, Any],
    diagnostics: PriceDiagnostics,
) -> None:
    meta = prices.get("_meta", {})
    meta = meta if isinstance(meta, dict) else {}
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
    with st.container(border=True):
        st.subheader("Метаданные прайса")
        st.table(
            [{"Поле": key, "Значение": value} for key, value in metadata_rows]
        )


def _render_structure(diagnostics: PriceDiagnostics) -> None:
    with st.container(border=True):
        st.subheader("Структура")
        st.table(
            [
                {
                    "Показатель": "Опции по запросу",
                    "Значение": diagnostics.on_request_count,
                },
                {
                    "Показатель": "Позиции с пустой или нулевой ценой",
                    "Значение": len(diagnostics.zero_price_items),
                },
                {
                    "Показатель": "Модели без полной цены",
                    "Значение": len(diagnostics.models_without_price),
                },
                *[
                    {
                        "Показатель": f"Класс {price_class}",
                        "Значение": count,
                    }
                    for price_class, count
                    in sorted(diagnostics.class_counts.items())
                ],
            ]
        )


def _render_issues(
    title: str,
    issues: list[Any],
    empty_message: str,
) -> None:
    with st.container(border=True):
        st.subheader(title)
        if issues:
            if title == "Errors":
                st.error(f"Найдено ошибок: {len(issues)}")
            else:
                st.warning(f"Найдено предупреждений: {len(issues)}")
            st.table(
                [
                    {
                        "Позиция": issue.item_key,
                        "Поле": issue.field,
                        "Сообщение": issue.message,
                    }
                    for issue in issues
                ]
            )
        else:
            st.success(empty_message)


def _render_price_problems(diagnostics: PriceDiagnostics) -> None:
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


def _render_price_rules(view_model: PriceOverviewViewModel) -> None:
    with st.container(border=True):
        st.subheader("Правила ценовых классов")
        st.caption(view_model.rules_note)
        st.table(
            [
                {
                    "Класс": row.price_class,
                    "Описание": row.meaning,
                    "Нижняя граница": row.lower_bound,
                    "Дефолт": row.default_value,
                    "Верхняя граница": row.upper_bound,
                }
                for row in view_model.rule_rows
            ]
        )
        st.table(
            [
                {"Константа": "VAT_RATE", "Значение": f"{view_model.vat_percent}%"},
                {"Константа": "MAX_COEFF", "Значение": str(view_model.max_coeff)},
                {"Константа": "MIN_COEFF_B", "Значение": str(view_model.min_coeff_b)},
                {
                    "Константа": "SYNTHETIC_DEALER_FACTOR",
                    "Значение": str(view_model.synthetic_dealer_factor),
                },
            ]
        )

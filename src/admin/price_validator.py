"""Структурная валидация canonical price items."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.admin.price_models import PriceItem


IssueLevel = Literal["error", "warning"]


@dataclass(frozen=True)
class ValidationIssue:
    """Одна ошибка или предупреждение по записи прайса."""

    level: IssueLevel
    item_key: str
    field: str
    message: str


def validate_prices(items: list[PriceItem]) -> list[ValidationIssue]:
    """Проверить price items и вернуть все найденные issues."""

    issues: list[ValidationIssue] = []
    for item in items:
        if item.item_type == "model":
            _validate_model(item, issues)
        else:
            _validate_option(item, issues)
    return issues


def _validate_model(item: PriceItem, issues: list[ValidationIssue]) -> None:
    _require_positive(item, "price_retail", item.price_retail, issues)
    _require_positive(item, "price_dealer_ru", item.price_dealer_ru, issues)
    if item.raw_payload.get("data_incomplete"):
        issues.append(
            ValidationIssue(
                level="warning",
                item_key=item.key,
                field="data_incomplete",
                message="Модель помечена как неполная по исходным данным.",
            )
        )


def _validate_option(item: PriceItem, issues: list[ValidationIssue]) -> None:
    if item.on_request:
        return

    if item.price_class == "A_retail_and_dealer":
        _require_positive(item, "price_retail", item.price_retail, issues)
        _require_positive(item, "price_dealer_ru", item.price_dealer_ru, issues)
        return

    if item.price_class == "B_retail_only":
        _require_positive(item, "price_retail", item.price_retail, issues)
        return

    if item.price_class == "C_manual_range":
        _validate_manual_range(item, issues)
        return

    _require_positive(item, "price_retail", item.price_retail, issues)


def _validate_manual_range(
    item: PriceItem, issues: list[ValidationIssue]
) -> None:
    if item.range_min is None:
        issues.append(
            ValidationIssue(
                level="error",
                item_key=item.key,
                field="range_min",
                message="Для C_manual_range нужен range_min.",
            )
        )
    if item.range_max is None:
        issues.append(
            ValidationIssue(
                level="error",
                item_key=item.key,
                field="range_max",
                message="Для C_manual_range нужен range_max.",
            )
        )
    if (
        item.range_min is not None
        and item.range_max is not None
        and item.range_min > item.range_max
    ):
        issues.append(
            ValidationIssue(
                level="error",
                item_key=item.key,
                field="range_min",
                message="range_min не должен быть больше range_max.",
            )
        )


def _require_positive(
    item: PriceItem,
    field: str,
    value: int | None,
    issues: list[ValidationIssue],
) -> None:
    if value is not None and value > 0:
        return
    issues.append(
        ValidationIssue(
            level="error",
            item_key=item.key,
            field=field,
            message="Поле должно быть положительным числом.",
        )
    )

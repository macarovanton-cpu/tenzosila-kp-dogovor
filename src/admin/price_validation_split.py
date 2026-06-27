"""Разделение результатов validate_prices на блокеры и предупреждения."""
from __future__ import annotations

from dataclasses import dataclass

from src.admin.price_models import PriceItem
from src.admin.price_validator import ValidationIssue, validate_prices


@dataclass(frozen=True)
class ValidationSplit:
    """Результат split-валидации: блокеры и предупреждения."""

    blockers: list[ValidationIssue]
    warnings: list[ValidationIssue]

    @property
    def has_blockers(self) -> bool:
        return len(self.blockers) > 0


def split_validation(
    items: list[PriceItem],
    *,
    old_items: list[PriceItem] | None = None,
) -> ValidationSplit:
    """Разделить issues validate_prices на блокеры и предупреждения.

    Блокеры запрещают применение прайса. Предупреждения показываются
    менеджеру, но не блокируют запись.
    """
    blockers: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    # Стандартный валидатор: error → блокер, warning → предупреждение
    for issue in validate_prices(items):
        if issue.level == "error":
            blockers.append(issue)
        else:
            warnings.append(issue)

    # Блокер: розница < дилера (перепутаны или ошибка ввода)
    for item in items:
        if (
            item.price_retail is not None
            and item.price_dealer_ru is not None
            and item.price_retail > 0
            and item.price_dealer_ru > 0
            and item.price_retail < item.price_dealer_ru
        ):
            blockers.append(
                ValidationIssue(
                    level="error",
                    item_key=item.key,
                    field="price_retail",
                    message="Розничная цена меньше дилерской.",
                )
            )

    # Блокер: пустой ключ позиции (UI требует уникальный непустой ключ для новых строк)
    for item in items:
        if item.key.strip() == "":
            blockers.append(
                ValidationIssue(
                    level="error",
                    item_key=item.key,
                    field="key",
                    message="Пустой ключ позиции.",
                )
            )

    # Блокер: дублирующиеся ключи
    seen: set[str] = set()
    reported: set[str] = set()
    for item in items:
        if item.key in seen and item.key not in reported:
            blockers.append(
                ValidationIssue(
                    level="error",
                    item_key=item.key,
                    field="key",
                    message="Дублирующийся ключ.",
                )
            )
            reported.add(item.key)
        seen.add(item.key)

    # Сравнительные предупреждения (только если передан старый прайс)
    if old_items is not None:
        old_by_key = {item.key: item for item in old_items}

        for item in items:
            if item.key not in old_by_key:
                warnings.append(
                    ValidationIssue(
                        level="warning",
                        item_key=item.key,
                        field="key",
                        message="Новая позиция, отсутствовавшая в предыдущем прайсе.",
                    )
                )
                continue

            old = old_by_key[item.key]
            had_price = old.price_retail is not None or old.price_dealer_ru is not None
            if item.on_request and not old.on_request and had_price:
                warnings.append(
                    ValidationIssue(
                        level="warning",
                        item_key=item.key,
                        field="on_request",
                        message="Позиция стала «по запросу», раньше имела цену.",
                    )
                )

    return ValidationSplit(blockers=blockers, warnings=warnings)

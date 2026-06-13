"""Read-only диагностика текущего JSON-прайса."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.admin.price_normalizer import normalize_prices
from src.admin.price_validator import ValidationIssue, validate_prices
from src.config import PRICES_JSON


@dataclass(frozen=True)
class DiagnosticItem:
    """Ссылка на проблемное поле позиции прайса."""

    item_type: str
    item_key: str
    field: str
    message: str


@dataclass(frozen=True)
class PriceDiagnostics:
    """Сводка здоровья прайса."""

    model_count: int
    option_count: int
    class_counts: dict[str, int]
    on_request_count: int
    valid_from: str | None
    valid_until: str | None
    is_expired: bool
    validation_issues: list[ValidationIssue]
    zero_price_items: list[DiagnosticItem]
    models_without_price: list[str]

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.validation_issues if issue.level == "error")

    @property
    def warning_count(self) -> int:
        return sum(
            1 for issue in self.validation_issues if issue.level == "warning"
        )


def diagnose_prices(
    prices: dict[str, Any],
    *,
    today: date | None = None,
) -> PriceDiagnostics:
    """Вернуть read-only диагностику структуры и цен прайса."""

    current_date = today or date.today()
    items = normalize_prices(prices)
    models = [item for item in items if item.item_type == "model"]
    options = [item for item in items if item.item_type == "option"]
    valid_from = _valid_from(prices)
    valid_until = _valid_until(prices)
    validation_issues = validate_prices(items)
    validation_issues.extend(_expiry_warnings(valid_until))

    return PriceDiagnostics(
        model_count=len(models),
        option_count=len(options),
        class_counts=dict(Counter(item.price_class for item in options)),
        on_request_count=sum(1 for item in options if item.on_request),
        valid_from=valid_from,
        valid_until=valid_until,
        is_expired=_is_expired(valid_until, current_date),
        validation_issues=validation_issues,
        zero_price_items=_zero_price_items(items),
        models_without_price=_models_without_price(models),
    )


def format_diagnostics(diagnostics: PriceDiagnostics) -> str:
    """Сформатировать диагностику для CLI."""

    class_lines = [
        f"  {name}: {count}"
        for name, count in sorted(diagnostics.class_counts.items())
    ]
    lines = [
        "Price diagnostics",
        f"models: {diagnostics.model_count}",
        f"options: {diagnostics.option_count}",
        "classes:",
        *class_lines,
        f"on_request: {diagnostics.on_request_count}",
        f"valid_from: {diagnostics.valid_from or 'unknown'}",
        f"valid_until: {diagnostics.valid_until or 'unknown'}",
        f"expired: {'yes' if diagnostics.is_expired else 'no'}",
        f"errors: {diagnostics.error_count}",
        f"warnings: {diagnostics.warning_count}",
        f"zero_price_items: {len(diagnostics.zero_price_items)}",
        f"models_without_price: {len(diagnostics.models_without_price)}",
    ]
    return "\n".join(lines)


def load_prices_file(path: Path = PRICES_JSON) -> dict[str, Any]:
    """Прочитать JSON-прайс без Streamlit runtime."""

    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose prices.json")
    parser.add_argument(
        "path",
        nargs="?",
        default=str(PRICES_JSON),
        help="Path to prices.json candidate",
    )
    args = parser.parse_args(argv)
    diagnostics = diagnose_prices(load_prices_file(Path(args.path)))
    print(format_diagnostics(diagnostics))
    return 0


def _valid_from(prices: dict[str, Any]) -> str | None:
    value = prices.get("_meta", {}).get("valid_from")
    return str(value) if value else None


def _valid_until(prices: dict[str, Any]) -> str | None:
    value = prices.get("_meta", {}).get("valid_until")
    return str(value) if value else None


def _is_expired(valid_until: str | None, today: date) -> bool:
    if not valid_until:
        return False
    try:
        return date.fromisoformat(valid_until) < today
    except ValueError:
        return False


def _expiry_warnings(valid_until: str | None) -> list[ValidationIssue]:
    if valid_until:
        return []
    return [
        ValidationIssue(
            level="warning",
            item_key="_meta",
            field="valid_until_missing",
            message="В _meta нет valid_until: срок окончания действия прайса неизвестен.",
        )
    ]


def _zero_price_items(items: list) -> list[DiagnosticItem]:
    result = []
    for item in items:
        if item.on_request:
            continue
        if item.price_retail is None or item.price_retail <= 0:
            result.append(
                DiagnosticItem(
                    item_type=item.item_type,
                    item_key=item.key,
                    field="price_retail",
                    message="Пустая или нулевая розничная цена.",
                )
            )
    return result


def _models_without_price(items: list) -> list[str]:
    return [
        item.key
        for item in items
        if _is_empty_price(item.price_retail)
        or _is_empty_price(item.price_dealer_ru)
    ]


def _is_empty_price(value: int | None) -> bool:
    return value is None or value <= 0


if __name__ == "__main__":
    raise SystemExit(main())

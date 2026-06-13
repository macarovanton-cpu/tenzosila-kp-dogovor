"""Сервис проверки загруженного JSON-прайса без Streamlit runtime."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.admin.price_diff import PriceDiff, diff_prices
from src.admin.price_normalizer import normalize_prices
from src.admin.price_validator import ValidationIssue, validate_prices


@dataclass(frozen=True)
class PriceUploadAnalysis:
    """Результат проверки загруженного прайса."""

    candidate_prices: dict[str, Any] | None
    validation_issues: list[ValidationIssue]
    diff: PriceDiff | None
    diff_summary: dict[str, int]
    download_json: str | None
    parse_error: str | None = None

    @property
    def errors(self) -> list[ValidationIssue]:
        return [
            issue for issue in self.validation_issues if issue.level == "error"
        ]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [
            issue for issue in self.validation_issues if issue.level == "warning"
        ]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def can_download(self) -> bool:
        return self.parse_error is None and self.error_count == 0


def analyze_uploaded_price_json(
    uploaded_bytes: bytes,
    *,
    current_prices: dict[str, Any],
) -> PriceUploadAnalysis:
    """Проверить загруженный JSON и сравнить с текущим прайсом."""

    candidate_prices, parse_error = _parse_json(uploaded_bytes)
    if parse_error:
        return _blocked_result(parse_error)

    assert candidate_prices is not None
    try:
        candidate_items = normalize_prices(candidate_prices)
        current_items = normalize_prices(current_prices)
    except (TypeError, ValueError) as exc:
        return _blocked_result(f"Не удалось нормализовать JSON-прайс: {exc}")

    issues = validate_prices(candidate_items)
    errors = [issue for issue in issues if issue.level == "error"]
    price_diff = None if errors else diff_prices(current_items, candidate_items)
    download_json = None if errors else _dump_json(candidate_prices)

    return PriceUploadAnalysis(
        candidate_prices=candidate_prices,
        validation_issues=issues,
        diff=price_diff,
        diff_summary=_diff_summary(price_diff),
        download_json=download_json,
    )


def _parse_json(uploaded_bytes: bytes) -> tuple[dict[str, Any] | None, str | None]:
    try:
        parsed = json.loads(uploaded_bytes.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        return None, f"Не удалось прочитать файл как UTF-8 JSON: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"Не удалось разобрать JSON: {exc.msg} (строка {exc.lineno})"

    if not isinstance(parsed, dict):
        return None, "Корень JSON-прайса должен быть объектом."
    return parsed, None


def _blocked_result(parse_error: str) -> PriceUploadAnalysis:
    return PriceUploadAnalysis(
        candidate_prices=None,
        validation_issues=[],
        diff=None,
        diff_summary={"added": 0, "removed": 0, "changed": 0},
        download_json=None,
        parse_error=parse_error,
    )


def _dump_json(prices: dict[str, Any]) -> str:
    return json.dumps(prices, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _diff_summary(price_diff: PriceDiff | None) -> dict[str, int]:
    if price_diff is None:
        return {"added": 0, "removed": 0, "changed": 0}
    return {
        "added": len(price_diff.added),
        "removed": len(price_diff.removed),
        "changed": len(price_diff.changed),
    }

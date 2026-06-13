"""Тесты структурного валидатора canonical price items."""
from __future__ import annotations

from src.admin.price_models import PriceItem
from src.admin.price_normalizer import normalize_prices
from src.admin.price_validator import ValidationIssue, validate_prices


def _item(
    *,
    item_type: str = "option",
    key: str = "item",
    price_retail: int | None = 1000,
    price_dealer_ru: int | None = 900,
    price_class: str = "A_retail_and_dealer",
    on_request: bool = False,
    range_min: int | None = None,
    range_max: int | None = None,
    raw_payload: dict | None = None,
) -> PriceItem:
    return PriceItem(
        item_type=item_type,  # type: ignore[arg-type]
        key=key,
        label=key,
        price_retail=price_retail,
        price_dealer_ru=price_dealer_ru,
        discount_pct=8,
        price_class=price_class,
        on_request=on_request,
        allow_customer_value=False,
        range_min=range_min,
        range_max=range_max,
        applies_to_lines=[],
        applies_to_lengths=[],
        raw_payload=raw_payload or {},
    )


def _errors(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    return [issue for issue in issues if issue.level == "error"]


def _warnings(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    return [issue for issue in issues if issue.level == "warning"]


def test_current_prices_have_no_errors(prices: dict) -> None:
    items = normalize_prices(prices)

    issues = validate_prices(items)

    assert _errors(issues) == []
    assert len(_warnings(issues)) == 4


def test_validator_collects_structured_errors_without_short_circuit() -> None:
    items = [
        _item(item_type="model", key="bad_model", price_dealer_ru=None),
        _item(key="bad_a", price_dealer_ru=None),
        _item(key="bad_b", price_retail=0, price_dealer_ru=None,
              price_class="B_retail_only"),
        _item(key="bad_c", price_class="C_manual_range", range_min=20,
              range_max=10),
    ]

    issues = validate_prices(items)
    issue_keys = {(issue.item_key, issue.field) for issue in _errors(issues)}

    assert issue_keys == {
        ("bad_model", "price_dealer_ru"),
        ("bad_a", "price_dealer_ru"),
        ("bad_b", "price_retail"),
        ("bad_c", "range_min"),
    }
    assert all(issue.message for issue in issues)


def test_on_request_option_allows_empty_price() -> None:
    items = [
        _item(
            key="ask_later",
            price_retail=None,
            price_dealer_ru=None,
            price_class="B_retail_only",
            on_request=True,
        )
    ]

    assert validate_prices(items) == []


def test_data_incomplete_model_is_warning_not_error() -> None:
    items = [
        _item(
            item_type="model",
            key="incomplete_model",
            raw_payload={"data_incomplete": True},
        )
    ]

    issues = validate_prices(items)

    assert _errors(issues) == []
    assert [(issue.level, issue.item_key, issue.field) for issue in issues] == [
        ("warning", "incomplete_model", "data_incomplete")
    ]


def test_unknown_option_requires_retail_for_synthetic_dealer() -> None:
    items = [
        _item(
            key="unknown_without_retail",
            price_retail=None,
            price_dealer_ru=None,
            price_class="UNKNOWN",
        )
    ]

    issues = validate_prices(items)

    assert [(issue.item_key, issue.field) for issue in _errors(issues)] == [
        ("unknown_without_retail", "price_retail")
    ]

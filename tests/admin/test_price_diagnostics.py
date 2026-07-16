"""Тесты read-only диагностики прайса."""
from __future__ import annotations

from datetime import date

from src.admin.price_diagnostics import diagnose_prices, format_diagnostics


def _sample_prices(
    *,
    valid_from: str = "2026-01-01",
    valid_until: str | None = None,
) -> dict:
    meta = {"valid_from": valid_from}
    if valid_until is not None:
        meta["valid_until"] = valid_until
    return {
        "_meta": meta,
        "models": {
            "model_ok": {"retail": 1000, "dealer_ru": 900},
            "model_missing": {"retail": 0, "dealer_ru": 900},
        },
        "options": {
            "option_a": {
                "label": "A",
                "price_retail": 1000,
                "price_dealer_ru": 900,
                "price_class": "A_retail_and_dealer",
            },
            "option_b_zero": {
                "label": "B",
                "price_retail": 0,
                "price_dealer_ru": None,
                "price_class": "B_retail_only",
            },
            "option_request": {
                "label": "Request",
                "price_retail": None,
                "price_dealer_ru": None,
                "price_class": "B_retail_only",
                "on_request": True,
            },
        },
    }


def test_diagnose_prices_reports_real_counts_and_classes(prices: dict) -> None:
    diagnostics = diagnose_prices(prices, today=date(2026, 6, 12))

    assert diagnostics.model_count == 53
    assert diagnostics.option_count == 89
    assert diagnostics.class_counts == {
        "A_retail_and_dealer": 20,
        "B_retail_only": 52,
        "C_manual_range": 12,
        "UNKNOWN": 5,
    }
    assert diagnostics.on_request_count == 1
    assert diagnostics.is_expired is False
    assert diagnostics.error_count == 0
    assert any(
        issue.level == "warning" and issue.field == "valid_until_missing"
        for issue in diagnostics.validation_issues
    )


def test_diagnose_prices_requires_valid_until_for_expiry() -> None:
    diagnostics = diagnose_prices(
        _sample_prices(valid_from="2026-01-01"),
        today=date(2026, 6, 12),
    )

    assert diagnostics.is_expired is False
    assert [
        (issue.level, issue.item_key, issue.field)
        for issue in diagnostics.validation_issues
        if issue.field == "valid_until_missing"
    ] == [("warning", "_meta", "valid_until_missing")]


def test_diagnose_prices_marks_only_past_valid_until_as_expired() -> None:
    old_prices = _sample_prices(valid_until="2026-06-11")
    fresh_prices = _sample_prices(valid_until="2026-06-12")

    old_diagnostics = diagnose_prices(old_prices, today=date(2026, 6, 12))
    fresh_diagnostics = diagnose_prices(fresh_prices, today=date(2026, 6, 12))

    assert old_diagnostics.is_expired is True
    assert fresh_diagnostics.is_expired is False


def test_diagnose_prices_lists_zero_prices_except_on_request() -> None:
    diagnostics = diagnose_prices(_sample_prices(), today=date(2026, 6, 12))

    assert [(item.item_type, item.item_key, item.field)
            for item in diagnostics.zero_price_items] == [
        ("model", "model_missing", "price_retail"),
        ("option", "option_b_zero", "price_retail"),
    ]
    assert "option_request" not in [
        item.item_key for item in diagnostics.zero_price_items
    ]


def test_diagnose_prices_lists_models_without_price() -> None:
    diagnostics = diagnose_prices(_sample_prices(), today=date(2026, 6, 12))

    assert diagnostics.models_without_price == ["model_missing"]


def test_format_diagnostics_contains_summary() -> None:
    diagnostics = diagnose_prices(_sample_prices(), today=date(2026, 6, 12))

    summary = format_diagnostics(diagnostics)

    assert "models: 2" in summary
    assert "options: 3" in summary
    assert "valid_until: unknown" in summary
    assert "expired: no" in summary
    assert "errors: 2" in summary
    assert "warnings: 1" in summary

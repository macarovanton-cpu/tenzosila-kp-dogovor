"""Тесты read-only view-model панели прайса и правил."""
from __future__ import annotations

from src.admin.price_overview_view import build_price_overview_view_model
from src.config import (
    MAX_COEFF,
    MIN_COEFF_B,
    SYNTHETIC_DEALER_FACTOR,
    VAT_RATE,
)


def test_price_overview_view_model_shows_configured_rules(prices: dict) -> None:
    view_model = build_price_overview_view_model(prices)

    assert view_model.vat_rate == VAT_RATE
    assert view_model.max_coeff == MAX_COEFF
    assert view_model.min_coeff_b == MIN_COEFF_B
    assert view_model.synthetic_dealer_factor == SYNTHETIC_DEALER_FACTOR
    assert view_model.vat_percent == 22

    rule_classes = {row.price_class for row in view_model.rule_rows}
    assert rule_classes == {
        "A_retail_and_dealer",
        "B_retail_only",
        "C_manual_range",
        "UNKNOWN",
        "on_request",
    }

    assert view_model.diagnostics.model_count == 45
    assert view_model.diagnostics.option_count == 65
    assert "read-only" in view_model.readonly_note
    assert "Фазе 4" in view_model.rules_note

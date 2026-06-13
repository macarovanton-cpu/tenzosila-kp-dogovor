"""Тесты нормализации текущего data/prices.json в canonical price items."""
from __future__ import annotations

from collections import Counter

from src.admin.price_normalizer import normalize_prices


def _find_item(items: list, item_type: str, key: str):
    for item in items:
        if item.item_type == item_type and item.key == key:
            return item
    raise AssertionError(f"Item {item_type}:{key} not found")


def test_normalize_prices_keeps_model_and_option_counts(prices: dict) -> None:
    items = normalize_prices(prices)

    by_type = Counter(item.item_type for item in items)

    assert len(items) == 110
    assert by_type == {"model": 45, "option": 65}


def test_normalize_prices_reports_option_classes(prices: dict) -> None:
    items = normalize_prices(prices)
    options = [item for item in items if item.item_type == "option"]

    by_class = Counter(item.price_class for item in options)
    on_request_count = sum(1 for item in options if item.on_request)

    assert by_class == {
        "A_retail_and_dealer": 20,
        "B_retail_only": 36,
        "C_manual_range": 4,
        "UNKNOWN": 5,
    }
    assert on_request_count == 1


def test_normalize_prices_maps_model_fields_without_losing_payload(
    prices: dict,
) -> None:
    items = normalize_prices(prices)

    model = _find_item(items, "model", "vesta-фл-60-18")

    assert model.label == "vesta-фл-60-18"
    assert model.price_retail == 1668432
    assert model.price_dealer_ru == 1534958
    assert model.price_class == "A_retail_and_dealer"
    assert model.raw_payload == prices["models"]["vesta-фл-60-18"]


def test_normalize_prices_maps_option_fields_without_losing_payload(
    prices: dict,
) -> None:
    items = normalize_prices(prices)

    option = _find_item(items, "option", "ramp_set_f_s")

    assert option.label == "Комплект пандусов под весы ВЕСТА-Ф/С (L=3,9м)"
    assert option.price_retail == 380000
    assert option.price_dealer_ru == 349600
    assert option.price_class == "A_retail_and_dealer"
    assert option.applies_to_lines == ["Ф", "С", "П"]
    assert option.applies_to_lengths == [16, 18, 20, 22, 24]
    assert option.raw_payload == prices["options"]["ramp_set_f_s"]


def test_normalize_prices_maps_manual_range_and_unknown_options(
    prices: dict,
) -> None:
    items = normalize_prices(prices)

    manual = _find_item(items, "option", "install_default")
    unknown = _find_item(items, "option", "frame_22")

    assert manual.price_class == "C_manual_range"
    assert manual.range_min == 100000
    assert manual.range_max == 1000000
    assert manual.allow_customer_value is False
    assert unknown.price_class == "UNKNOWN"
    assert unknown.price_retail == 162500


def test_normalize_prices_preserves_on_request_option(prices: dict) -> None:
    items = normalize_prices(prices)

    option = _find_item(items, "option", "canopy_turnkey_24")

    assert option.price_class == "B_retail_only"
    assert option.on_request is True
    assert option.price_retail is None
    assert option.raw_payload["on_request"] is True

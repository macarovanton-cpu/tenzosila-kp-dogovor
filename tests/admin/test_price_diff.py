"""Тесты diff двух нормализованных прайсов."""
from __future__ import annotations

from dataclasses import replace

from src.admin.price_diff import diff_prices
from src.admin.price_models import PriceItem


def _item(
    key: str,
    *,
    item_type: str = "option",
    price_retail: int | None = 1000,
    price_dealer_ru: int | None = 900,
    price_class: str = "A_retail_and_dealer",
    range_min: int | None = None,
    range_max: int | None = None,
    on_request: bool = False,
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
        raw_payload={},
    )


def test_diff_prices_returns_empty_diff_for_equal_items() -> None:
    item = _item("same")

    diff = diff_prices([item], [item])

    assert diff.added == []
    assert diff.removed == []
    assert diff.changed == []


def test_diff_prices_detects_added_and_removed_by_type_and_key() -> None:
    old_model = _item("shared", item_type="model")
    new_option = _item("shared", item_type="option")

    diff = diff_prices([old_model], [new_option])

    assert [(item.item_type, item.key) for item in diff.added] == [
        ("option", "shared")
    ]
    assert [(item.item_type, item.key) for item in diff.removed] == [
        ("model", "shared")
    ]
    assert diff.changed == []


def test_diff_prices_detects_changed_significant_fields() -> None:
    old_item = _item(
        "changed",
        price_retail=1000,
        price_dealer_ru=900,
        price_class="A_retail_and_dealer",
        range_min=100,
        range_max=200,
    )
    new_item = replace(
        old_item,
        price_retail=1100,
        price_dealer_ru=950,
        price_class="C_manual_range",
        range_min=150,
        range_max=250,
        on_request=True,
    )

    diff = diff_prices([old_item], [new_item])

    assert len(diff.changed) == 1
    changed = diff.changed[0]
    assert (changed.item_type, changed.item_key) == ("option", "changed")
    assert [(change.field, change.old_value, change.new_value)
            for change in changed.changes] == [
        ("price_retail", 1000, 1100),
        ("price_dealer_ru", 900, 950),
        ("price_class", "A_retail_and_dealer", "C_manual_range"),
        ("range_min", 100, 150),
        ("range_max", 200, 250),
        ("on_request", False, True),
    ]


def test_diff_prices_ignores_non_significant_fields() -> None:
    old_item = _item("same_price")
    new_item = replace(
        old_item,
        label="Новое описание без изменения цены",
        applies_to_lengths=[18, 20],
        raw_payload={"note": "changed"},
    )

    diff = diff_prices([old_item], [new_item])

    assert diff.changed == []

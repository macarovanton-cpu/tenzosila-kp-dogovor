"""Тесты разделения валидации прайса на блокеры и предупреждения."""
from __future__ import annotations

from src.admin.price_models import PriceItem
from src.admin.price_validation_split import split_validation


def _item(
    *,
    item_type: str = "option",
    key: str = "item",
    price_retail: int | None = 1000,
    price_dealer_ru: int | None = 900,
    price_class: str = "A_retail_and_dealer",
    on_request: bool = False,
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
        range_min=None,
        range_max=None,
        applies_to_lines=[],
        applies_to_lengths=[],
        raw_payload=raw_payload or {},
    )


# ---------------------------------------------------------------------------
# Блокеры
# ---------------------------------------------------------------------------


def test_none_price_when_not_on_request_is_blocker() -> None:
    items = [_item(key="no_price", price_retail=None, price_class="B_retail_only")]

    result = split_validation(items)

    assert result.has_blockers
    assert any(i.item_key == "no_price" for i in result.blockers)


def test_none_price_when_on_request_is_not_blocker_nor_warning() -> None:
    items = [
        _item(
            key="ask_later",
            price_retail=None,
            price_dealer_ru=None,
            price_class="B_retail_only",
            on_request=True,
        )
    ]

    result = split_validation(items)

    assert not result.has_blockers
    assert result.warnings == []


def test_retail_less_than_dealer_is_blocker() -> None:
    items = [_item(key="swapped", price_retail=800, price_dealer_ru=900)]

    result = split_validation(items)

    assert result.has_blockers
    blocker_fields = {(i.item_key, i.field) for i in result.blockers}
    assert ("swapped", "price_retail") in blocker_fields


def test_duplicate_key_is_blocker() -> None:
    items = [
        _item(key="dup"),
        _item(key="dup"),
    ]

    result = split_validation(items)

    assert result.has_blockers
    assert any(i.item_key == "dup" and i.field == "key" for i in result.blockers)


# ---------------------------------------------------------------------------
# Предупреждения
# ---------------------------------------------------------------------------


def test_new_position_is_warning_when_old_items_given() -> None:
    old = [_item(key="existing")]
    new = [_item(key="existing"), _item(key="brand_new")]

    result = split_validation(new, old_items=old)

    assert not result.has_blockers
    assert any(
        i.item_key == "brand_new" and i.field == "key" for i in result.warnings
    )


def test_data_incomplete_is_warning() -> None:
    items = [
        _item(
            item_type="model",
            key="incomplete",
            raw_payload={"data_incomplete": True},
        )
    ]

    result = split_validation(items)

    assert not result.has_blockers
    assert any(i.item_key == "incomplete" and i.field == "data_incomplete" for i in result.warnings)


def test_became_on_request_is_warning() -> None:
    old = [_item(key="opt", price_retail=1000, on_request=False)]
    new = [_item(key="opt", price_retail=None, on_request=True)]

    result = split_validation(new, old_items=old)

    assert not result.has_blockers
    assert any(i.item_key == "opt" and i.field == "on_request" for i in result.warnings)


# ---------------------------------------------------------------------------
# Чистый набор
# ---------------------------------------------------------------------------


def test_clean_items_have_no_blockers() -> None:
    items = [
        _item(key="a", price_retail=1000, price_dealer_ru=900),
        _item(key="b", price_retail=2000, price_dealer_ru=1800),
    ]

    result = split_validation(items)

    assert not result.has_blockers
    assert result.blockers == []

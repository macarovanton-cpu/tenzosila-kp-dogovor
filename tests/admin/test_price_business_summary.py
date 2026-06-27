"""Тесты бизнес-сводки изменений прайса."""
from __future__ import annotations

from dataclasses import replace

import pytest

from src.admin.price_business_summary import build_business_summary
from src.admin.price_models import PriceItem


def _item(
    key: str,
    *,
    item_type: str = "option",
    label: str | None = None,
    price_retail: int | None = 1000,
    price_dealer_ru: int | None = 900,
    on_request: bool = False,
) -> PriceItem:
    return PriceItem(
        item_type=item_type,  # type: ignore[arg-type]
        key=key,
        label=label or key,
        price_retail=price_retail,
        price_dealer_ru=price_dealer_ru,
        discount_pct=8,
        price_class="A_retail_and_dealer",
        on_request=on_request,
        allow_customer_value=False,
        range_min=None,
        range_max=None,
        applies_to_lines=[],
        applies_to_lengths=[],
        raw_payload={},
    )


# ---------------------------------------------------------------------------
# Пустой diff
# ---------------------------------------------------------------------------

def test_empty_diff_produces_empty_summary() -> None:
    item = _item("same")
    summary = build_business_summary([item], [item])

    assert summary.price_up == []
    assert summary.price_down == []
    assert summary.added == []
    assert summary.removed == []
    assert summary.to_on_request == []


# ---------------------------------------------------------------------------
# Подорожание и процент от старой цены
# ---------------------------------------------------------------------------

def test_price_up_detected_and_pct_from_old_price() -> None:
    old = _item("m1", price_retail=100_000)
    new = replace(old, price_retail=110_000)

    summary = build_business_summary([old], [new])

    assert len(summary.price_up) == 1
    entry = summary.price_up[0]
    assert entry.key == "m1"
    assert entry.old_value == 100_000
    assert entry.new_value == 110_000
    assert entry.delta_pct == pytest.approx(10.0)
    assert summary.price_down == []


# ---------------------------------------------------------------------------
# Подешевление и процент от старой цены
# ---------------------------------------------------------------------------

def test_price_down_detected_and_pct_from_old_price() -> None:
    old = _item("m2", price_retail=200_000)
    new = replace(old, price_retail=180_000)

    summary = build_business_summary([old], [new])

    assert len(summary.price_down) == 1
    entry = summary.price_down[0]
    assert entry.old_value == 200_000
    assert entry.new_value == 180_000
    assert entry.delta_pct == pytest.approx(-10.0)
    assert summary.price_up == []


# ---------------------------------------------------------------------------
# Переход в «по запросу» — в to_on_request, НЕ в price_down
# ---------------------------------------------------------------------------

def test_on_request_transition_goes_to_on_request_not_price_down() -> None:
    old = _item("svc1", price_retail=50_000, on_request=False)
    new = replace(old, on_request=True, price_retail=None)

    summary = build_business_summary([old], [new])

    assert len(summary.to_on_request) == 1
    entry = summary.to_on_request[0]
    assert entry.key == "svc1"
    assert entry.old_value == 50_000
    assert entry.new_value is None
    assert entry.delta_pct is None

    assert summary.price_down == []
    assert summary.price_up == []


# ---------------------------------------------------------------------------
# Допуск ±1 руб не попадает в price_up/price_down
# ---------------------------------------------------------------------------

def test_rounding_tolerance_1rub_not_in_price_up() -> None:
    old = _item("r1", price_retail=500_000)
    new = replace(old, price_retail=500_001)

    summary = build_business_summary([old], [new])

    assert summary.price_up == []
    assert summary.price_down == []


def test_rounding_tolerance_minus1rub_not_in_price_down() -> None:
    old = _item("r2", price_retail=500_000)
    new = replace(old, price_retail=499_999)

    summary = build_business_summary([old], [new])

    assert summary.price_down == []
    assert summary.price_up == []


def test_2rub_change_is_significant() -> None:
    """Ровно 2 рубля — уже значимое изменение, за порогом допуска."""
    old = _item("r3", price_retail=500_000)
    new = replace(old, price_retail=500_002)

    summary = build_business_summary([old], [new])

    assert len(summary.price_up) == 1


# ---------------------------------------------------------------------------
# Новые и удалённые позиции
# ---------------------------------------------------------------------------

def test_added_item() -> None:
    existing = _item("e1")
    new_item = _item("n1", label="Новая опция", price_retail=30_000)

    summary = build_business_summary([existing], [existing, new_item])

    assert len(summary.added) == 1
    entry = summary.added[0]
    assert entry.key == "n1"
    assert entry.label == "Новая опция"
    assert entry.old_value is None
    assert entry.new_value == 30_000


def test_removed_item() -> None:
    existing = _item("e1")
    old_only = _item("del1", label="Удалённая опция", price_retail=20_000)

    summary = build_business_summary([existing, old_only], [existing])

    assert len(summary.removed) == 1
    entry = summary.removed[0]
    assert entry.key == "del1"
    assert entry.old_value == 20_000
    assert entry.new_value is None


# ---------------------------------------------------------------------------
# Комплексный сценарий: несколько изменений одновременно
# ---------------------------------------------------------------------------

def test_complex_diff_groups_correctly() -> None:
    up = _item("up1", price_retail=100_000)
    down = _item("down1", price_retail=200_000)
    on_req = _item("req1", price_retail=50_000, on_request=False)
    added_item = _item("new1", price_retail=10_000)
    removed_item = _item("old1", price_retail=15_000)
    unchanged = _item("same1", price_retail=999_000)

    old_items = [up, down, on_req, removed_item, unchanged]
    new_items = [
        replace(up, price_retail=120_000),
        replace(down, price_retail=180_000),
        replace(on_req, on_request=True, price_retail=None),
        added_item,
        unchanged,
    ]

    summary = build_business_summary(old_items, new_items)

    assert {e.key for e in summary.price_up} == {"up1"}
    assert {e.key for e in summary.price_down} == {"down1"}
    assert {e.key for e in summary.to_on_request} == {"req1"}
    assert {e.key for e in summary.added} == {"new1"}
    assert {e.key for e in summary.removed} == {"old1"}


# ---------------------------------------------------------------------------
# None цены — не крашит, позиция пропускается
# ---------------------------------------------------------------------------

def test_none_price_retail_skipped_safely() -> None:
    old = _item("null1", price_retail=None)
    new = replace(old, price_dealer_ru=500)  # изменение не-retail поля

    # Не должно упасть, позиция не попадает ни в одну группу
    summary = build_business_summary([old], [new])

    assert summary.price_up == []
    assert summary.price_down == []

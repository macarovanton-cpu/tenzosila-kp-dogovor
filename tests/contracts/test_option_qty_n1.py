"""Д08 (N1): цена опции в снапшоте — за единицу; сумма договора = сумма КП."""
from __future__ import annotations

from collections import Counter

from src.contracts.from_kp import (
    _fmt,
    build_spec_rows_from_snapshot,
    build_specification_from_kp_snapshot,
    build_specification_items,
)
from src.contracts.supply_filler import _supply_spec_rows
from src.data_loader import load_models, load_payment_terms, load_prices
from src.spec_builder import build_spec_items
from tests.test_kp_restore import _kp_row
from tests.test_validation import _valid_state

PRICES, MODELS = load_prices(), load_models()


def _opt(price: int, qty: int = 1) -> dict:
    return {"enabled": True, "price": price, "qty": qty, "customer_side": False}


def _by_group(items: list[dict]) -> Counter:
    groups: Counter = Counter()
    for it in items:
        groups[it["payment_group"]] += it["total"]
    return groups


def _case(options: dict) -> tuple[dict, list[dict], list[dict]]:
    state = _valid_state()
    state["options"] = options
    return _kp_row(state), build_spec_items(state, PRICES, MODELS), state


def test_ramps_x2_kbu_x3_spec_sums_equal_kp():
    row, kp_items, _ = _case({
        "ramp_set_f_s": _opt(380_000, 2),
        "kbu_p06_44_18": _opt(400_000, 3),
        "install_default": _opt(180_000),
    })
    items = build_specification_items(row, PRICES)
    ramps = next(it for it in items if it["id"] == "pandus")
    assert (ramps["quantity"], ramps["price_per_unit"], ramps["total"]) == (2, 380_000, 760_000)
    assert sum(it["total"] for it in items) == sum(it["total"] for it in kp_items)
    assert _by_group(items) == _by_group(kp_items)  # оплата по группам сходится

    rows = build_spec_rows_from_snapshot(row, PRICES)
    assert sum(r["price"] for r in rows) == sum(it["total"] for it in kp_items)
    spec = build_specification_from_kp_snapshot(row, PRICES, MODELS, load_payment_terms())
    assert spec["СПЕЦ_ИТОГО"] == _fmt(sum(it["total"] for it in kp_items))


def test_supply_kbu_x3_sum_equals_kp():
    row, kp_items, _ = _case({"kbu_p06_44_18": _opt(400_000, 3), "ramp_set_f_s": _opt(380_000, 2)})
    total, rows = _supply_spec_rows(build_specification_items(row, PRICES), "Весы")
    assert total == sum(it["total"] for it in kp_items) and len(rows) == 1

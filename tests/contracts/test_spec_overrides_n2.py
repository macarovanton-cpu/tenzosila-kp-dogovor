"""Д09 (N2): правки таблицы КП (цена/кол-во, в т. ч. модели) доходят до договора."""
from __future__ import annotations

from collections import Counter

from src.contracts.from_kp import (
    _fmt,
    build_spec_rows_from_snapshot,
    build_specification_from_kp_snapshot,
    build_specification_items,
)
from src.data_loader import load_models, load_payment_terms, load_prices
from src.spec_builder import build_spec_items
from tests.test_kp_restore import _kp_row
from tests.test_validation import _valid_state

PRICES, MODELS = load_prices(), load_models()


def _opt(price: int, qty: int = 1) -> dict:
    return {"enabled": True, "price": price, "qty": qty, "customer_side": False}


def _groups(items: list[dict]) -> Counter:
    out: Counter = Counter()
    for it in items:
        out[it["payment_group"]] += it["total"]
    return out


def test_table_edits_reach_contract():
    state = _valid_state()
    orion_price = PRICES["options"]["orion_standard"]["price_retail"]
    state["options"] = {
        "ramp_set_f_s": _opt(380_000),
        "orion_standard": _opt(orion_price),
        "install_default": _opt(180_000),
    }
    state["custom_items"] = [{"id": "custom_1", "name": "Шкаф", "price": 50_000}]
    state["spec_items_overrides"] = {
        state["model_id"]: {"price": 2_000_000},
        "ramp_set_f_s": {"price": 300_000, "qty": 3},
        "orion_install": {"price": 77_000},  # расщеплённый ОРИОН
        "custom_1": {"qty": 2},
    }
    kp_items = build_spec_items(state, PRICES, MODELS)
    kp_total = sum(it["total"] for it in kp_items)
    row = _kp_row(state)

    items = build_specification_items(row, PRICES)
    assert sum(it["total"] for it in items) == kp_total
    assert _groups(items) == _groups(kp_items)
    weights = next(it for it in items if it["id"] == "weights")
    assert weights["price_per_unit"] == 2_000_000
    ramps = next(it for it in items if it["id"] == "pandus")
    assert (ramps["quantity"], ramps["price_per_unit"]) == (3, 300_000)
    assert next(it for it in items if it["id"] == "orion_install")["total"] == 77_000

    assert sum(r["price"] for r in build_spec_rows_from_snapshot(row, PRICES)) == kp_total
    spec = build_specification_from_kp_snapshot(row, PRICES, MODELS, load_payment_terms())
    assert spec["СПЕЦ_ИТОГО"] == _fmt(kp_total)


def test_without_overrides_unchanged():
    state = _valid_state()
    state["options"] = {"ramp_set_f_s": _opt(380_000, 2)}
    items = build_specification_items(_kp_row(state), PRICES)
    assert sum(it["total"] for it in items) == sum(
        it["total"] for it in build_spec_items(state, PRICES, MODELS)
    )

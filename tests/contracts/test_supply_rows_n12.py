"""Д10 (N12): договор поставки — позиции фундамента и поверки не выпадают."""
from __future__ import annotations

from src.contracts.clauses_context import build_clauses_context
from src.contracts.from_kp import build_specification_items
from src.contracts.supply_filler import _supply_spec_rows, decide_contract_type
from src.data_loader import load_models, load_prices
from src.spec_builder import build_spec_items
from tests.test_kp_restore import _kp_row
from tests.test_validation import _valid_state

PRICES = load_prices()


def test_supply_with_concrete_base_and_verification_sum_equals_kp():
    state = _valid_state()
    state["options"] = {
        key: {"enabled": True, "price": price, "qty": 1, "customer_side": False}
        for key, price in (
            ("frame_18", 140_000),
            ("concrete_base_on_frame", 600_000),
            ("verification_default", 60_000),
            ("delivery_default", 70_000),
        )
    }
    items = build_specification_items(_kp_row(state), PRICES)
    ctx = build_clauses_context({"items": items})
    assert decide_contract_type(
        ctx["installation_scope"], ctx["foundation_scope"], ctx["has_orion"]
    ) == "supply"
    total, rows = _supply_spec_rows(items, "Весы")
    assert total == sum(it["total"] for it in build_spec_items(state, PRICES, load_models()))
    names = [r["name"] for r in rows]
    assert names[0] == "Весы" and names[-1] == "Доставка"
    assert "Бетонное основание для весов на раме" in names
    assert any(n.startswith("Поверка") for n in names)

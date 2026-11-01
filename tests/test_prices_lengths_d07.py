"""Д07 (В2-а): закладные и бетонное основание на раме — цена по длине."""
from __future__ import annotations

import pytest

from src.contracts.from_kp import build_specification_items
from src.data_loader import load_prices
from src.filters import get_visible_options
from src.storage.kp_restore import reconstruct_kp_state
from src.storage.snapshot_builder import build_kp_snapshot
from tests.test_kp_restore import _kp_row
from tests.test_validation import _valid_state

PRICES = load_prices()
OPTS = PRICES["options"]

# Изменённые поля прежних записей и новые ключи (для дифф-теста Д03)
D07_FIELDS = {
    ("options", "embedded_parts", "applies_to_lengths"),
    ("options", "embedded_parts", "notes"),
    ("options", "concrete_base_on_frame", "applies_to_lengths"),
    ("options", "concrete_base_on_frame", "price_retail"),
    ("options", "concrete_base_on_frame", "notes"),
}
D07_NEW = {"embedded_parts_12", "embedded_parts_24"} | {
    f"concrete_base_on_frame_{n}" for n in (12, 20, 22, 24)
}

# длина → (ключ закладных, розн., дил.), (ключ основания, розн. или None — по запросу)
BY_LENGTH = {
    12: (("embedded_parts_12", 30_000, 27_600), ("concrete_base_on_frame_12", None)),
    16: (("embedded_parts", 35_000, 32_200), ("concrete_base_on_frame", 600_000)),
    18: (("embedded_parts", 35_000, 32_200), ("concrete_base_on_frame", 600_000)),
    20: (("embedded_parts", 35_000, 32_200), ("concrete_base_on_frame_20", None)),
    22: (("embedded_parts", 35_000, 32_200), ("concrete_base_on_frame_22", None)),
    24: (("embedded_parts_24", 40_000, 36_800), ("concrete_base_on_frame_24", None)),
}


@pytest.mark.parametrize("length", sorted(BY_LENGTH))
def test_one_key_per_length_with_price(length):
    (emb_key, retail, dealer), (base_key, base_retail) = BY_LENGTH[length]
    emb = [k for k, _ in get_visible_options(OPTS, "С", length, "misc") if k.startswith("embedded_parts")]
    base = [k for k, _ in get_visible_options(OPTS, "С", length, "foundation_and_base")
            if k.startswith("concrete_base_on_frame")]
    assert emb == [emb_key] and base == [base_key]
    e = OPTS[emb_key]
    assert (e["price_retail"], e["price_dealer_ru"], e["discount_pct"], e["price_class"]) == (
        retail, dealer, 8, "A_retail_and_dealer")
    b = OPTS[base_key]
    assert b["price_class"] == "B_retail_only"
    assert b["price_retail"] == base_retail and bool(b.get("on_request")) == (base_retail is None)


def _old_kp(length: int, key: str, price: int) -> dict:
    """КП v0.5: прежний ключ на длине, к которой он теперь неприменим."""
    state = _valid_state()
    state.update(model_line="С", model_max=80, model_length=length,
                 model_id=f"vesta-с-80-{length}", model_price=2_000_000)
    state["options"] = {key: {"enabled": True, "price": price, "qty": 1, "customer_side": False}}
    state["spec_items_overrides"] = {key: {"price": price + 1}}
    return _kp_row(state)


@pytest.mark.parametrize("length,key,new_key,price", [
    (24, "embedded_parts", "embedded_parts_24", 35_000),
    (20, "concrete_base_on_frame", "concrete_base_on_frame_20", 550_000),
])
def test_open_old_kp_moves_key_keeps_price(length, key, new_key, price):
    out = reconstruct_kp_state(_old_kp(length, key, price), PRICES)
    suffix = f"__vesta-с-80-{length}"
    assert set(out["options"]) == {new_key}
    assert out["options"][new_key]["price"] == price
    assert out[f"opt_{new_key}_price{suffix}"] == price
    assert out["spec_items_overrides"] == {new_key: {"price": price + 1}}


def test_contract_by_old_and_resaved_kp_rama_concrete():
    row = _old_kp(20, "concrete_base_on_frame", 550_000)
    resaved = dict(row, data=build_kp_snapshot(reconstruct_kp_state(row, PRICES)))
    assert resaved["data"]["foundation_execution"] == "rama_concrete"
    for kp in (row, resaved):
        items = [it for it in build_specification_items(kp, PRICES) if it["id"] == "foundation"]
        assert len(items) == 1
        assert items[0]["metadata"]["scope"] == "rama_concrete"
        assert items[0]["total"] == 550_000
        assert items[0]["name"] == "Бетонное основание для весов на раме"

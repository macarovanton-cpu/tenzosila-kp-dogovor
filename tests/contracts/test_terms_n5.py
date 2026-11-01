"""Д11 (N5): сроки договора — из КП (роли позиций и ручной срок)."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.contracts.from_kp import build_spec_v2_data, build_specification_items, kp_term_days
from src.contracts.kp_load import build_kp_payload
from src.contracts.supply_filler import build_supply_context
from src.data_loader import load_models, load_payment_terms, load_prices
from tests.test_kp_restore import _kp_row
from tests.test_validation import _valid_state

PRICES, MODELS = load_prices(), load_models()
EQUIPMENT = json.loads(Path("data/equipment_specs.json").read_text(encoding="utf-8"))


def _opt(key: str) -> dict:
    return {"enabled": True, "price": PRICES["options"][key]["price_retail"], "qty": 1}


def _state(manual: int | None, keys: tuple[str, ...]) -> dict:
    state = _valid_state()  # С-60-18
    state["options"] = {k: _opt(k) for k in keys}
    state["total_term_days"] = manual
    state["total_term_days_user_set"] = manual is not None
    return state


_SPEC_KEYS = ("foundation_s_f_18", "install_default")


def test_manual_term_scales_roles_like_kp():
    # фикс. монтаж 3, вариативные 30−3=27 → весы 20·27/30=18, фундамент 9
    row = _kp_row(_state(30, _SPEC_KEYS))
    assert kp_term_days(row, PRICES, MODELS) == {"scales": 18, "foundation": 9, "install": 3}
    assert build_kp_payload(row, PRICES, MODELS, load_payment_terms())["term_days"]["scales"] == 18


def test_without_manual_term_defaults():
    # в снапшоте есть total_term_days, но без ручной правки — дефолты по составу
    state = _state(None, _SPEC_KEYS)
    state["total_term_days"] = 35
    row = _kp_row(state)
    assert kp_term_days(row, PRICES, MODELS) == {"scales": 20, "foundation": 10, "install": 3}


def test_spec_terms_lines_from_kp():
    data, _, _ = build_spec_v2_data(
        _kp_row(_state(30, _SPEC_KEYS)), PRICES, MODELS, load_payment_terms(),
        EQUIPMENT,
    )
    text = "\n".join(data["_terms_lines"])
    assert "строительство фундамента Весов: в течение 9 (девяти) рабочих дней" in text
    assert "поставка Весов: в течение 18 (восемнадцати) рабочих дней" in text
    assert "в течение 3 (трёх) рабочих дней" in text


def test_supply_terms_from_kp():
    row = _kp_row(_state(15, ("delivery_default",)))
    items = build_specification_items(row, PRICES)
    deal = {"items": items, "term_days": kp_term_days(row, PRICES, MODELS)}
    res = build_supply_context({}, items, deal, [], {"contract_number": "1"}, date(2026, 1, 1))
    # фикс. доставка 1 → весы 14
    assert res["СРОК_ПРОИЗВОДСТВА_ДН"].startswith("14 (")
    assert res["СРОК_ДОСТАВКИ_ДН"].startswith("1 (")
    # без сроков КП в deal — как раньше, дефолт
    base = build_supply_context({}, items, {"items": items}, [], {"contract_number": "1"}, date(2026, 1, 1))
    assert base["СРОК_ПРОИЗВОДСТВА_ДН"].startswith("20 (")

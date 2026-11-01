"""Д02 (N11): активные группы split-оплаты в форме и в validate = в документе."""
from __future__ import annotations

from streamlit.testing.v1 import AppTest

from src.generators.payment_renderer import get_active_payment_groups
from src.spec_builder import build_spec_items
from src.validation import validate
from tests.test_validation import _valid_state

_OPT = {"enabled": True, "price": 100_000, "qty": 1, "customer_side": False}


def _split_state(**extra) -> dict:
    state = _valid_state()
    state["payment_preset_id"] = "split_by_items"
    state.update(extra)
    return state


def _doc_groups(state: dict, prices: dict, models_json: dict) -> dict:
    return get_active_payment_groups(build_spec_items(state, prices, models_json))["groups"]


def _check(state, group_id, prices, models_json, payment_terms, managers) -> None:
    """Группа активна в документе, и validate проверяет её проценты."""
    assert _doc_groups(state, prices, models_json)[group_id]
    state["payment_split_state"] = {group_id: {"prepay": 40, "postpay": 40}}
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert any("не равна 100" in e for e in errors), errors


def test_orion_poles_without_foundation_activate_foundation(
    prices, models_json, payment_terms, managers
):
    state = _split_state(options={"orion_cable_poles": dict(_OPT)})
    _check(state, "foundation", prices, models_json, payment_terms, managers)


def test_custom_install_item_activates_installation(
    prices, models_json, payment_terms, managers
):
    state = _split_state(custom_items=[{"id": "custom_1", "name": "Монтаж весов", "price": 90_000}])
    _check(state, "installation_and_verification", prices, models_json, payment_terms, managers)


def test_customer_side_verification_as_in_document(
    prices, models_json, payment_terms, managers
):
    # B16: позиция поверки силами Заказчика есть в документе — группа активна и в форме.
    opt = dict(_OPT, customer_side=True)
    state = _split_state(options={"verification_default": opt})
    _check(state, "installation_and_verification", prices, models_json, payment_terms, managers)


def test_inactive_group_not_validated(prices, models_json, payment_terms, managers):
    state = _split_state(payment_split_state={"foundation": {"prepay": 40, "postpay": 40}})
    assert not _doc_groups(state, prices, models_json)["foundation"]
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert errors == []


def _form_app() -> None:
    import json
    from pathlib import Path

    import streamlit as st

    from src.ui.payment_section import _render_split

    terms = json.loads(Path("data/payment_terms.json").read_text(encoding="utf-8"))
    preset = next(p for p in terms["presets"] if p["id"] == "split_by_items")
    items = [
        {"item_key": "vesta-с-60-18", "payment_group": "scales"},
        {"item_key": "orion_cable_poles", "payment_group": "foundation"},
    ]
    st.session_state.setdefault("payment_days", 5)
    _render_split(st.session_state, preset, items)


def test_form_shows_group_of_spec_items():
    at = AppTest.from_function(_form_app).run()
    assert not at.exception
    keys = {w.key for w in at.number_input}
    assert {"split_foundation_prepay", "split_foundation_postpay"} <= keys
    assert "split_installation_and_verification_prepay" not in keys

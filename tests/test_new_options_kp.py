"""Д05: новые опции прайса 28.09 в КП — блок, видимость, оплата, срок, форма."""
from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from src.config import is_weighbridge_foundation_key
from src.data_loader import load_payment_terms, load_prices
from src.filters import get_visible_options
from src.generators.payment_renderer import render_split_by_items
from src.spec_builder import build_spec_items, resolve_payment_group
from src.storage.kp_restore import reconstruct_kp_state
from src.term_days import calculate_term_days_per_item, resolve_term_role
from src.ui.options_section import _disable_other_ramp, _shefmontazh_params
from src.validation import validate
from tests.test_kp_restore import _kp_row
from tests.test_validation import _valid_state

PRICES = load_prices()
OPTS = PRICES["options"]

# ключ → (блок, линейка видна, линейка не видна, группа оплаты, роль срока)
CASES = [
    ("kbu_p06_35_l_18", "foundation_and_base", "СЛ", "С", "scales", None),
    ("kbu_p06_44_18", "foundation_and_base", "С", "СЛ", "scales", None),
    ("kbu_p08_44_18", "foundation_and_base", "Ф", "ФЛ", "scales", None),
    ("ramp_set_f_s_8mm", "ramps", "С", "СЛ", "scales", None),
    ("ramp_set_concrete", "ramps", "ФЛ", None, "scales", None),
    ("foundation_heating_gorynych_5", "misc", "С", None, "scales", None),
    ("ppr_documentation", "install", "П", None, "installation_and_verification", "install"),
    ("canopy_18", "canopy", "С", None, "scales", "canopy"),
    ("foundation_under_canopy_18", "canopy", "С", None, "scales", "canopy"),
    ("canopy_installation_18", "canopy", "С", None, "scales", "canopy"),
    ("canopy_lighting", "canopy", "С", None, "scales", "canopy"),
]


def _visible(block: str, line: str, length: int = 18) -> set[str]:
    return {k for k, _ in get_visible_options(OPTS, line, length, block)}


@pytest.mark.parametrize("key,block,line_on,line_off,group,role", CASES)
def test_option_block_visibility_group_role(key, block, line_on, line_off, group, role):
    assert key in _visible(block, line_on)
    if line_off:
        assert key not in _visible(block, line_off)
    assert key not in _visible(block, line_on, 12 if key.endswith("_18") else 99)
    assert resolve_payment_group(key) == group
    assert resolve_term_role(key) == role


def test_shefmontazh_record_not_an_option_row():
    blocks = ("install", "misc", "foundation_and_base", "canopy", "ramps")
    assert all("shefmontazh" not in _visible(b, "С") for b in blocks)


def test_not_weighbridge_foundation():
    assert is_weighbridge_foundation_key("foundation_s_f_18")
    assert not is_weighbridge_foundation_key("foundation_heating_gorynych_5")
    assert not is_weighbridge_foundation_key("foundation_under_canopy_18")


def _state(line: str = "С", options: dict | None = None, **extra) -> dict:
    state = _valid_state()
    state.update(model_line=line, model_id=f"vesta-{line.lower()}-60-18", options=options or {})
    state.update(extra)
    return state


def _opt(price: int, qty: int = 1) -> dict:
    return {"enabled": True, "price": price, "qty": qty, "customer_side": False}


def test_kp_rows_and_terms(prices, models_json):
    state = _state(options={
        "ramp_set_f_s_8mm": _opt(430_000),
        "canopy_18": _opt(2_800_000),
        "canopy_installation_18": _opt(1_600_000),
        "install_default": _opt(180_000),
        "ppr_documentation": _opt(50_000),
    })
    items = build_spec_items(state, prices, models_json)
    by_key = {it["item_key"]: it for it in items}
    assert by_key["ramp_set_f_s_8mm"]["name"] == "Комплект пандусов под весы ВЕСТА-С (L=3,9м), 8мм"
    assert by_key["ppr_documentation"]["name"] == "Разработка ППР и исполнительной документации"
    days, total = calculate_term_days_per_item(items)
    # один срок «навес» на все части, ППР — срок монтажа
    assert days["canopy_18"] == days["canopy_installation_18"] == 25
    assert days["ppr_documentation"] == days["install_default"]
    assert total == calculate_term_days_per_item(
        [it for it in items if it["item_key"] not in ("ppr_documentation", "canopy_installation_18")]
    )[1]


def test_ppr_with_install_payment_line(prices, models_json):
    state = _state(
        options={"install_default": _opt(180_000), "ppr_documentation": _opt(50_000)},
        payment_preset_id="split_by_items",
    )
    preset = next(p for p in load_payment_terms()["presets"] if p["id"] == "split_by_items")
    text = render_split_by_items(state, build_spec_items(state, prices, models_json), preset)
    iv_line = next(line for line in text.splitlines() if "Акту" in line or "бригад" in line)
    assert iv_line.startswith("— Монтаж") and "поверк" not in iv_line.lower()


def test_ramp_6_and_8mm_exclusive():
    ss = {"opt_ramp_set_f_s_enabled__m": True, "opt_ramp_set_f_s_8mm_enabled__m": True,
          "options": {"ramp_set_f_s": _opt(380_000)}, "spec_items_overrides": {"ramp_set_f_s": {"qty": 2}}}
    _disable_other_ramp(ss, "ramp_set_f_s_8mm", "__m")
    assert ss["opt_ramp_set_f_s_enabled__m"] is False
    assert "ramp_set_f_s" not in ss["options"] and not ss["spec_items_overrides"]


def test_shefmontazh_price_default_and_line_p():
    assert _shefmontazh_params(OPTS, {"model_line": "С", "model_length": 18}).default_v == 140_000
    assert _shefmontazh_params(OPTS, {"model_line": "П", "model_length": 18}) is None  # В5


def test_on_request_needs_manual_price(prices, models_json, payment_terms, managers):
    state = _state(options={"canopy_lighting": dict(_opt(0), is_on_request=True)})
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert "Опция «Освещение под навесом» — цена по запросу: укажите цену вручную." in errors
    state["options"]["canopy_lighting"]["price"] = 120_000
    errors, _ = validate(state, prices, models_json, payment_terms, managers)
    assert not any("по запросу" in e for e in errors)


@pytest.mark.parametrize("line,key,price", [
    ("СЛ", "kbu_p06_35_l_18", 300_000), ("С", "kbu_p06_44_18", 400_000),
    ("С", "ramp_set_f_s_8mm", 430_000), ("С", "ramp_set_concrete", 275_000),
    ("С", "foundation_heating_gorynych_5", 90_000), ("С", "ppr_documentation", 50_000),
    ("С", "canopy_18", 2_800_000), ("С", "foundation_under_canopy_18", 1_100_000),
    ("С", "canopy_installation_18", 1_600_000), ("С", "canopy_lighting", 70_000),
])
def test_save_and_open_keeps_key_and_price(line, key, price):
    state = _state(line, options={key: _opt(price, 3 if key.startswith("kbu_") else 1)})
    state.update(kp_date=None, kp_number="КП-1")
    out = reconstruct_kp_state(_kp_row(state), PRICES)
    assert out["options"][key]["price"] == price
    assert out[f"opt_{key}_price__{state['model_id']}"] == price


# --- форма (AppTest) ---

_MODEL = "vesta-с-60-18"


def _form_app() -> None:
    import streamlit as st

    from src.data_loader import load_models, load_options_meta, load_prices
    from src.ui.options_section import render_options_section

    for k, v in {"model_line": "С", "model_max": 60, "model_length": 18,
                 "model_id": "vesta-с-60-18", "options": {}}.items():
        st.session_state.setdefault(k, v)
    render_options_section(st.session_state, load_prices(), load_models(), load_options_meta())


def _cb(at: AppTest, key: str):
    return at.checkbox(key=f"opt_{key}_enabled__{_MODEL}")


def test_form_shef_price_ppr_gate_and_on_request():
    at = AppTest.from_function(_form_app).run()
    assert not at.exception
    assert _cb(at, "ppr_documentation").disabled

    _cb(at, "install_default").check().run()
    price = at.number_input(key=f"opt_install_default_price__{_MODEL}")
    assert price.value == 180_000
    at.checkbox(key=f"opt_install_default_shefmontazh__{_MODEL}").check().run()
    assert at.number_input(key=f"opt_install_default_price__{_MODEL}").value == 140_000
    at.checkbox(key=f"opt_install_default_shefmontazh__{_MODEL}").uncheck().run()
    assert at.number_input(key=f"opt_install_default_price__{_MODEL}").value == 180_000

    assert not _cb(at, "ppr_documentation").disabled
    _cb(at, "ppr_documentation").check().run()
    assert at.session_state["options"]["ppr_documentation"]["enabled"]
    _cb(at, "install_default").uncheck().run()
    assert _cb(at, "ppr_documentation").disabled and not _cb(at, "ppr_documentation").value
    assert not at.session_state["options"]["ppr_documentation"]["enabled"]

    lighting = _cb(at, "canopy_lighting")
    assert not lighting.disabled
    lighting.check().run()
    assert at.number_input(key=f"opt_canopy_lighting_price__{_MODEL}").value is None
    assert at.session_state["options"]["canopy_lighting"]["price"] == 0
    assert not at.exception and not at.warning

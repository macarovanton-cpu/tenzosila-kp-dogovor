"""Д01: предупреждения свободной цены и сохранность цены вне коридора."""
from __future__ import annotations

from streamlit.testing.v1 import AppTest

from src.price_warnings import price_warnings
from src.pricing import get_model_slider_params, get_slider_params

# A: min 80 000 (дилерская), max 140 000
_A = get_slider_params(
    {"price_class": "A_retail_and_dealer", "price_retail": 100_000, "price_dealer_ru": 80_000}
)
# B: min 60 000, max 270 000, дилерской нет
_B = get_slider_params({"price_class": "B_retail_only", "price_retail": 100_000})
# C: min 10 000, max 50 000, дилерской нет
_C = get_slider_params(
    {"price_class": "C_manual_range", "price_retail": 20_000,
     "range_min": 10_000, "range_max": 50_000}
)
# Модель: min 1 754 000, max 2.0 × retail
_M = get_model_slider_params({"retail": 1_906_544, "dealer_ru": 1_754_021})


def test_inside_corridor_no_warnings():
    for params in (_A, _B, _C, _M):
        assert price_warnings("X", params.default_v, params) == []


def test_class_a_below_dealer_gives_both_warnings():
    msgs = price_warnings("Опция", 70_000, _A)
    assert msgs == [
        "Цена «Опция» 70 000 ₽ ниже дилерской 80 000 ₽.",
        "Цена «Опция» 70 000 ₽ вне коридора 80 000–140 000 ₽.",
    ]


def test_class_a_above_corridor_only_corridor_warning():
    assert price_warnings("Опция", 150_000, _A) == [
        "Цена «Опция» 150 000 ₽ вне коридора 80 000–140 000 ₽."
    ]


def test_class_b_has_no_dealer_check():
    assert price_warnings("Работы", 50_000, _B) == [
        "Цена «Работы» 50 000 ₽ вне коридора 60 000–270 000 ₽."
    ]
    assert price_warnings("Работы", 300_000, _B) == [
        "Цена «Работы» 300 000 ₽ вне коридора 60 000–270 000 ₽."
    ]


def test_class_c_below_and_above():
    assert len(price_warnings("Поверка", 5_000, _C)) == 1
    assert len(price_warnings("Поверка", 60_000, _C)) == 1
    assert price_warnings("Поверка", 30_000, _C) == []


def test_model_below_dealer_and_above_corridor():
    assert len(price_warnings("m", 1_000_000, _M)) == 2
    assert len(price_warnings("m", _M.max_v + 1, _M)) == 1


def test_dealer_non_round_between_min_and_dealer():
    # min_v = ceil(dealer) до тысяч > dealer: цена между ними — вне коридора, но не ниже дилерской
    msgs = price_warnings("m", 1_754_021, _M)
    assert len(msgs) == 1 and "вне коридора" in msgs[0]


# --- сохранённая цена вне коридора остаётся в поле (AppTest) ---


def _model_app() -> None:
    import streamlit as st
    from src.ui import model_section
    state = {
        "model_id": "vesta-с-60-18", "model_line": "С", "model_max": 60,
        "model_length": 18, "platform_width_m": 3.0, "model_price": 1_000_000,
    }
    model_section._render_model_price_slider(
        state, {"retail": 1_906_544, "dealer_ru": 1_754_021}
    )
    st.session_state["out"] = state["model_price"]


def _option_app() -> None:
    import streamlit as st
    from src.pricing import get_slider_params
    from src.ui.options_section import _render_price_widget
    params = get_slider_params(
        {"price_class": "A_retail_and_dealer", "price_retail": 100_000, "price_dealer_ru": 80_000}
    )
    st.session_state["out"] = _render_price_widget("x", params, "__m", "Опция")


def test_model_price_below_corridor_is_kept_and_warned():
    at = AppTest.from_function(_model_app).run()
    assert not at.exception
    assert at.session_state["out"] == 1_000_000
    assert len(at.warning) == 2
    assert all("«ВЕСТА-С-60-18»" in w.value for w in at.warning)


def test_option_price_above_corridor_is_kept_and_warned():
    at = AppTest.from_function(_option_app).run()
    assert not at.warning
    at.number_input[0].set_value(500_000).run()  # цена выше коридора A (140 000)
    assert not at.exception
    assert at.session_state["out"] == 500_000
    assert len(at.warning) == 1

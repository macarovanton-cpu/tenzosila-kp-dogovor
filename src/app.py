"""Streamlit entry point конфигуратора КП ВЕСТА."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Чтобы запускалось и `streamlit run src/app.py`, и из корня проекта
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.data_loader import (  # noqa: E402
    load_managers,
    load_models,
    load_options_meta,
    load_payment_terms,
    load_prices,
)
from src.pricing import calc_totals  # noqa: E402
from src.spec_builder import build_spec_items, resolve_term_days  # noqa: E402
from src.state import init_state  # noqa: E402
from src.ui.construction_section import render_construction_section  # noqa: E402
from src.ui.equipment_section import render_equipment_section  # noqa: E402
from src.ui.header import render_header  # noqa: E402
from src.ui.model_section import render_model_section  # noqa: E402
from src.ui.options_section import render_options_section  # noqa: E402
from src.ui.payment_section import render_payment_section  # noqa: E402
from src.ui.sidebar import render_sidebar  # noqa: E402
from src.validation import validate  # noqa: E402


def main() -> None:
    st.set_page_config(
        page_title="Конфигуратор КП ВЕСТА",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("Конфигуратор коммерческого предложения")
    st.caption(
        "ТПК «Тензосила» · автомобильные весы ВЕСТА · "
        "Фаза 1.1+1.2 (без DOCX-генерации)"
    )

    init_state()

    models_json = load_models()
    prices = load_prices()
    payment_terms = load_payment_terms()
    options_meta = load_options_meta()
    managers = load_managers()

    render_header(st.session_state, managers)

    col1, col2 = st.columns(2, gap="large")
    with col1:
        render_model_section(st.session_state, models_json, prices)
        render_equipment_section(st.session_state, models_json)
        render_construction_section(st.session_state, models_json)
    with col2:
        render_options_section(
            st.session_state, prices, models_json, options_meta
        )

    spec_items = build_spec_items(st.session_state, prices, models_json)
    payment_preview = render_payment_section(
        st.session_state, payment_terms, spec_items
    )

    errors, warnings = validate(
        st.session_state, prices, models_json, payment_terms, managers
    )
    totals = calc_totals(spec_items)
    term_days = resolve_term_days(spec_items, st.session_state)

    render_sidebar(
        st.session_state,
        spec_items,
        errors,
        warnings,
        totals,
        payment_preview,
        term_days,
    )


if __name__ == "__main__":
    main()

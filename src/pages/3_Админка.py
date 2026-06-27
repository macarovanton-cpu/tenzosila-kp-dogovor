"""Read-only страница админки прайса."""
from __future__ import annotations

import streamlit as st

from src.admin.price_overview_view import render_price_overview
from src.admin.price_update_view import render_update_view
from src.admin.price_upload_view import render_price_upload
from src.data_loader import load_prices


st.title("Админка")
st.info(
    "На этой странице можно посмотреть диагностику прайса и обновить его из PDF "
    "с записью в data/prices.json. Разграничение прав доступа пока не реализовано — "
    "страница видна всем пользователям приложения."
)

try:
    prices = load_prices()
except Exception as exc:  # pragma: no cover - защита UI от битого локального файла.
    st.error(f"Не удалось прочитать или проверить текущий прайс: {exc}")
    st.stop()

render_price_overview(prices)
render_price_upload(prices)
st.divider()
render_update_view()

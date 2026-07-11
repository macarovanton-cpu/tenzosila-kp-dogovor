"""Read-only страница админки прайса."""
from __future__ import annotations

import streamlit as st

from src.admin.price_overview_view import render_price_overview
from src.admin.price_update_view import render_update_view
from src.admin.price_upload_view import render_price_upload
from src.admin.price_write_service import rollback_prices
from src.config import PRICES_JSON
from src.data_loader import load_prices

_BACKUP_PATH = PRICES_JSON.with_name("prices.backup.json")

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
    # P2: Откат доступен даже при битом prices.json — именно этот сценарий требует восстановления.
    if _BACKUP_PATH.exists():
        if st.button("Откатить на предыдущую версию (восстановить из бэкапа)"):
            if rollback_prices():
                st.success("Прайс восстановлен из предыдущей версии")
                st.rerun()
            else:
                st.error("Откат не удался.")
    st.stop()

render_price_overview(prices)

# Кнопка отката на главном экране
backup_exists = _BACKUP_PATH.exists()

if st.button("Откатить на предыдущую версию", disabled=not backup_exists):
    st.session_state["_rollback_confirm"] = True

if st.session_state.get("_rollback_confirm"):
    st.warning("Вернуть прайс из предыдущей версии?")
    c1, c2 = st.columns([1, 5])
    if c1.button("Да, откатить", type="primary"):
        ok = rollback_prices()
        st.session_state.pop("_rollback_confirm", None)
        if ok:
            # P2: сбросить черновик update-потока, чтобы старые данные не перезаписали откат.
            for _key in (
                "price_update_stage", "price_update_source",
                "price_update_working_items", "price_update_checked",
                "price_update_backup_path",
            ):
                st.session_state.pop(_key, None)
            st.success("Прайс восстановлен из предыдущей версии")
            st.rerun()
        else:
            st.error("Бэкап не найден — откат невозможен.")
    if c2.button("Отмена"):
        st.session_state.pop("_rollback_confirm", None)
        st.rerun()

render_price_upload(prices)
st.divider()
render_update_view()

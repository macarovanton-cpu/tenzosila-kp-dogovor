"""Entry point конфигуратора КП ВЕСТА — роутер навигации."""
from pathlib import Path

import streamlit as st

_pages = Path(__file__).parent / "pages"

pg = st.navigation(
    [
        st.Page(str(_pages / "1_Коммерческое_предложение.py"), title="Коммерческое предложение"),
        st.Page(str(_pages / "2_Договор.py"), title="Договор"),
        st.Page(str(_pages / "3_Админка.py"), title="Админка"),
    ]
)
pg.run()

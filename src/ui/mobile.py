"""Адаптивные CSS-стили для мобильных устройств."""
from __future__ import annotations

import streamlit as st

_MOBILE_CSS: str = """<style>
@media (max-width: 768px) {
    /* Убрать боковые padding контейнера */
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* Sidebar свёрнут по умолчанию */
    section[data-testid="stSidebar"] {
        width: 0px !important;
        min-width: 0px !important;
    }
    section[data-testid="stSidebar"][aria-expanded="true"] {
        width: 85vw !important;
        min-width: 85vw !important;
    }

    /* Колонки стопкой */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        width: 100% !important;
        flex: 1 0 100% !important;
    }

    /* Таблица спецификации — горизонтальный скролл */
    [data-testid="stDataEditor"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }
    [data-testid="stDataEditor"] table {
        min-width: 600px;
    }

    /* Touch-target минимум 44px (Apple HIG) */
    button,
    [data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-secondary"] {
        min-height: 44px !important;
    }

    /* Шрифт 16px в инпутах — предотвращает iOS auto-zoom при фокусе */
    [data-testid="stSelectbox"] input,
    [data-testid="stSelectbox"] div[data-baseweb="select"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        font-size: 16px !important;
    }

    /* Меньше вертикальных отступов между секциями */
    [data-testid="stVerticalBlock"] > div {
        gap: 0.5rem !important;
    }
}
</style>"""


def inject_mobile_css() -> None:
    """Внедрить CSS-правила для мобильной адаптации (viewport <= 768px)."""
    st.markdown(_MOBILE_CSS, unsafe_allow_html=True)

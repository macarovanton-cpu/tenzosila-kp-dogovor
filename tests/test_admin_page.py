"""Smoke-тесты read-only страницы админки."""
from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = str(Path(__file__).resolve().parent.parent / "src" / "app.py")


def _fresh_app() -> AppTest:
    return AppTest.from_file(APP_PATH, default_timeout=30).run()


def _element_values(elements: list) -> list[str]:
    return [str(element.value) for element in elements]


def test_admin_page_shows_price_diagnostics() -> None:
    at = _fresh_app()

    at.switch_page("pages/3_Админка.py").run()

    assert not at.exception, f"Admin page raised: {at.exception}"
    page_text = [
        *_element_values(at.title),
        *_element_values(at.header),
        *_element_values(at.subheader),
        *_element_values(at.markdown),
        *_element_values(at.info),
        *_element_values(at.warning),
        *_element_values(at.error),
        *_element_values(at.success),
    ]
    joined_text = "\n".join(page_text)
    assert "Админка" in joined_text
    assert "Диагностика текущего прайса" in joined_text
    assert "read-only" in joined_text
    metrics = {metric.label: metric.value for metric in at.metric}
    assert metrics["Модели"] == "45"
    assert metrics["Опции"] == "65"
    assert metrics["Errors"] == "0"
    assert metrics["Warnings"] == "5"

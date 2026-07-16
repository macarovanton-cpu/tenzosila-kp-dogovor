"""Smoke-тесты страницы админки."""
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

    at.switch_page("app_pages/3_Админка.py").run()

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
        *_element_values(at.caption),
    ]
    joined_text = "\n".join(page_text)
    assert "Админка" in joined_text
    assert "Состояние прайса" in joined_text
    assert "Проверка загруженного прайса" in joined_text
    assert "read-only" in joined_text

    # Технические детали свёрнуты в expander
    expander_labels = [exp.label for exp in at.expander]
    assert any("Технические детали" in lbl for lbl in expander_labels), (
        f"Expander 'Технические детали' не найден. Expanders: {expander_labels}"
    )

    # Кнопка отката присутствует
    button_labels = [btn.label for btn in at.button]
    assert any("Откатить" in lbl for lbl in button_labels), (
        f"Кнопка отката не найдена. Кнопки на странице: {button_labels}"
    )

    # Метрики бизнес-карточки
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("Модели") == "53"
    assert "Предупреждений" in metrics

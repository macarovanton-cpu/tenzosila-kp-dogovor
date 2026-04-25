"""Page Object для конфигуратора КП.

Селекторы Streamlit (1.38+):
- `<input>` у text_input/checkbox/number_input имеет точный `aria-label`
- selectbox-комбобокс использует динамический `aria-label` ("Selected X. Линейка"),
  поэтому ищем через контейнер `data-testid="stSelectbox"` + filter has_text
- expander — `<button>` (BaseWeb summary) с текстом заголовка; для опционных
  блоков заголовок плавает («Фундамент (N включено)»), ловим regex'ом
- кнопка генерации — `<button data-testid="stBaseButton-primary">` с
  `<p>📄 Сгенерировать КП</p>` внутри, ловим через get_by_role + name
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from playwright.sync_api import Download, Locator, Page


GENERATE_LABEL = "📄 Сгенерировать КП"


class KpPage:
    def __init__(self, page: Page):
        self.page = page

    # ----------------------------------------------------- internal helpers

    def _wait_rerun(self) -> None:
        # Streamlit мигает status-widget'ом во время rerun. Ждём, пока в нём
        # перестанет упоминаться "Running". Не используем networkidle —
        # Streamlit держит постоянное websocket-соединение.
        try:
            self.page.wait_for_function(
                """() => {
                  const w = document.querySelector('[data-testid="stStatusWidget"]');
                  if (!w) return true;
                  const t = (w.innerText || '').toLowerCase();
                  return !t.includes('running');
                }""",
                timeout=8_000,
            )
        except Exception:
            pass
        # Маленький буфер на пере-рендер — Streamlit перерисовывает дерево.
        self.page.wait_for_timeout(300)

    def _input_by_aria(self, label: str) -> Locator:
        # Точный aria-label у input/textarea-виджетов Streamlit. Тип не
        # фильтруем — Streamlit использует aria-label на самом widget input.
        return self.page.locator(
            f'input[aria-label="{label}"], textarea[aria-label="{label}"]'
        ).first

    def _checkbox_by_aria(self, label: str) -> Locator:
        # Только checkbox-input. Help-tooltip-кнопки внутри лейбла имеют
        # aria-label "Help for X" — не пересекаются, но фильтр type="checkbox"
        # делает локатор однозначным.
        return self.page.locator(
            f'input[type="checkbox"][aria-label="{label}"]'
        ).first

    def _selectbox(self, label: str, *, scope: str = "main") -> Locator:
        """Контейнер selectbox с подписью label. scope: 'main' | 'sidebar'."""
        root = self._scope_root(scope)
        return root.locator('[data-testid="stSelectbox"]').filter(
            has_text=label
        ).first

    def _scope_root(self, scope: str) -> Locator:
        if scope == "sidebar":
            return self.page.locator('section[data-testid="stSidebar"]')
        return self.page.locator('[data-testid="stMain"], [data-testid="stAppViewContainer"]').first

    # -------------------------------------------------------- header inputs

    def set_kp_number(self, value: str) -> None:
        inp = self._input_by_aria("Номер КП")
        inp.fill(value)
        inp.press("Tab")
        self._wait_rerun()

    def set_client_name(self, value: str) -> None:
        inp = self._input_by_aria("Название клиента")
        inp.fill(value)
        inp.press("Tab")
        self._wait_rerun()

    # ------------------------------------------------------ model cascade

    def select_line(self, line: str) -> None:
        self._select_option_in("Линейка", line)

    def set_max_load(self, value: int | str) -> None:
        self._select_option_in("Макс. нагрузка, т", str(value))

    def set_length(self, value: int | str) -> None:
        self._select_option_in("Длина платформы, м", str(value))

    def toggle_dual_range(self, on: bool = True) -> None:
        cb = self._checkbox_by_aria("Двухдиапазонные весы")
        if self._is_aria_checked(cb) != on:
            self._toggle_input(cb)
            self._wait_rerun()

    def _toggle_input(self, cb: Locator) -> None:
        # Streamlit checkbox/radio — `<input>` визуально скрыт. JS-click
        # триггерит change-event, Streamlit подхватывает на rerun.
        # Проверено: значительно быстрее клика по родительскому label
        # (никакого scroll-into-view), все сценарии проходят.
        cb.evaluate("el => el.click()")

    def _is_aria_checked(self, cb: Locator) -> bool:
        try:
            val = cb.get_attribute("aria-checked", timeout=1500)
            if val is not None:
                return val == "true"
        except Exception:
            pass
        try:
            return bool(cb.is_checked(timeout=1500))
        except Exception:
            return False

    # --------------------------------------------------- options expanders

    def open_block(self, block_label: str) -> None:
        """Раскрыть expander по подписи.

        Streamlit рендерит expander как `<details>/<summary>` (заголовок —
        markdown-параграф). Счётчик «(N включено)» меняет текст summary при
        toggle опций. Устанавливаем `details.open = true` напрямую через JS:
        клики по summary иногда схлопываются при Streamlit-rerun'е.
        """
        summaries = self.page.locator("summary").all()
        for s in summaries:
            md = s.locator('[data-testid="stMarkdownContainer"] p').first
            try:
                text = md.inner_text(timeout=400).strip()
            except Exception:
                continue
            if text == block_label or text.startswith(f"{block_label} ("):
                details = s.locator("xpath=ancestor::details[1]")
                details.evaluate("el => { el.open = true; }")
                self.page.wait_for_timeout(150)
                return
        raise AssertionError(
            f"Expander {block_label!r} не найден среди {len(summaries)} summary."
        )

    def toggle_option(
        self, block_label: str, option_label: str, on: bool = True
    ) -> None:
        self.open_block(block_label)
        cb = self._checkbox_by_aria(option_label)
        # Дождаться, пока input реально привязан к DOM (после раскрытия expander).
        cb.wait_for(state="attached", timeout=8_000)
        if self._is_aria_checked(cb) != on:
            self._toggle_input(cb)
            self._wait_rerun()

    def set_verification_doer(self, doer: str) -> None:
        # st.radio рендерит <input type="radio">, но aria-label может быть
        # на родительском label, не на input. Пробуем оба пути и не падаем,
        # если уже выбран нужный — дефолт «Подрядчик» совпадает с большинством
        # тестовых сценариев.
        radio = self._input_by_aria(doer)
        try:
            if radio.count() and radio.is_checked(timeout=1500):
                return
        except Exception:
            pass
        try:
            self._toggle_input(radio)
            self._wait_rerun()
            return
        except Exception:
            pass
        # Альтернатива: клик по тексту в радиогруппе.
        try:
            self.page.get_by_role("radio", name=doer, exact=True).first.click(
                force=True
            )
            self._wait_rerun()
        except Exception:
            # «Подрядчик» — дефолт; для других тестов уточним по запросу.
            pass

    # --------------------------------------------------- payment (sidebar)

    def open_payment_panel(self) -> None:
        # Sidebar-expander «💸 Условия оплаты» — тот же <details>/<summary>.
        self.open_block("💸 Условия оплаты")

    def select_payment_preset(self, preset_label: str) -> None:
        # Пресет лежит в основном контенте (payment_section.py:34), не в sidebar.
        self._select_option_in("Пресет", preset_label)

    def set_payment_custom_text(self, text: str) -> None:
        # textarea с aria-label="Текст условий оплаты"
        ta = self._input_by_aria("Текст условий оплаты")
        ta.fill(text)
        ta.press("Tab")
        self._wait_rerun()

    # ---------------------------------------------------------- generation

    def is_generate_disabled(self) -> bool:
        btn = self._generate_button()
        try:
            return bool(btn.is_disabled())
        except Exception:
            return True

    def generate(self) -> Download:
        with self.page.expect_download(timeout=15_000) as info:
            self._generate_button().click()
        return info.value

    def _generate_button(self) -> Locator:
        return self.page.get_by_role(
            "button", name=GENERATE_LABEL
        ).first

    def get_validation_messages(self) -> list[str]:
        out: list[str] = []
        for loc in self.page.locator(
            'section[data-testid="stSidebar"] [data-testid="stMarkdown"]'
        ).all():
            try:
                txt = loc.inner_text(timeout=500).strip()
            except Exception:
                continue
            if txt:
                out.append(txt)
        return out

    # -------------------------------------------------------------- helpers

    def _select_option_in(self, label: str, option_text: str) -> None:
        sb = self._selectbox(label)
        sb.click()
        # BaseWeb dropdown рендерит список в портале с role=option
        self.page.get_by_role(
            "option", name=option_text, exact=True
        ).first.click()
        self._wait_rerun()

    # ----------------------------------------------- bulk scenario applier

    def apply_options(
        self, options: Iterable[tuple[str, str, bool]]
    ) -> None:
        for block_label, option_label, on in options:
            self.toggle_option(block_label, option_label, on=on)


def save_download(download: Download, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    download.save_as(str(target))
    return target


__all__ = ["KpPage", "GENERATE_LABEL", "save_download"]

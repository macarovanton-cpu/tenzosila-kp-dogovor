"""Ловушки группы C из FIX_SPEC_generation_2026-07-08.md — кавычки имени заказчика.

C1+C3 — один баг (нет нормализации прямых кавычек), не два отдельных пункта:
менеджер всегда вводит имя заказчика прямыми кавычками (Shift+2), не ёлочками.
Простой случай (`rama_ploshadka_montazh`, `ООО "Ромашка-Юг"`) и вложенный
случай с тремя прямыми кавычками (`montazh_orion`,
`ООО "Агрофирма "Промышленная"`) — оба должны превращаться в ёлочки без потерь.

C4 — сторож двух форм имени подрядчика по контексту: «ТПК «Тензосила»»
(преамбула/реквизиты) и «Компания «Тензосила»» (блок Госреестра/сертификации).
Обе формы сейчас корректно присутствуют в сгенерированном документе — тест
зелёный регрессионный сторож, а не документированная ловушка. Строка
Госреестра запечена статикой в data/спецификация-шаблоне (ООО «ТПК
«Тензосила») — см. src/contracts/supplier.py docstring.
"""
from __future__ import annotations

import re

from tests.autoverify.docx_text import extract_text

# "kp" исключён: КП-шаблон легитимно использует `"` как символ дюйма в
# описании дисплеев (напр. YHL-3"), не относится к кавычкам имени заказчика.
_DOC_KINDS_WITH_CUSTOMER_NAME = ("contract", "spec", "supply")

# Легитимный статичный шаблонный паттерн подписи — дата прописью в кавычках
# вокруг пустых подчёркиваний, напр. «"____" ___________2026 г.» — не имеет
# отношения к кавычкам имени заказчика, исключается перед проверкой.
_SIGNATURE_DATE_QUOTES_RE = re.compile(r'"_+"')


def test_c1_c3_straight_quotes_simple(generated) -> None:
    """Простой ввод прямыми кавычками → ёлочки в документе."""
    if generated.fixture_id != "rama_ploshadka_montazh":
        return
    for kind in ("contract", "spec"):
        text = extract_text(generated.docx_paths[kind])
        assert "«Ромашка-Юг»" in text, f"{generated.fixture_id}/{kind}: нет «Ромашка-Юг»"
        clean = _SIGNATURE_DATE_QUOTES_RE.sub("", text)
        assert '"' not in clean, f"{generated.fixture_id}/{kind}: остались прямые кавычки"


def test_c1_c3_straight_quotes_nested(generated) -> None:
    """Вложенное имя, введённое тремя прямыми кавычками → вложенные ёлочки без потерь."""
    if generated.fixture_id != "montazh_orion":
        return
    for kind in ("contract", "spec"):
        text = extract_text(generated.docx_paths[kind])
        assert "«Агрофирма «Промышленная»»" in text, (
            f"{generated.fixture_id}/{kind}: вложенные ёлочки не собраны корректно"
        )
        clean = _SIGNATURE_DATE_QUOTES_RE.sub("", text)
        assert '"' not in clean, f"{generated.fixture_id}/{kind}: остались прямые кавычки"


def test_no_straight_quotes_regression(generated) -> None:
    """Ни в одном документе не должно быть прямых кавычек `"` (кроме даты подписи)."""
    for kind, path in generated.docx_paths.items():
        if kind not in _DOC_KINDS_WITH_CUSTOMER_NAME:
            continue
        text = _SIGNATURE_DATE_QUOTES_RE.sub("", extract_text(path))
        assert '"' not in text, f"{generated.fixture_id}/{kind}: найдены прямые кавычки"


def test_c4_contractor_name_forms_sentinel(generated) -> None:
    """Госреестр/сертификация должны использовать форму «Компания «Тензосила»»."""
    if generated.flow != "spec":
        return
    text = extract_text(generated.docx_paths["spec"])
    if "78871-20" not in text:
        return
    assert "«ТПК «Тензосила»" in text, (
        f"{generated.fixture_id}: форма «ТПК «Тензосила»» отсутствует (преамбула/реквизиты)"
    )
    assert "«Компания «Тензосила»" in text, (
        f"{generated.fixture_id}: форма «Компания «Тензосила»» отсутствует в блоке "
        f"Госреестра — сейчас там тоже «ТПК» (см. модуль docstring)"
    )

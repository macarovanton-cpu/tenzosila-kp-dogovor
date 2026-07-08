"""БАГ-1b регресс (не входит в 12 пунктов ловушек FIX_SPEC).

Рама без монтажа должна давать договор поставки, а не спецификацию. Согласно
DIAG_P0_2026-07-08.md это не баг генератора: при installation_scope="none"
foundation_scope дефолтится в "none" (не "customer_builds"), а
decide_contract_type("none", "none", False) уже сегодня возвращает "supply".
Баг находится в UX-подсказке радиокнопки в src/pages/2_Договор.py, которую
headless-раннер не затрагивает. Тест ниже ожидаемо ЗЕЛЁНЫЙ — это регресс-
проверка того, что сам генератор ведёт себя корректно.
"""
from __future__ import annotations


def test_rama_without_installation_is_supply(generated) -> None:
    """Рама без монтажа -> supply-флоу, генерация проходит без ошибок."""
    if generated.fixture_id != "rama_bez_montazha":
        return
    assert generated.flow == "supply", (
        f"{generated.fixture_id}: flow={generated.flow!r}, ожидался 'supply'"
    )
    assert "supply" in generated.docx_paths, (
        f"{generated.fixture_id}: нет документа поставки в docx_paths"
    )

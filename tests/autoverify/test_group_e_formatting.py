"""Ловушки группы E из FIX_SPEC_generation_2026-07-08.md — оформление/порядок.

E1: двойная точка в адресе объекта (клауза delivery_address ставит точку
после переменной — если адрес уже с точкой на входе, получается «..»).
E2: пункт «3. Срок поставки...» должен быть пронумерован (сейчас у «Порядок
оплаты» и «Срок поставки...» верхнеуровневые номера 2./3. отсутствуют вовсе —
подтверждено эмпирически на всех spec-фикстурах).
E3a: порядок позиций Весы→Рама→Пандусы→Доставка→Монтаж→Поверка.
E3b: наименования позиций == эталонным (таблица FIX_SPEC §E3b).
"""
from __future__ import annotations

from tests.autoverify.docx_text import extract_text, find_spec_table

# Эталонные наименования из FIX_SPEC §E3b (там, где текущий код расходится
# с эталоном на фикстуре rama_ploshadka_montazh/montazh_orion).
_EXPECTED_NAMES = {
    "installation": "Монтаж автомобильных весов",
    "verification": "Поверка автомобильных весов с доставкой эталонов",
    "delivery": "Доставка весов до объекта",
}


def _category(name: str) -> int | None:
    """Категория позиции для проверки порядка (E3a)."""
    if name.startswith("Весы"):
        return 0
    if name.startswith("Рама"):
        return 1
    if "пандус" in name.lower():
        return 2
    if name.startswith("Доставка"):
        return 3
    if name.startswith("Монтаж") and "ОРИОН" not in name:
        return 4
    if name.startswith("Поверка"):
        return 5
    return None


def test_e1_address_single_trailing_dot(generated) -> None:
    """Клауза адреса поставки не должна содержать двойную точку."""
    clause = next(
        (c for c in generated.clauses.get("final", []) if c.id == "delivery_address"),
        None,
    )
    assert clause is not None, f"{generated.fixture_id}: клауза delivery_address не найдена"
    assert ".." not in clause.text, (
        f"{generated.fixture_id}: двойная точка в адресе: {clause.text!r}"
    )


def test_e2_section_3_present(generated) -> None:
    """Пункт «3. Срок поставки...» должен быть пронумерован."""
    if generated.flow != "spec":
        return
    text = extract_text(generated.docx_paths["spec"])
    # substring, не startswith: искомая строка сама начинается с номера «3. »
    lines = [line for line in text.split("\n") if "Срок поставки Весов" in line]
    assert lines, f"{generated.fixture_id}: строка «Срок поставки Весов...» не найдена"
    assert lines[0].startswith("3."), (
        f"{generated.fixture_id}: пункт «Срок поставки» без номера «3.»: {lines[0]!r}"
    )


def test_e3a_item_order(generated) -> None:
    """Порядок позиций: Весы→Рама→Пандусы→Доставка→Монтаж→Поверка."""
    if generated.fixture_id != "rama_ploshadka_montazh":
        return
    table = find_spec_table(generated.docx_paths["spec"])
    categories = [_category(name) for name, _ in table.rows]
    categories = [c for c in categories if c is not None]
    assert categories == sorted(categories), (
        f"{generated.fixture_id}: порядок позиций нарушен: "
        f"{[name for name, _ in table.rows]}"
    )


def test_e3b_item_naming(generated) -> None:
    """Наименования позиций == эталонным (FIX_SPEC §E3b)."""
    if generated.fixture_id not in ("rama_ploshadka_montazh", "montazh_orion"):
        return
    for item in generated.items:
        expected = _EXPECTED_NAMES.get(item["id"])
        if expected is not None:
            assert item["name"] == expected, (
                f"{generated.fixture_id}: {item['id']} имя {item['name']!r}, "
                f"ожидалось {expected!r}"
            )

    if generated.fixture_id == "rama_ploshadka_montazh":
        rama_item = next(it for it in generated.items if it["name"].startswith("Рама"))
        assert rama_item["name"] == "Рама 18м для весов ВЕСТА", (
            f"{generated.fixture_id}: рама названа {rama_item['name']!r}, "
            f"ожидалось «Рама 18м для весов ВЕСТА»"
        )
        pandus_item = next(it for it in generated.items if "пандус" in it["name"].lower())
        assert pandus_item["name"] == "Комплект пандусов для весов ВЕСТА-СЛ/ФЛ", (
            f"{generated.fixture_id}: пандусы названы {pandus_item['name']!r}, "
            f"ожидалось «Комплект пандусов для весов ВЕСТА-СЛ/ФЛ»"
        )

    if generated.fixture_id == "montazh_orion":
        orion_item = next(it for it in generated.items if "ОРИОН" in it["name"])
        assert orion_item["name"] == "Программно-аппаратный комплекс «ОРИОН»", (
            f"{generated.fixture_id}: ОРИОН назван {orion_item['name']!r}, "
            f"ожидалось «Программно-аппаратный комплекс «ОРИОН»»"
        )

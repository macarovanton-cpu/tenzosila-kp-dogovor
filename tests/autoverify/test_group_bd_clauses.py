"""Ловушки группы B/D из FIX_SPEC_generation_2026-07-08.md — дубли и клаузы.

D1: строка Госреестра «№ 78871-20» должна встречаться ×1.
D3: «именуемые совместно «Стороны»» должна встречаться ×1 в преамбуле.
D2+B1: клауза «Выезд ... бригады» — формулировка по признаку стройки, без
дублей (сейчас обе формулировки печатаются подряд БЕЗУСЛОВНО, независимо от
сценария — эмпирически подтверждено на всех spec-фикстурах).
"""
from __future__ import annotations

from tests.autoverify.docx_text import extract_text

# fixture_id -> подрядчик строит фундамент сам (foundation_scope in
# contractor_full/contractor_with_materials) -> ожидается «строительной и
# монтажной бригад». Остальные spec-фикстуры с монтажом (без такого
# фундамента) -> ожидается «монтажной бригады» без «строительной».
_CONTRACTOR_BUILDS_FOUNDATION = {"fundament_montazh_poverka", "winter_concrete", "orion"}
_INSTALL_NO_CONTRACTOR_FOUNDATION = {"rama_ploshadka_montazh", "montazh_orion"}


def test_d1_gosreestr_line_once(generated) -> None:
    """Строка с «78871-20» встречается не более 1 раза на документ."""
    for kind, path in generated.docx_paths.items():
        text = extract_text(path)
        count = text.count("78871-20")
        assert count <= 1, f"{generated.fixture_id}/{kind}: «78871-20» встречается {count} раз"


def test_d3_storony_phrase_once(generated) -> None:
    """«именуемые совместно «Стороны»» встречается не более 1 раза на документ."""
    for kind, path in generated.docx_paths.items():
        text = extract_text(path)
        count = text.count("именуемые совместно «Стороны»")
        assert count <= 1, (
            f"{generated.fixture_id}/{kind}: фраза «именуемые совместно «Стороны»» "
            f"встречается {count} раз"
        )


def test_d2b1_crew_dispatch_wording(generated) -> None:
    """Клауза выезда бригады — ровно одна, формулировка по признаку стройки."""
    if generated.fixture_id not in (
        _CONTRACTOR_BUILDS_FOUNDATION | _INSTALL_NO_CONTRACTOR_FOUNDATION
    ):
        return
    text = extract_text(generated.docx_paths["spec"])
    crew_lines = [
        line for line in text.split("\n") if "Выезд" in line and "бригад" in line
    ]
    where = generated.fixture_id
    assert len(crew_lines) == 1, (
        f"{where}: клауза выезда бригады встречается {len(crew_lines)} раз(а), "
        f"ожидалась ровно 1: {crew_lines}"
    )
    line = crew_lines[0]
    if generated.fixture_id in _CONTRACTOR_BUILDS_FOUNDATION:
        assert "строительной и монтажной бригад" in line, (
            f"{where}: подрядчик строит фундамент, но клауза не содержит "
            f"«строительной и монтажной бригад»: {line!r}"
        )
    else:
        assert "строительной" not in line, (
            f"{where}: подрядчик НЕ строит фундамент, но клауза упоминает "
            f"«строительной»: {line!r}"
        )
        assert "монтажной бригады" in line, (
            f"{where}: нет клаузы «Выезд монтажной бригады»: {line!r}"
        )

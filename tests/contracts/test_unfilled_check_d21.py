"""Д21: проверка документа после генерации — поля шаблона во всех XML-частях word/."""
from __future__ import annotations

import dataclasses
import zipfile
from pathlib import Path

import pytest
from docx import Document

from src.contracts.filler import get_unfilled_placeholders, unfilled_fields_error
from tests.autoverify.runner import generate_all
from tests.golden.fixtures import load_fixture

_GOLDEN = sorted(Path("tests/golden/expected").glob("*.docx"))


@pytest.mark.parametrize("path", _GOLDEN, ids=lambda p: p.name)
def test_golden_documents_pass(path: Path) -> None:
    assert get_unfilled_placeholders(str(path)) == []


def _doc_with_leftovers(tmp_path: Path) -> Path:
    """Тело чистое; тег в колонтитуле, тег в надписи, разбитый на runs плейсхолдер, маркер."""
    src = tmp_path / "src.docx"
    doc = Document()
    doc.add_paragraph("body")
    split = doc.add_paragraph()
    split.add_run("{{SPL")
    split.add_run("IT}}")
    doc.add_paragraph("PAYMENT_SECTION")
    doc.sections[0].header.paragraphs[0].text = "{{HEADER_TAG}}"
    doc.save(str(src))
    out = tmp_path / "out.docx"
    textbox = "</w:r><w:r><w:txbxContent><w:p><w:r><w:t>{%if x%}</w:t></w:r></w:p></w:txbxContent>"
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = data.replace(b"<w:t>body</w:t>", ("<w:t>body</w:t>" + textbox).encode())
            zout.writestr(item, data)
    return out


def test_header_textbox_split_and_marker_found(tmp_path: Path) -> None:
    path = _doc_with_leftovers(tmp_path)
    assert get_unfilled_placeholders(str(path)) == [
        "PAYMENT_SECTION", "{%if x%}", "{{HEADER_TAG}}", "{{SPLIT}}",
    ]
    err = unfilled_fields_error("Спецификация", path.read_bytes())
    assert err.startswith("Документ «Спецификация» не сформирован: остались незаполненные поля ")
    assert "{{HEADER_TAG}}" in err


_NEW_OPTIONS = {
    "kbu_p06_35_l_18": 300_000, "ramp_set_concrete": 275_000,
    "foundation_heating_gorynych_5": 90_000, "ppr_documentation": 50_000,
    "canopy_18": 2_800_000, "foundation_under_canopy_18": 1_100_000,
    "canopy_installation_18": 1_600_000, "canopy_lighting": 70_000,
    "frame_18": 140_000, "fence_light_18": 115_000,
    "factory_calibration": 120_000, "bytovka_weigh_room": 200_000,
}


def test_spec_with_all_new_options_tables_in_place(tmp_path: Path) -> None:
    """п. 1.7: ~15 позиций — таблица позиций, комплект и ИТОГО на своих местах."""
    fx = load_fixture("G-01")  # СЛ-60-18, фундамент, монтаж, поверка, доставка
    opts = dict(fx.kp_state["options"])
    for key, price in _NEW_OPTIONS.items():
        opts[key] = {"enabled": True, "price": price, "qty": 1, "customer_side": False}
    result = generate_all(dataclasses.replace(fx, kp_state={**fx.kp_state, "options": opts}), tmp_path)
    assert len(result.items) >= 15

    doc = Document(str(result.docx_paths["spec"]))
    positions = [row.cells[0].text for row in doc.tables[0].rows]
    for item in result.items:
        assert item["name"] in positions, item["name"]
    total = int(sum(i["total"] for i in result.items))
    assert doc.tables[0].rows[-1].cells[-1].text == f"{total:,}".replace(",", " ")
    assert "ИТОГО" in doc.tables[0].rows[-1].cells[0].text
    kit = " ".join(row.cells[0].text for row in doc.tables[2].rows)
    assert "Датчик весоизмерительный" in kit and "Терминал весовой" in kit

"""Тесты на корректность плейсхолдеров в DOCX-шаблонах договора."""
from pathlib import Path

from docx import Document

CONTRACTS = Path("templates/contracts")


def _header_text(docx_path: Path) -> str:
    doc = Document(docx_path)
    parts = []
    for section in doc.sections:
        for p in section.header.paragraphs:
            parts.append(p.text)
    return "\n".join(parts)


def _all_text(docx_path: Path) -> str:
    doc = Document(docx_path)
    parts = []
    for p in doc.paragraphs:
        parts.append(p.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    parts.append(p.text)
    return "\n".join(parts)


def test_contract_header_has_placeholder():
    text = _header_text(CONTRACTS / "contract.docx")
    assert "{{ДОГОВОР_НОМЕР}}" in text, f"Hardcoded header: {text!r}"
    assert "{{ДОГОВОР_ДАТА_ПОЛНАЯ}}" in text


def test_spec_header_has_placeholder():
    text = _header_text(CONTRACTS / "spec_foundation_install.docx")
    assert "{{ДОГОВОР_НОМЕР}}" in text, f"Hardcoded header: {text!r}"


def test_spec_no_kompaniya_tenzosila():
    text = _all_text(CONTRACTS / "spec_foundation_install.docx")
    assert "Компания Тензосила" not in text, "Нашли захардкоженное название"


def test_spec_has_tpk_tenzosila():
    text = _all_text(CONTRACTS / "spec_foundation_install.docx")
    assert "ТПК" in text, "ООО «ТПК «Тензосила»» должно быть в тексте"

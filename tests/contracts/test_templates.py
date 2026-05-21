"""Тесты на корректность плейсхолдеров и вёрстки DOCX-шаблонов договора."""
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

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


# --- вёрстка ---

def _body_paras(doc):
    body_tag = qn("w:body")
    return [p for p in doc.paragraphs if p._p.getparent().tag == body_tag]


def _find_body_para(doc, contains: str):
    for p in _body_paras(doc):
        if contains in p.text:
            return p
    return None


def _has_para_prop(para, prop_name: str) -> bool:
    pPr = para._p.find(qn("w:pPr"))
    if pPr is None:
        return False
    el = pPr.find(qn(prop_name))
    if el is None:
        return False
    return el.get(qn("w:val"), "1") not in ("0", "false", "off")


def test_spec_п14_has_page_break_before():
    doc = Document(CONTRACTS / "spec_foundation_install.docx")
    p = _find_body_para(doc, "Технические характеристики")
    assert p is not None, "Параграф 'Технические характеристики' не найден"
    assert _has_para_prop(p, "w:pageBreakBefore"), "п.14 должен иметь pageBreakBefore"


def test_spec_приложение_has_page_break_before():
    doc = Document(CONTRACTS / "spec_foundation_install.docx")
    p = _find_body_para(doc, "Приложение №{{СПЕЦ_НОМЕР}}")
    assert p is not None, "Параграф 'Приложение №' не найден"
    assert _has_para_prop(p, "w:pageBreakBefore"), "Приложение должно иметь pageBreakBefore"

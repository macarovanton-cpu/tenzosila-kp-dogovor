"""spec_v2_filler.py — рендер спецификации v2 с динамическими clauses."""
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from src.contracts.filler import fill_spec_with_items

_CLAUSE_SECTION_ORDER = [
    "obligations_supplier",
    "obligations_customer",
    "special_conditions",
    "final",
]

_CLAUSE_SECTION_HEADERS = {
    "obligations_supplier": "4. Обязательства Подрядчика",
    "obligations_customer": "5. Обязательства Заказчика",
    "special_conditions": "6. Особые условия",
    "final": "7. Заключительные положения",
}


def _make_clause_para(
    text: str, bold: bool = False, justify: bool = False,
):
    """Создать XML-элемент параграфа для clause секции."""
    p = OxmlElement('w:p')
    if justify:
        pPr = OxmlElement('w:pPr')
        jc = OxmlElement('w:jc')
        jc.set(qn('w:val'), 'both')
        pPr.append(jc)
        p.append(pPr)
    if not text:
        return p
    lines = text.split('\n')
    for i, line in enumerate(lines):
        r = OxmlElement('w:r')
        if bold:
            rPr = OxmlElement('w:rPr')
            rPr.append(OxmlElement('w:b'))
            r.append(rPr)
        t_el = OxmlElement('w:t')
        t_el.text = line
        t_el.set(qn('xml:space'), 'preserve')
        r.append(t_el)
        p.append(r)
        if i < len(lines) - 1:
            br_r = OxmlElement('w:r')
            if bold:
                br_rPr = OxmlElement('w:rPr')
                br_rPr.append(OxmlElement('w:b'))
                br_r.append(br_rPr)
            br_r.append(OxmlElement('w:br'))
            p.append(br_r)
    return p


def fill_spec_v2(
    template_path: str,
    data: dict,
    items: list[dict],
    deal: dict,
    output_path: str,
) -> None:
    """Рендер спецификации v2: таблица позиций + динамические clauses.

    Трёхшаговый подход:
    1. fill_spec_with_items() для таблицы и {{}} плейсхолдеров.
    2. build_contract_clauses(deal) — фильтрация и рендер clauses.
    3. python-docx: замена маркеров на параграфы clauses.
    """
    from src.contracts.clauses_renderer import build_contract_clauses

    fill_spec_with_items(template_path, data, items, output_path)

    clauses_by_section = build_contract_clauses(deal)

    doc = Document(output_path)
    for section_id in _CLAUSE_SECTION_ORDER:
        marker = "{{CLAUSE_SECTION_" + section_id + "}}"
        clauses = clauses_by_section.get(section_id, [])
        for para in doc.paragraphs:
            if marker in para.text:
                p_el = para._element
                if clauses:
                    p_el.addprevious(_make_clause_para(""))
                    header = _CLAUSE_SECTION_HEADERS[section_id]
                    p_el.addprevious(_make_clause_para(header, bold=True))
                    for clause in clauses:
                        text = f"{clause.auto_number}. {clause.text}"
                        p_el.addprevious(
                            _make_clause_para(text, justify=True)
                        )
                p_el.getparent().remove(p_el)
                break
    doc.save(output_path)

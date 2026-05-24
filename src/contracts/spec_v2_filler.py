"""spec_v2_filler.py — рендер спецификации v2 с динамическими clauses."""
import copy

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from src.contracts.clauses_context import build_clauses_context
from src.contracts.filler import fill_spec_with_items, _set_cell_text

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

_CHECK_LABELS = [
    ("L, мм", "h4, мм", "h11, мм"),
    ("W, мм", "h5, мм", "h12, мм"),
    ("Х1, мм", "h6, мм", "L1, мм"),
    ("Х2, мм", "h7, мм", "L2, мм"),
    ("h1, мм", "h8, мм", "L3, мм"),
    ("h2, мм", "h9, мм", ""),
    ("h3, мм", "h10, мм", ""),
]


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


def _replace_marker_with_paragraphs(
    doc, marker: str, lines: list[str],
) -> bool:
    """Заменить {{MARKER}} на список параграфов. Возвращает True если нашёл."""
    for para in doc.paragraphs:
        if marker in para.text:
            p_el = para._element
            for line in reversed(lines):
                p_el.addnext(_make_clause_para(line))
            p_el.getparent().remove(p_el)
            return True
    return False


def _remove_marker(doc, marker: str) -> bool:
    """Удалить параграф с маркером. Возвращает True если нашёл."""
    for para in doc.paragraphs:
        if marker in para.text:
            para._element.getparent().remove(para._element)
            return True
    return False


def _fill_kit_table(doc, kit_items: list[dict]) -> None:
    """Заполнить таблицу комплекта поставки (Table 2) клонированием шаблонной строки."""
    if len(doc.tables) < 3:
        return
    table = doc.tables[2]
    tbl = table._tbl
    all_trs = list(tbl.iterchildren(qn('w:tr')))
    if len(all_trs) < 2:
        return

    template_tr = copy.deepcopy(all_trs[1])
    tbl.remove(all_trs[1])

    all_trs = list(tbl.iterchildren(qn('w:tr')))
    header_tr = all_trs[0]

    for item in reversed(kit_items):
        new_tr = copy.deepcopy(template_tr)
        tcs = [c for c in new_tr if c.tag == qn('w:tc')]
        if tcs:
            _set_cell_text(tcs[0], item.get("name", ""))
        if len(tcs) > 1:
            _set_cell_text(tcs[1], item.get("qty", ""))
        header_tr.addnext(new_tr)


def _make_table_3col(labels: list[tuple[str, str, str]]):
    """Создать XML таблицы 3 колонки из списка кортежей-меток."""
    tbl = OxmlElement('w:tbl')
    tblPr = OxmlElement('w:tblPr')
    tblStyle = OxmlElement('w:tblStyle')
    tblStyle.set(qn('w:val'), 'TableGrid')
    tblPr.append(tblStyle)
    tblW = OxmlElement('w:tblW')
    tblW.set(qn('w:w'), '0')
    tblW.set(qn('w:type'), 'auto')
    tblPr.append(tblW)
    tbl.append(tblPr)
    tblGrid = OxmlElement('w:tblGrid')
    for _ in range(3):
        tblGrid.append(OxmlElement('w:gridCol'))
    tbl.append(tblGrid)

    for row_labels in labels:
        tr = OxmlElement('w:tr')
        for label in row_labels:
            tc = OxmlElement('w:tc')
            p = OxmlElement('w:p')
            if label:
                r = OxmlElement('w:r')
                t = OxmlElement('w:t')
                t.text = label
                t.set(qn('xml:space'), 'preserve')
                r.append(t)
                p.append(r)
            tc.append(p)
            tr.append(tc)
        tbl.append(tr)
    return tbl


def _render_foundation_check(doc, data: dict) -> bool:
    """Вставить контрольный лист фундамента вместо маркера."""
    marker = "{{APPENDIX_FOUNDATION_CHECK}}"
    for para in doc.paragraphs:
        if marker in para.text:
            p_el = para._element
            parent = p_el.getparent()

            model_short = data.get("СПЕЦ_МОДЕЛЬ_КРАТКОЕ", "")

            note_p = _make_clause_para(
                "Примечание: Размеры h – абсолютные значения по нивелиру (по рейке в мм)"
            )
            parent.insert(list(parent).index(p_el) + 1, note_p)

            check_tbl = _make_table_3col(_CHECK_LABELS)
            parent.insert(list(parent).index(p_el) + 1, check_tbl)

            subtitle = _make_clause_para(
                f"Контрольный лист на фундамент весов {model_short}",
                bold=True,
            )
            parent.insert(list(parent).index(p_el) + 1, subtitle)

            parent.insert(list(parent).index(p_el) + 1, _make_clause_para(""))

            parent.remove(p_el)
            return True
    return False


def fill_spec_v2(
    template_path: str,
    data: dict,
    items: list[dict],
    deal: dict,
    output_path: str,
) -> None:
    """Рендер спецификации v2: таблица позиций + динамические секции.

    data может содержать:
      _payment_lines: list[str] — строки оплаты
      _terms_lines:   list[str] — строки сроков
      _kit_items:     list[dict] — [{name, qty}] для комплекта
    """
    from src.contracts.clauses_renderer import build_contract_clauses

    fill_spec_with_items(template_path, data, items, output_path)

    doc = Document(output_path)

    # --- Payment ---
    payment_lines = data.get("_payment_lines", [])
    if payment_lines:
        _replace_marker_with_paragraphs(doc, "{{PAYMENT_SECTION}}", payment_lines)
    else:
        _remove_marker(doc, "{{PAYMENT_SECTION}}")

    # --- Terms ---
    terms_lines = data.get("_terms_lines", [])
    if terms_lines:
        _replace_marker_with_paragraphs(doc, "{{TERMS_SECTION}}", terms_lines)
    else:
        _remove_marker(doc, "{{TERMS_SECTION}}")

    # --- Kit ---
    kit_items = data.get("_kit_items", [])
    if kit_items:
        _fill_kit_table(doc, kit_items)

    # --- Foundation check appendix ---
    ctx = build_clauses_context(deal)
    if ctx["foundation_scope"] == "customer_builds":
        _render_foundation_check(doc, data)
    else:
        _remove_marker(doc, "{{APPENDIX_FOUNDATION_CHECK}}")

    # --- Clauses ---
    clauses_by_section = build_contract_clauses(deal)
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

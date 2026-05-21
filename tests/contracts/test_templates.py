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


def _row_has_cant_split(row) -> bool:
    trPr = row._tr.find(qn("w:trPr"))
    if trPr is None:
        return False
    cs = trPr.find(qn("w:cantSplit"))
    if cs is None:
        return False
    return cs.get(qn("w:val"), "1") not in ("0", "false", "off")


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


def test_spec_footer_has_page_field():
    """Шаблон spec_foundation_install.docx содержит поле PAGE в footer2."""
    import zipfile
    with zipfile.ZipFile(CONTRACTS / "spec_foundation_install.docx") as z:
        footer_xml = z.read("word/footer2.xml").decode("utf-8")
    assert "instrText" in footer_xml, "instrText отсутствует в footer2"
    assert "PAGE" in footer_xml, "Поле PAGE отсутствует в footer2"


def test_spec_п15_has_keep_with_next():
    """Параграф п.15 (Комплект поставки) имеет keepWithNext."""
    doc = Document(CONTRACTS / "spec_foundation_install.docx")
    p = _find_body_para(doc, "Комплект поставки")
    assert p is not None, "Параграф 'Комплект поставки' не найден"
    assert _has_para_prop(p, "w:keepNext"), "п.15 должен иметь keepNext"


def test_spec_table2_rows_have_cant_split():
    """Все строки TABLE[2] (Комплект поставки) имеют cantSplit."""
    doc = Document(CONTRACTS / "spec_foundation_install.docx")
    assert len(doc.tables) > 2, "TABLE[2] не найдена в шаблоне"
    for i, row in enumerate(doc.tables[2].rows):
        assert _row_has_cant_split(row), (
            f"TABLE[2] row[{i}] должна иметь cantSplit"
        )


def test_spec_no_kratkoe_placeholder():
    """Плейсхолдер ЗАКАЗЧИК_ДИРЕКТОР_ФИО_КРАТКОЕ отсутствует в шаблоне."""
    import zipfile
    with zipfile.ZipFile(CONTRACTS / "spec_foundation_install.docx") as z:
        for name in z.namelist():
            if name.endswith(".xml"):
                text = z.read(name).decode("utf-8")
                assert "ЗАКАЗЧИК_ДИРЕКТОР_ФИО_КРАТКОЕ" not in text, (
                    f"Устаревший плейсхолдер найден в {name}"
                )


def test_spec_appendix_has_initsialy():
    """Приложение №1 содержит {{ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ}} (минимум 2 вхождения в XML)."""
    import zipfile
    with zipfile.ZipFile(CONTRACTS / "spec_foundation_install.docx") as z:
        content = z.read("word/document.xml").decode("utf-8")
    assert content.count("ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ") >= 2, (
        "ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ должен встречаться минимум 2 раза: "
        "таблица подписей + Приложение №1"
    )


def test_spec_kwn_chain_until_signatures():
    """Цепочка keepNext непрерывна: п.14 → пустые → п.15 → пустой → [61], TABLE[3] cantSplit."""
    doc = Document(CONTRACTS / "spec_foundation_install.docx")
    body_paras = _body_paras(doc)

    p14_idx = next(
        i for i, p in enumerate(body_paras) if "Технические характеристики" in p.text
    )
    p15_idx = next(
        i for i, p in enumerate(body_paras) if "Комплект поставки" in p.text
    )

    # body_paras от п.14 до пустого после п.15 включительно (p14_idx .. p15_idx+1)
    for i in range(p14_idx, p15_idx + 2):
        p = body_paras[i]
        assert _has_para_prop(p, "w:keepNext"), (
            f"body_paras[{i}] {p.text[:40]!r} должен иметь keepNext"
        )

    # body_paras[p15_idx+2] — пустой параграф [61] перед таблицей подписей
    p61 = body_paras[p15_idx + 2]
    assert _has_para_prop(p61, "w:keepNext"), (
        "Параграф перед таблицей подписей (body_paras[p15_idx+2]) должен иметь keepNext"
    )

    # Таблица подписей (doc.tables[3]) — cantSplit
    assert len(doc.tables) > 3, "doc.tables[3] (подписи) не найдена"
    for i, row in enumerate(doc.tables[3].rows):
        assert _row_has_cant_split(row), f"doc.tables[3] row[{i}] должна иметь cantSplit"


def test_spec_max_empty_paras_between_th_and_kompl():
    """Между таблицей ТХ и заголовком п.15 не более 1 пустого параграфа."""
    doc = Document(CONTRACTS / "spec_foundation_install.docx")
    body_paras = _body_paras(doc)
    p14_idx = next(
        i for i, p in enumerate(body_paras) if "Технические характеристики" in p.text
    )
    p15_idx = next(
        i for i, p in enumerate(body_paras) if "Комплект поставки" in p.text
    )
    # p14_idx+2 .. p15_idx — параграфы после p.14 и его empty-пары до заголовка п.15
    between = body_paras[p14_idx + 2 : p15_idx]
    assert len(between) <= 1, (
        f"Между таблицей ТХ и заголовком п.15 должно быть не более 1 пустого параграфа, "
        f"найдено {len(between)}"
    )

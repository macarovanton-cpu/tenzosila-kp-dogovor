"""Тесты склейки спецификации с внешними приложениями."""
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from src.contracts.compose import compose_spec_with_attachments
from src.contracts.filler import get_unfilled_placeholders


def _make_spec(path: Path) -> None:
    doc = Document()
    doc.add_paragraph("Начало спецификации")
    doc.add_paragraph("Конец спецификации")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Поставщик"
    table.rows[0].cells[1].text = "Заказчик"
    doc.save(path)


def _make_appendix(path: Path, title: str, page_break_before: bool = False) -> None:
    doc = Document()
    p = doc.add_paragraph(f"Приложение №{{{{ПРИЛОЖЕНИЕ_НОМЕР}}}}. {title}")
    p.paragraph_format.page_break_before = page_break_before
    doc.add_paragraph("К Спецификации №{{СПЕЦ_НОМЕР}}")
    doc.add_paragraph("К Договору №{{ДОГОВОР_НОМЕР}} от {{ДОГОВОР_ДАТА_ПОЛНАЯ}}")
    doc.add_paragraph("Утверждаю {{ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ}}")
    doc.save(path)


def _all_text(doc: Document) -> str:
    texts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                texts.append(cell.text)
    return "\n".join(texts)


def _paragraph_text(p_el) -> str:
    return "".join(t.text or "" for t in p_el.findall(".//" + qn("w:t")))


def _has_page_break(p_el) -> bool:
    if p_el.find(".//" + qn("w:pageBreakBefore")) is not None:
        return True
    for br in p_el.findall(".//" + qn("w:br")):
        if br.get(qn("w:type")) == "page":
            return True
    return False


def _body_paragraphs(doc: Document) -> list:
    return [el for el in doc.element.body.iterchildren() if el.tag == qn("w:p")]


def _data() -> dict:
    return {
        "СПЕЦ_НОМЕР": "7",
        "ДОГОВОР_НОМЕР": "Д-42",
        "ДОГОВОР_ДАТА_ПОЛНАЯ": "10 июня 2026 г.",
        "ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ": "И.И. Иванов",
    }


def test_compose_both(tmp_path: Path) -> None:
    spec = tmp_path / "spec.docx"
    build_task = tmp_path / "build_task.docx"
    control_sheet = tmp_path / "control_sheet.docx"
    _make_spec(spec)
    _make_appendix(build_task, "Строительное задание")
    _make_appendix(control_sheet, "Контрольный лист")

    before_count = len(Document(spec).paragraphs)
    compose_spec_with_attachments(
        spec,
        {
            "build_task_path": str(build_task),
            "build_task_source": "manual",
            "include_control_sheet": True,
            "control_sheet_path": str(control_sheet),
        },
        _data(),
    )

    doc = Document(spec)
    text = _all_text(doc)
    assert len(doc.paragraphs) > before_count
    assert "Строительное задание" in text
    assert "Контрольный лист" in text
    assert "Поставщик" in text
    assert "Заказчик" in text


def test_compose_build_task_only(tmp_path: Path) -> None:
    spec = tmp_path / "spec.docx"
    build_task = tmp_path / "build_task.docx"
    control_sheet = tmp_path / "control_sheet.docx"
    _make_spec(spec)
    _make_appendix(build_task, "Строительное задание")
    _make_appendix(control_sheet, "Контрольный лист")

    compose_spec_with_attachments(
        spec,
        {
            "build_task_path": str(build_task),
            "build_task_source": "manual",
            "include_control_sheet": False,
            "control_sheet_path": str(control_sheet),
        },
        _data(),
    )

    text = _all_text(Document(spec))
    assert "Строительное задание" in text
    assert "Контрольный лист" not in text


def test_compose_none_leaves_file_unchanged(tmp_path: Path) -> None:
    spec = tmp_path / "spec.docx"
    _make_spec(spec)
    before = spec.read_bytes()

    compose_spec_with_attachments(
        spec,
        {
            "build_task_path": "",
            "build_task_source": "none",
            "include_control_sheet": False,
            "control_sheet_path": "",
        },
        _data(),
    )

    assert spec.read_bytes() == before


def test_placeholders_filled(tmp_path: Path) -> None:
    spec = tmp_path / "spec.docx"
    build_task = tmp_path / "build_task.docx"
    _make_spec(spec)
    _make_appendix(build_task, "Строительное задание")

    compose_spec_with_attachments(
        spec,
        {
            "build_task_path": str(build_task),
            "build_task_source": "manual",
            "include_control_sheet": False,
            "control_sheet_path": "",
        },
        _data(),
    )

    text = _all_text(Document(spec))
    assert "{{" not in text
    assert get_unfilled_placeholders(str(spec)) == []
    assert "К Спецификации №7" in text
    assert "Д-42" in text


def test_numbering_is_fixed_by_attachment_type(tmp_path: Path) -> None:
    spec = tmp_path / "spec.docx"
    build_task = tmp_path / "build_task.docx"
    control_sheet = tmp_path / "control_sheet.docx"
    _make_spec(spec)
    _make_appendix(build_task, "Строительное задание")
    _make_appendix(control_sheet, "Контрольный лист")

    compose_spec_with_attachments(
        spec,
        {
            "build_task_path": str(build_task),
            "build_task_source": "manual",
            "include_control_sheet": True,
            "control_sheet_path": str(control_sheet),
        },
        _data(),
    )

    text = _all_text(Document(spec))
    assert "Приложение №1. Строительное задание" in text
    assert "Приложение №2. Контрольный лист" in text


def test_no_blank_page_break_between_spec_and_first_appendix(tmp_path: Path) -> None:
    spec = tmp_path / "spec.docx"
    build_task = tmp_path / "build_task.docx"
    _make_spec(spec)
    _make_appendix(build_task, "Строительное задание", page_break_before=True)

    compose_spec_with_attachments(
        spec,
        {
            "build_task_path": str(build_task),
            "build_task_source": "manual",
            "include_control_sheet": False,
            "control_sheet_path": "",
        },
        _data(),
    )

    doc = Document(spec)
    paragraphs = _body_paragraphs(doc)
    spec_end_idx = next(
        i for i, p_el in enumerate(paragraphs)
        if _paragraph_text(p_el) == "Конец спецификации"
    )
    appendix_idx = next(
        i for i, p_el in enumerate(paragraphs)
        if "Приложение №1. Строительное задание" in _paragraph_text(p_el)
    )
    between = paragraphs[spec_end_idx + 1:appendix_idx]

    assert all(_paragraph_text(p_el).strip() for p_el in between)
    assert not any(_has_page_break(p_el) for p_el in between)
    assert not _has_page_break(paragraphs[appendix_idx])

"""Склейка спецификации с внешними DOCX-приложениями."""
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docxcompose.composer import Composer

from src.contracts.filler import fill_template


def _collect_appendices(attachments: dict) -> list[tuple[Path, int]]:
    """Вернуть пути и фиксированные номера: build_task -> 1, control_sheet -> 2."""
    out: list[tuple[Path, int]] = []
    build_task = (attachments.get("build_task_path") or "").strip()
    if build_task and attachments.get("build_task_source") != "none":
        out.append((Path(build_task), 1))

    control_sheet = (attachments.get("control_sheet_path") or "").strip()
    if attachments.get("include_control_sheet") and control_sheet:
        out.append((Path(control_sheet), 2))
    return out


def _remove_first_page_break_before(doc) -> None:
    """Убрать pageBreakBefore с первого параграфа приложения перед docxcompose."""
    if not doc.paragraphs:
        return
    p_pr = doc.paragraphs[0]._p.pPr
    if p_pr is None:
        return
    page_break = p_pr.find(qn("w:pageBreakBefore"))
    if page_break is not None:
        p_pr.remove(page_break)


def compose_spec_with_attachments(
    spec_path: Path,
    attachments: dict,
    data: dict,
) -> None:
    """Подклеить приложения к спецификации на месте.

    Порядок: Спецификация -> Приложение N1 (build_task) -> N2 (control_sheet).
    Пути берутся из attachments. Если приложений нет, файл не меняется.
    """
    appendices = _collect_appendices(attachments)
    if not appendices:
        return

    spec_path = Path(spec_path)
    composer = Composer(Document(str(spec_path)))
    tmp_files: list[Path] = []
    try:
        for src, number in appendices:
            filled = spec_path.parent / f"_attach_{number}_{spec_path.stem}.docx"
            fill_template(
                str(src),
                {**data, "ПРИЛОЖЕНИЕ_НОМЕР": str(number)},
                str(filled),
            )
            tmp_files.append(filled)
            appendix_doc = Document(str(filled))
            _remove_first_page_break_before(appendix_doc)
            appendix_doc.save(str(filled))
            composer.append(appendix_doc)
        composer.save(str(spec_path))
    finally:
        for tmp_file in tmp_files:
            tmp_file.unlink(missing_ok=True)

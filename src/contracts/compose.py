"""Склейка спецификации с внешними DOCX-приложениями."""
import tempfile
from pathlib import Path

from docx import Document
from docxcompose.composer import Composer
from docxtpl import DocxTemplate

from src.contracts.filler import fill_template
from src.contracts.spec_v2_filler import _remove_marker, _replace_marker_with_paragraphs

_SUPPLY_TEMPLATES = Path("templates/contracts")


def compose_supply(context: dict, output_path: Path) -> None:
    """Рендер 3 шаблонов договора поставки и склейка в один DOCX.

    context — результат supply_filler.build_supply_context().
    Ключ _payment_lines используется для двупрохода (docxtpl → python-docx).
    Остальные ключи передаются docxtpl напрямую.
    """
    payment_lines: list[str] = context.get("_payment_lines", [])
    # Контекст для docxtpl: без служебных ключей с подчёркиванием
    tpl_context = {k: v for k, v in context.items() if not k.startswith("_")}

    tmp_files: list[Path] = []
    try:
        # --- 1. supply_contract (двупроход) ---
        contract_tpl = _SUPPLY_TEMPLATES / "supply_contract.docx"
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            contract_tmp1 = Path(f.name)
        tmp_files.append(contract_tmp1)

        tpl = DocxTemplate(str(contract_tpl))
        tpl.render(tpl_context)
        tpl.save(str(contract_tmp1))

        # Второй проход: заменить {{PAYMENT_SECTION}} реальными параграфами.
        # Пустой список оплаты → удалить маркер, иначе в п.4.2 остаётся пустой блок.
        contract_doc = Document(str(contract_tmp1))
        if payment_lines:
            _replace_marker_with_paragraphs(
                contract_doc, "{{PAYMENT_SECTION}}", payment_lines
            )
        else:
            _remove_marker(contract_doc, "{{PAYMENT_SECTION}}")
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            contract_tmp2 = Path(f.name)
        tmp_files.append(contract_tmp2)
        contract_doc.save(str(contract_tmp2))

        # --- 2. supply_appendix_1 ---
        appendix1_tpl = _SUPPLY_TEMPLATES / "supply_appendix_1.docx"
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            app1_tmp = Path(f.name)
        tmp_files.append(app1_tmp)
        tpl1 = DocxTemplate(str(appendix1_tpl))
        tpl1.render(tpl_context)
        tpl1.save(str(app1_tmp))

        # --- 3. supply_appendix_2 ---
        appendix2_tpl = _SUPPLY_TEMPLATES / "supply_appendix_2.docx"
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            app2_tmp = Path(f.name)
        tmp_files.append(app2_tmp)
        tpl2 = DocxTemplate(str(appendix2_tpl))
        tpl2.render(tpl_context)
        tpl2.save(str(app2_tmp))

        # --- Склейка через docxcompose ---
        composer = Composer(Document(str(contract_tmp2)))

        for app_tmp in (app1_tmp, app2_tmp):
            app_doc = Document(str(app_tmp))
            _ensure_first_page_break_before(app_doc)
            composer.append(app_doc)

        composer.save(str(output_path))
    finally:
        for tmp_file in tmp_files:
            tmp_file.unlink(missing_ok=True)


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


def _ensure_first_page_break_before(doc) -> None:
    """Поставить pageBreakBefore на первый параграф приложения перед docxcompose."""
    if not doc.paragraphs:
        return
    doc.paragraphs[0].paragraph_format.page_break_before = True


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
            _ensure_first_page_break_before(appendix_doc)
            appendix_doc.save(str(filled))
            composer.append(appendix_doc)
        composer.save(str(spec_path))
    finally:
        for tmp_file in tmp_files:
            tmp_file.unlink(missing_ok=True)

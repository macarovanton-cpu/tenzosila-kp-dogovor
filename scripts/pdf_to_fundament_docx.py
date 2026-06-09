"""CLI конвертера PDF-чертежей фундаментов в DOCX-приложения."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.pdf_to_fundament_core import (
    CS_OUT,
    CS_SRC,
    FIRST_PAGE_IMAGE_MAX_H_EMU,
    NEXT_PAGE_IMAGE_MAX_H_EMU,
    OUT_DIR,
    SRC_DIR,
    TEXTBOX_ANCHOR_BASE_ID,
    TEXTBOX_DOC_PR_BASE_ID,
    TEXTBOX_HEIGHT_EMU,
    TEXTBOX_WIDTH_EMU,
    USABLE_W_EMU,
    WP14_ANCHOR_ID_ATTR,
    WPS_TXBX_TAG,
    _clone_textbox,
    _image_emu,
    _load_reference_parts,
    _pdf_files,
    _render_pages,
    convert,
)


def _iter_batch() -> list[tuple[Path, Path]]:
    jobs: list[tuple[Path, Path]] = []
    for pdf_path in _pdf_files(SRC_DIR):
        jobs.append((pdf_path, OUT_DIR / f"{pdf_path.stem}.docx"))
    for pdf_path in _pdf_files(CS_SRC):
        jobs.append((pdf_path, CS_OUT / f"{pdf_path.stem}.docx"))
    return jobs


def _convert_many(jobs: list[tuple[Path, Path]]) -> int:
    errors = 0
    total = len(jobs)
    for idx, (pdf_path, out_path) in enumerate(jobs, start=1):
        prefix = f"[{idx}/{total}] {pdf_path.name} ..."
        try:
            convert(pdf_path, out_path)
        except Exception as exc:  # noqa: BLE001 - CLI должен продолжать пакет.
            errors += 1
            print(f"{prefix} ERROR: {exc}")
        else:
            print(f"{prefix} OK")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Конвертировать PDF-чертежи фундаментов в DOCX-приложения."
    )
    parser.add_argument("pdf", nargs="?", type=Path, help="PDF-файл для конвертации")
    parser.add_argument("--all", action="store_true", help="Конвертировать все PDF из папок")
    args = parser.parse_args(argv)

    if args.all:
        jobs = _iter_batch()
        if not jobs:
            print("PDF-файлы не найдены.")
            return 0
        return 1 if _convert_many(jobs) else 0

    if args.pdf is None:
        parser.error("укажите PDF-файл или --all")

    out_path = OUT_DIR / f"{args.pdf.stem}.docx"
    return 1 if _convert_many([(args.pdf, out_path)]) else 0


if __name__ == "__main__":
    raise SystemExit(main())

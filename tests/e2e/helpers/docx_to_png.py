"""DOCX → PDF (LibreOffice) → PNG (pdf2image/poppler).

Зависимости: soffice в PATH (или через SOFFICE_BIN), poppler в PATH.
На Windows: https://github.com/oschwartz10612/poppler-windows/releases
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _resolve_soffice() -> str:
    explicit = os.getenv("SOFFICE_BIN")
    if explicit and Path(explicit).exists():
        return explicit
    found = shutil.which("soffice") or shutil.which("soffice.exe")
    if found:
        return found
    # Типичный путь установки на Windows
    win_default = Path(r"C:\Program Files\LibreOffice\program\soffice.exe")
    if win_default.exists():
        return str(win_default)
    raise FileNotFoundError(
        "soffice не найден. Установите LibreOffice и/или задайте SOFFICE_BIN."
    )


class PopplerMissing(RuntimeError):
    """Poppler-binaries (pdftoppm/pdfinfo) недоступны для pdf2image."""


def docx_to_pdf(docx: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    soffice = _resolve_soffice()
    completed = subprocess.run(
        [
            soffice,
            "--headless",
            "--norestore",
            "--nologo",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(docx),
        ],
        capture_output=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "soffice failed: "
            f"{completed.stdout!r} / {completed.stderr!r}"
        )
    pdf = out_dir / (docx.stem + ".pdf")
    if not pdf.exists():
        # soffice иногда нормализует имя
        candidates = list(out_dir.glob(f"{docx.stem}*.pdf"))
        if not candidates:
            raise RuntimeError(f"PDF не появился в {out_dir}")
        pdf = candidates[0]
    return pdf


def pdf_to_pngs(pdf: Path, out_dir: Path, dpi: int = 150) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        from pdf2image import convert_from_path
    except ImportError as exc:
        raise PopplerMissing(
            "Установите pdf2image: pip install pdf2image"
        ) from exc
    try:
        pages = convert_from_path(str(pdf), dpi=dpi)
    except Exception as exc:  # pdf2image.exceptions.PDFInfoNotInstalledError и т.п.
        raise PopplerMissing(
            f"poppler/pdftoppm недоступны: {exc}. "
            "Установите poppler-windows и добавьте в PATH."
        ) from exc

    paths: list[Path] = []
    for i, img in enumerate(pages, 1):
        p = out_dir / f"{pdf.stem}_p{i:02d}.png"
        img.save(p, "PNG")
        paths.append(p)
    return paths


def docx_to_png(docx: Path, out_dir: Path, dpi: int = 150) -> list[Path]:
    pdf = docx_to_pdf(docx, out_dir)
    return pdf_to_pngs(pdf, out_dir, dpi=dpi)


__all__ = ["docx_to_pdf", "pdf_to_pngs", "docx_to_png", "PopplerMissing"]

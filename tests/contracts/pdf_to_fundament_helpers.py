"""Общие helper-функции для тестов pdf_to_fundament_docx."""
import struct
import zipfile
from pathlib import Path

import fitz
from lxml import etree


REFERENCE = Path("templates/contracts/spec_v2.docx")
WP14_ANCHOR_ID_ATTR = (
    "{http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing}anchorId"
)
XML_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "wp14": "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
}


def png_size(data: bytes) -> tuple[int, int]:
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return struct.unpack(">II", data[16:24])


def make_a3_landscape_pdf(path: Path, pages: int = 2) -> None:
    doc = fitz.open()
    for page_idx in range(pages):
        page = doc.new_page(width=1190.55, height=841.89)
        page.insert_text((72, 72), f"A3 landscape page {page_idx + 1}")
    doc.save(path)
    doc.close()


def docx_xml(path: Path, name: str) -> str:
    with zipfile.ZipFile(path) as docx:
        return docx.read(name).decode("utf-8")


def docx_root(path: Path, name: str):
    with zipfile.ZipFile(path) as docx:
        return etree.fromstring(docx.read(name))

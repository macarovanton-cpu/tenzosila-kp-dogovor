"""Д20 (N7): спецсимволы &, <, > в имени клиента не ломают XML генерируемых DOCX."""
from __future__ import annotations

import dataclasses
import re
import zipfile
from pathlib import Path

import pytest
from docx import Document
from lxml import etree

from src.contracts.filler import _replace_textbox_placeholders
from tests.autoverify.docx_text import extract_text
from tests.autoverify.runner import generate_all
from tests.golden.fixtures import load_fixture

NAME = "ООО «А&Б» <тест>"


def _check_docx(path: Path) -> None:
    """DOCX читается python-docx, все XML-части парсятся, текст имени цел."""
    Document(str(path))
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.endswith((".xml", ".rels")):
                etree.fromstring(z.read(n))
        assert b"&amp;amp;" not in z.read("word/document.xml")
    assert NAME in extract_text(path), path.name


@pytest.mark.parametrize("fixture_id", ["G-01", "G-04"])
def test_special_chars_in_client_name(fixture_id: str, tmp_path: Path) -> None:
    fx = load_fixture(fixture_id)
    fx = dataclasses.replace(
        fx,
        kp_state={**fx.kp_state, "client_name": NAME},
        requisites={
            **fx.requisites,
            "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": NAME,
            "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ": NAME,
        },
    )
    result = generate_all(fx, tmp_path)
    for path in result.docx_paths.values():
        _check_docx(path)


def test_textbox_placeholder_escaped(tmp_path: Path) -> None:
    path = tmp_path / "t.docx"
    doc = Document()
    doc.add_paragraph("x")
    doc.save(str(path))
    # Кладём плейсхолдер в сырой XML части, как в text box
    tmp2 = tmp_path / "t2.docx"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp2, "w") as zout:
        for item in zin.infolist():
            b = zin.read(item.filename)
            if item.filename == "word/document.xml":
                b = b.replace(b"<w:t>x</w:t>", "<w:t>{{KEY}}</w:t>".encode())
                assert b"{{KEY}}" in b
            zout.writestr(item, b)
    _replace_textbox_placeholders(str(tmp2), {"KEY": "A&B <x>"})
    with zipfile.ZipFile(tmp2) as z:
        xml = z.read("word/document.xml")
    etree.fromstring(xml)
    assert "A&B <x>" in "".join(etree.fromstring(xml).itertext())
    assert re.search(rb"A&amp;B &lt;x&gt;", xml)

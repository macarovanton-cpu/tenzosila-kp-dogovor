"""Юниты walker'а: прозрачные обёртки, таблицы, textbox, секции (P0-01)."""

from __future__ import annotations

from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from tests.golden.dump_walker import DumpContext, walk_block

_W = nsdecls("w")


def _walk(body_xml: str) -> list[str]:
    """Прогнать walker по синтетическому w:body-фрагменту."""
    return walk_block(parse_xml(f"<w:body {_W}>{body_xml}</w:body>"), DumpContext())


# ── Прозрачные обёртки: текст не пропадает молча ─────────────────────────


def test_block_sdt_content_is_walked():
    """Block-level w:sdt (content control) разворачивается прозрачно."""
    lines = _walk(
        "<w:sdt><w:sdtPr/><w:sdtContent>"
        "<w:p><w:r><w:t>из контрола</w:t></w:r></w:p>"
        "</w:sdtContent></w:sdt>"
    )
    assert lines == ["P{}", "  R{} 'из контрола'"]


def test_inline_ins_and_sdt_transparent_and_merged():
    """w:ins (рецензия) и inline w:sdt прозрачны; раны сливаются со соседями."""
    lines = _walk(
        "<w:p>"
        "<w:ins w:id='1' w:author='x'><w:r><w:t>вставка</w:t></w:r></w:ins>"
        "<w:sdt><w:sdtContent><w:r><w:t> контрол</w:t></w:r></w:sdtContent></w:sdt>"
        "</w:p>"
    )
    assert lines == ["P{}", "  R{} 'вставка контрол'"]


def test_del_content_not_dumped():
    """w:del (удалённый текст рецензии) невидим в документе — не дампится."""
    lines = _walk(
        "<w:p><w:del w:id='2'><w:r><w:delText>удалено</w:delText></w:r></w:del>"
        "<w:r><w:t>осталось</w:t></w:r></w:p>"
    )
    assert lines == ["P{}", "  R{} 'осталось'"]


def test_sdt_wrapped_table_row():
    """Строка таблицы внутри w:sdt (repeating section) не пропадает."""
    lines = _walk(
        "<w:tbl><w:tblGrid><w:gridCol w:w='100'/></w:tblGrid>"
        "<w:sdt><w:sdtContent>"
        "<w:tr><w:tc><w:p><w:r><w:t>строка-в-sdt</w:t></w:r></w:p></w:tc></w:tr>"
        "</w:sdtContent></w:sdt>"
        "</w:tbl>"
    )
    assert lines == [
        "TBL{cols=1;grid=100}",
        "  TR{}",
        "    TC{}",
        "      P{}",
        "        R{} 'строка-в-sdt'",
    ]


def test_hyperlink_runs_transparent():
    lines = _walk(
        "<w:p><w:hyperlink r:id='rId5' "
        "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'>"
        "<w:r><w:t>ссылка</w:t></w:r></w:hyperlink></w:p>"
    )
    assert lines == ["P{}", "  R{} 'ссылка'"]


# ── Таблицы, textbox, секции ─────────────────────────────────────────────


def test_table_with_vmerge_and_nested_paragraphs():
    lines = _walk(
        "<w:tbl><w:tblGrid><w:gridCol w:w='100'/><w:gridCol w:w='200'/></w:tblGrid>"
        "<w:tr><w:tc><w:tcPr><w:vMerge w:val='restart'/></w:tcPr>"
        "<w:p><w:r><w:t>17</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>x</w:t></w:r></w:p></w:tc></w:tr>"
        "<w:tr><w:tc><w:tcPr><w:vMerge/></w:tcPr><w:p/></w:tc>"
        "<w:tc><w:p><w:r><w:t>y</w:t></w:r></w:p></w:tc></w:tr>"
        "</w:tbl>"
    )
    assert lines == [
        "TBL{cols=2;grid=100,200}",
        "  TR{}",
        "    TC{vmerge=restart}",
        "      P{}",
        "        R{} '17'",
        "    TC{}",
        "      P{}",
        "        R{} 'x'",
        "  TR{}",
        "    TC{vmerge=cont}",
        "      P{}",
        "    TC{}",
        "      P{}",
        "        R{} 'y'",
    ]


def test_textbox_in_pict_is_walked():
    """w:txbxContent внутри w:pict (VML) — python-docx API его не видит."""
    lines = _walk(
        "<w:p><w:r><w:pict xmlns:v='urn:schemas-microsoft-com:vml'>"
        "<v:shape><v:textbox><w:txbxContent>"
        "<w:p><w:r><w:t>Поставщик</w:t></w:r></w:p>"
        "</w:txbxContent></v:textbox></v:shape>"
        "</w:pict></w:r></w:p>"
    )
    assert lines == [
        "P{}",
        "  R{} [PICT]",
        "    TXBX",
        "      P{}",
        "        R{} 'Поставщик'",
    ]


def test_alternate_content_choice_only_no_duplication():
    """mc:AlternateContent: textbox дампится один раз (Choice), Fallback — дубль."""
    mc = "http://schemas.openxmlformats.org/markup-compatibility/2006"
    wps = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
    lines = _walk(
        f"<w:p><w:r><mc:AlternateContent xmlns:mc='{mc}'>"
        f"<mc:Choice Requires='wps'><w:drawing><wps:txbx xmlns:wps='{wps}'>"
        "<w:txbxContent><w:p><w:r><w:t>Поставщик</w:t></w:r></w:p></w:txbxContent>"
        "</wps:txbx></w:drawing></mc:Choice>"
        "<mc:Fallback><w:pict xmlns:v='urn:schemas-microsoft-com:vml'>"
        "<v:shape><v:textbox><w:txbxContent>"
        "<w:p><w:r><w:t>Поставщик</w:t></w:r></w:p>"
        "</w:txbxContent></v:textbox></v:shape></w:pict></mc:Fallback>"
        "</mc:AlternateContent></w:r></w:p>"
    )
    assert lines == [
        "P{}",
        "  R{} [DRAWING]",
        "    TXBX",
        "      P{}",
        "        R{} 'Поставщик'",
    ]


def test_sectpr_inside_ppr_emits_sect_line():
    """Разрыв секции посреди документа (sectPr в pPr) виден в дампе."""
    lines = _walk(
        "<w:p><w:pPr><w:sectPr><w:pgSz w:w='11906' w:h='16838'/></w:sectPr></w:pPr>"
        "<w:r><w:t>конец секции</w:t></w:r></w:p>"
    )
    assert lines == ["P{}", "  R{} 'конец секции'", "SECT{pgSz=11906x16838}"]

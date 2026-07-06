"""Юниты whitelist-сводок канонического дампа DOCX (P0-01)."""

from __future__ import annotations

from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from tests.golden.dump_props import (
    ppr_summary,
    rpr_summary,
    sectpr_summary,
    tbl_summary,
    tcpr_summary,
    trpr_summary,
)

_W = nsdecls("w")


def test_rpr_noise_ignored_whitelist_kept():
    """rsidRPr + lang + b -> ровно {b}: шум не попадает в сводку."""
    rpr = parse_xml(
        f'<w:rPr {_W} w:rsidRPr="00AB12CD">'
        '<w:lang w:val="ru-RU"/><w:noProof/><w:b/>'
        "</w:rPr>"
    )
    assert rpr_summary(rpr, {}) == "{b}"


def test_rpr_canonical_key_order():
    """Порядок ключей фиксирован whitelist'ом, а не порядком XML."""
    rpr = parse_xml(
        f'<w:rPr {_W}><w:b/><w:sz w:val="22"/>'
        '<w:rFonts w:ascii="Arial" w:hAnsi="Arial"/></w:rPr>'
    )
    assert rpr_summary(rpr, {}) == "{font=Arial;sz=11;b}"


def test_rpr_explicit_off_and_halfpoint():
    """Явное выключение тогла значимо (b=off); полупункты -> 10.5."""
    rpr = parse_xml(f'<w:rPr {_W}><w:b w:val="0"/><w:sz w:val="21"/></w:rPr>')
    assert rpr_summary(rpr, {}) == "{sz=10.5;b=off}"


def test_rpr_none_and_empty():
    """Нет rPr и пустой rPr — одинаково {} (провал в наследование)."""
    assert rpr_summary(None, {}) == "{}"
    assert rpr_summary(parse_xml(f"<w:rPr {_W}/>"), {}) == "{}"


def test_rpr_font_ascii_hansi_differ():
    rpr = parse_xml(f'<w:rPr {_W}><w:rFonts w:ascii="Arial" w:hAnsi="Times New Roman"/></w:rPr>')
    assert rpr_summary(rpr, {}) == "{font=Arial/Times New Roman}"


def test_ppr_style_jc_spacing_ind_pgbrk():
    """Сигнатура бага 4341a91: spacing line=360 + jc=both должны быть видны."""
    ppr = parse_xml(
        f'<w:pPr {_W}><w:pStyle w:val="ListParagraph"/><w:pageBreakBefore/>'
        '<w:spacing w:line="360" w:lineRule="auto" w:after="120"/>'
        '<w:ind w:left="0" w:hanging="360"/><w:jc w:val="both"/></w:pPr>'
    )
    summary = ppr_summary(ppr, {"ListParagraph": "Абзац списка"}, {})
    assert summary == (
        "{style='Абзац списка';jc=both;spacing=line:360/auto,after:120;"
        "ind=left:0,hanging:360;pgbrk}"
    )


def test_ppr_explicit_zero_spacing_kept():
    """Явный ноль значим: w:after='0' гасит spacing стиля и должен дампиться."""
    ppr = parse_xml(f'<w:pPr {_W}><w:spacing w:after="0"/></w:pPr>')
    assert ppr_summary(ppr, {}, {}) == "{spacing=after:0}"


def test_ppr_num_alias_by_first_use():
    """numId нормализуются в num1, num2... по порядку первого использования."""
    aliases: dict[str, str] = {}
    ppr_a = parse_xml(
        f'<w:pPr {_W}><w:numPr><w:ilvl w:val="0"/><w:numId w:val="7"/></w:numPr></w:pPr>'
    )
    ppr_b = parse_xml(
        f'<w:pPr {_W}><w:numPr><w:ilvl w:val="1"/><w:numId w:val="3"/></w:numPr></w:pPr>'
    )
    assert ppr_summary(ppr_a, {}, aliases) == "{num=num1.0}"
    assert ppr_summary(ppr_b, {}, aliases) == "{num=num2.1}"
    assert ppr_summary(ppr_a, {}, aliases) == "{num=num1.0}"  # повтор стабилен


def test_tcpr_vmerge_restart_and_continue():
    """Формат spec_vmerge.py: restart с val, continue — пустой элемент."""
    tc_restart = parse_xml(
        f'<w:tc {_W}><w:tcPr><w:vMerge w:val="restart"/></w:tcPr></w:tc>'
    )
    tc_cont = parse_xml(f"<w:tc {_W}><w:tcPr><w:vMerge/></w:tcPr></w:tc>")
    tc_plain = parse_xml(f"<w:tc {_W}><w:tcPr/></w:tc>")
    assert tcpr_summary(tc_restart) == "{vmerge=restart}"
    assert tcpr_summary(tc_cont) == "{vmerge=cont}"
    assert tcpr_summary(tc_plain) == "{}"


def test_tcpr_gridspan():
    tc = parse_xml(f'<w:tc {_W}><w:tcPr><w:gridSpan w:val="2"/></w:tcPr></w:tc>')
    assert tcpr_summary(tc) == "{span=2}"


def test_trpr_height():
    """Сигнатура бага раздутых строк appendix_1 (trHeight)."""
    tr = parse_xml(
        f'<w:tr {_W}><w:trPr><w:trHeight w:val="2289" w:hRule="atLeast"/></w:trPr></w:tr>'
    )
    assert trpr_summary(tr) == "{h=atLeast:2289}"
    assert trpr_summary(parse_xml(f"<w:tr {_W}/>")) == "{}"


def test_tbl_grid():
    tbl = parse_xml(
        f'<w:tbl {_W}><w:tblGrid><w:gridCol w:w="4927"/><w:gridCol w:w="2268"/>'
        "</w:tblGrid></w:tbl>"
    )
    assert tbl_summary(tbl) == "{cols=2;grid=4927,2268}"


def test_sectpr_summary():
    sect = parse_xml(
        f'<w:sectPr {_W}><w:headerReference w:type="default" r:id="rId8" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="794" w:right="851" w:bottom="794" w:left="1134" '
        'w:header="709" w:footer="709" w:gutter="0"/></w:sectPr>'
    )
    assert sectpr_summary(sect) == "{pgSz=11906x16838;pgMar=794,851,794,1134;hdr=default}"

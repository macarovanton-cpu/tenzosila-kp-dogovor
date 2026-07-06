"""Тесты канонического дампа DOCX (P0-01): сводки, склейка ранов, стабильность."""

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
from tests.golden.dump_walker import DumpContext, walk_block

_W = nsdecls("w")


def _walk(body_xml: str) -> list[str]:
    """Прогнать walker по синтетическому w:body-фрагменту."""
    return walk_block(parse_xml(f"<w:body {_W}>{body_xml}</w:body>"), DumpContext())


# ── Сводки rPr ───────────────────────────────────────────────────────────


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


# ── Сводки pPr ───────────────────────────────────────────────────────────


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


# ── Таблицы ──────────────────────────────────────────────────────────────


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


# ── Walker: склейка ранов ────────────────────────────────────────────────


def test_runs_split_by_noise_are_merged():
    """Три рана, разбитые proofErr/rsid, одна значимая сводка -> одна строка R."""
    lines = _walk(
        '<w:p w:rsidR="00AA00AA">'
        '<w:r w:rsidRPr="00BB00BB"><w:t xml:space="preserve">Кавычки </w:t></w:r>'
        '<w:proofErr w:type="spellStart"/>'
        '<w:r><w:rPr><w:lang w:val="ru-RU"/><w:noProof/></w:rPr><w:t>«ёлочки»</w:t></w:r>'
        '<w:proofErr w:type="spellEnd"/>'
        "<w:r><w:t> и О.А. Фамилия</w:t></w:r>"
        "</w:p>"
    )
    assert lines == ["P{}", "  R{} 'Кавычки «ёлочки» и О.А. Фамилия'"]


def test_runs_with_different_summary_not_merged():
    """Средний ран bold -> три строки R; дифф локален строке с изменением."""
    lines = _walk(
        "<w:p>"
        '<w:r><w:t xml:space="preserve">до </w:t></w:r>'
        "<w:r><w:rPr><w:b/></w:rPr><w:t>жирный</w:t></w:r>"
        '<w:r><w:t xml:space="preserve"> после</w:t></w:r>'
        "</w:p>"
    )
    assert lines == ["P{}", "  R{} 'до '", "  R{b} 'жирный'", "  R{} ' после'"]


def test_tab_and_br_inside_run_text():
    """w:tab/w:br -> \\t/\\n в repr-тексте, склейку не рвут."""
    lines = _walk(
        "<w:p><w:r><w:t>a</w:t><w:tab/><w:t>b</w:t><w:br/><w:t>c</w:t></w:r></w:p>"
    )
    assert lines == ["P{}", "  R{} 'a\\tb\\nc'"]


def test_page_break_is_separate_line():
    lines = _walk(
        '<w:p><w:r><w:t>a</w:t><w:br w:type="page"/><w:t>b</w:t></w:r></w:p>'
    )
    assert lines == ["P{}", "  R{} 'a'", "  [PAGEBREAK]", "  R{} 'b'"]


def test_field_page_dumped_with_instr_and_cached():
    """Поле PAGE: instrText дампится, fldChar-границы — нет."""
    lines = _walk(
        "<w:p>"
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        '<w:r><w:instrText xml:space="preserve"> PAGE \\* MERGEFORMAT </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        "<w:r><w:t>3</w:t></w:r>"
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        "</w:p>"
    )
    assert lines == ["P{}", "  R{} [FIELD 'PAGE \\\\* MERGEFORMAT'] cached='3'"]


# ── Walker: таблицы, textbox, секции ─────────────────────────────────────


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


def test_hyperlink_runs_transparent():
    lines = _walk(
        "<w:p><w:hyperlink r:id='rId5' "
        "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'>"
        "<w:r><w:t>ссылка</w:t></w:r></w:hyperlink></w:p>"
    )
    assert lines == ["P{}", "  R{} 'ссылка'"]

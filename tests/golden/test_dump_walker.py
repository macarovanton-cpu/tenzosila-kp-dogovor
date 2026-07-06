"""Юниты walker'а канонического дампа DOCX: склейка ранов и поля (P0-01)."""

from __future__ import annotations

from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from tests.golden.dump_walker import DumpContext, walk_block

_W = nsdecls("w")


def _walk(body_xml: str) -> list[str]:
    """Прогнать walker по синтетическому w:body-фрагменту."""
    return walk_block(parse_xml(f"<w:body {_W}>{body_xml}</w:body>"), DumpContext())


# ── Склейка ранов ────────────────────────────────────────────────────────


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


def test_tab_br_and_nobreak_hyphen_inside_run_text():
    """w:tab/w:br -> \\t/\\n; w:noBreakHyphen -> U+2011 — не теряется молча.

    U+2011 печатаемый, поэтому repr оставляет его литералом (не экранирует)."""
    lines = _walk(
        "<w:p><w:r><w:t>a</w:t><w:tab/><w:t>b</w:t><w:br/>"
        "<w:t>8</w:t><w:noBreakHyphen/><w:t>800</w:t></w:r></w:p>"
    )
    assert lines == ["P{}", "  R{} 'a\\tb\\n8‑800'"]


def test_page_break_is_separate_line():
    lines = _walk(
        '<w:p><w:r><w:t>a</w:t><w:br w:type="page"/><w:t>b</w:t></w:r></w:p>'
    )
    assert lines == ["P{}", "  R{} 'a'", "  [PAGEBREAK]", "  R{} 'b'"]


# ── Поля ─────────────────────────────────────────────────────────────────


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


def test_field_tab_stays_inside_cached():
    """w:tab между separate и end уходит в кэш поля, а не в соседнюю строку R."""
    lines = _walk(
        "<w:p>"
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        "<w:r><w:instrText>PAGE</w:instrText></w:r>"
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        "<w:r><w:t>3</w:t><w:tab/><w:t>4</w:t></w:r>"
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        "</w:p>"
    )
    assert lines == ["P{}", "  R{} [FIELD 'PAGE'] cached='3\\t4'"]


def test_field_spanning_paragraphs_emits_instr():
    """Поле, не закрытое в своём параграфе (TOC), доэмитивается — instr не теряется."""
    lines = _walk(
        "<w:p>"
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" </w:instrText></w:r>'
        "</w:p>"
        "<w:p><w:r><w:t>Раздел 1</w:t></w:r></w:p>"
    )
    assert lines == [
        "P{}",
        "  R{} [FIELD 'TOC \\\\o \"1-3\"'] cached=''",
        "P{}",
        "  R{} 'Раздел 1'",
    ]


def test_fld_simple():
    """w:fldSimple: инструкция из атрибута + кэш из вложенных ранов."""
    lines = _walk(
        '<w:p><w:fldSimple w:instr=" PAGE "><w:r><w:t>5</w:t></w:r></w:fldSimple></w:p>'
    )
    assert lines == ["P{}", "  R{} [FIELD 'PAGE'] cached='5'"]

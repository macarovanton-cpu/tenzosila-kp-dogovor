"""Whitelist-сводки свойств OOXML для канонического дампа DOCX (P0-01).

Чистые функции lxml-Element -> str вида "{key=val;key2}". Только ЯВНЫЕ
(direct) свойства из whitelist в каноническом порядке ключей; шум (rsid*,
w:lang, w:proofErr и т.д.) не попадает в сводку по построению.
Спецификация формата — в докстринге tests/golden/dump_docx.py.
"""

from __future__ import annotations

from typing import Callable

from lxml import etree

from docx.oxml.ns import qn

_FALSY = {"0", "false", "off", "none"}

# канонический порядок типов ссылок колонтитулов (общий с dump_docx)
HF_TYPES = ("default", "first", "even")


def _fmt(parts: list[str]) -> str:
    """Собрать сводку: пустой список -> "{}" (значимо: нет явных свойств)."""
    return "{" + ";".join(parts) + "}"


def _append_val(parts: list[str], el: etree._Element, tag: str, name: str,
                fmt: Callable[[str], str] | None = None) -> None:
    """Добавить "name=val" по w:val прямого ребёнка tag (нет/пусто — пропуск)."""
    child = el.find(qn(tag))
    if child is None:
        return
    val = child.get(qn("w:val"))
    if not val:
        return
    parts.append(f"{name}={fmt(val) if fmt else val}")


def _add_toggle(parts: list[str], el: etree._Element, tag: str, name: str) -> None:
    """Тогл OOXML: явное вкл -> "name", явное выкл -> "name=off" (гасит стиль)."""
    child = el.find(qn(tag))
    if child is None:
        return
    val = child.get(qn("w:val"))
    off = val is not None and val.lower() in _FALSY
    parts.append(f"{name}=off" if off else name)


def _sz_pt(half_points: str) -> str:
    """Полупункты OOXML -> пункты: 22 -> "11", 21 -> "10.5"."""
    half = int(half_points)
    return str(half // 2) if half % 2 == 0 else f"{half / 2:.1f}"


def rpr_summary(rpr: etree._Element | None, style_names: dict[str, str]) -> str:
    """Сводка rPr рана. Порядок: style,font,sz,b,i,u,strike,color,vertAlign,highlight."""
    parts: list[str] = []
    if rpr is None:
        return _fmt(parts)
    _append_val(parts, rpr, "w:rStyle", "style", fmt=lambda v: repr(style_names.get(v, v)))
    r_fonts = rpr.find(qn("w:rFonts"))
    if r_fonts is not None:
        ascii_f = r_fonts.get(qn("w:ascii"))
        hansi_f = r_fonts.get(qn("w:hAnsi"))
        if ascii_f and hansi_f and ascii_f != hansi_f:
            parts.append(f"font={ascii_f}/{hansi_f}")
        elif ascii_f or hansi_f:
            parts.append(f"font={ascii_f or hansi_f}")
    _append_val(parts, rpr, "w:sz", "sz", fmt=_sz_pt)
    _add_toggle(parts, rpr, "w:b", "b")
    _add_toggle(parts, rpr, "w:i", "i")
    u = rpr.find(qn("w:u"))
    if u is not None:
        parts.append(f"u={u.get(qn('w:val')) or 'single'}")
    _add_toggle(parts, rpr, "w:strike", "strike")
    _append_val(parts, rpr, "w:color", "color", fmt=str.upper)
    _append_val(parts, rpr, "w:vertAlign", "vertAlign")
    _append_val(parts, rpr, "w:highlight", "highlight")
    return _fmt(parts)


def _num_alias(num_id: str, num_aliases: dict[str, str]) -> str:
    """numId -> стабильный алиас numN по порядку первого использования."""
    if num_id not in num_aliases:
        num_aliases[num_id] = f"num{len(num_aliases) + 1}"
    return num_aliases[num_id]


def _attr_pairs(el: etree._Element, names: tuple[tuple[str, tuple[str, ...]], ...]) -> list[str]:
    """Пары "name:val" по явным атрибутам (первый существующий из синонимов)."""
    out: list[str] = []
    for name, attrs in names:
        for attr in attrs:
            val = el.get(qn(f"w:{attr}"))
            if val is not None:
                out.append(f"{name}:{val}")
                break
    return out


def ppr_summary(
    ppr: etree._Element | None,
    style_names: dict[str, str],
    num_aliases: dict[str, str],
) -> str:
    """Сводка pPr параграфа. Порядок: style,jc,spacing,ind,num,pgbrk."""
    parts: list[str] = []
    if ppr is None:
        return _fmt(parts)
    _append_val(parts, ppr, "w:pStyle", "style", fmt=lambda v: repr(style_names.get(v, v)))
    _append_val(parts, ppr, "w:jc", "jc")
    spacing = ppr.find(qn("w:spacing"))
    if spacing is not None:
        sp: list[str] = []
        line = spacing.get(qn("w:line"))
        if line is not None:
            sp.append(f"line:{line}/{spacing.get(qn('w:lineRule')) or 'auto'}")
        sp += _attr_pairs(spacing, (("before", ("before",)), ("after", ("after",))))
        if sp:
            parts.append("spacing=" + ",".join(sp))
    ind = ppr.find(qn("w:ind"))
    if ind is not None:
        # start/end — новые имена left/right в OOXML; нормализуем к left/right
        ip = _attr_pairs(ind, (("left", ("left", "start")), ("right", ("right", "end")),
                               ("firstLine", ("firstLine",)), ("hanging", ("hanging",))))
        if ip:
            parts.append("ind=" + ",".join(ip))
    num_pr = ppr.find(qn("w:numPr"))
    if num_pr is not None:
        num_id_el = num_pr.find(qn("w:numId"))
        ilvl_el = num_pr.find(qn("w:ilvl"))
        if num_id_el is not None and num_id_el.get(qn("w:val")):
            alias = _num_alias(num_id_el.get(qn("w:val")), num_aliases)
            ilvl = ilvl_el.get(qn("w:val")) if ilvl_el is not None else "0"
            parts.append(f"num={alias}.{ilvl or '0'}")
    pgbrk = ppr.find(qn("w:pageBreakBefore"))
    if pgbrk is not None:
        val = pgbrk.get(qn("w:val"))
        if val is None or val.lower() not in _FALSY:
            parts.append("pgbrk")
    return _fmt(parts)


def tcpr_summary(tc: etree._Element) -> str:
    """Сводка ячейки w:tc: vmerge (restart/cont) + span (gridSpan > 1)."""
    parts: list[str] = []
    tc_pr = tc.find(qn("w:tcPr"))
    if tc_pr is not None:
        vmerge = tc_pr.find(qn("w:vMerge"))
        if vmerge is not None:
            val = vmerge.get(qn("w:val"))
            parts.append("vmerge=restart" if val == "restart" else "vmerge=cont")
        span = tc_pr.find(qn("w:gridSpan"))
        if span is not None and int(span.get(qn("w:val")) or 1) > 1:
            parts.append(f"span={span.get(qn('w:val'))}")
    return _fmt(parts)


def trpr_summary(tr: etree._Element) -> str:
    """Сводка строки w:tr: только trHeight (h=<hRule>:<val>)."""
    parts: list[str] = []
    tr_pr = tr.find(qn("w:trPr"))
    if tr_pr is not None:
        height = tr_pr.find(qn("w:trHeight"))
        if height is not None:
            rule = height.get(qn("w:hRule")) or "auto"
            parts.append(f"h={rule}:{height.get(qn('w:val')) or '0'}")
    return _fmt(parts)


def tbl_summary(tbl: etree._Element) -> str:
    """Сводка таблицы: число колонок + ширины tblGrid (twips)."""
    grid = tbl.find(qn("w:tblGrid"))
    cols = grid.findall(qn("w:gridCol")) if grid is not None else []
    widths = ",".join(c.get(qn("w:w")) or "?" for c in cols)
    return _fmt([f"cols={len(cols)}", f"grid={widths}"] if cols else ["cols=0"])


def sectpr_summary(sect_pr: etree._Element) -> str:
    """Сводка секции: pgSz, pgMar, типы ссылок hdr/ftr (без rId), titlePg."""
    parts: list[str] = []
    pg_sz = sect_pr.find(qn("w:pgSz"))
    if pg_sz is not None:
        parts.append(f"pgSz={pg_sz.get(qn('w:w'))}x{pg_sz.get(qn('w:h'))}")
    pg_mar = sect_pr.find(qn("w:pgMar"))
    if pg_mar is not None:
        mar = ",".join(pg_mar.get(qn(f"w:{a}")) or "?" for a in ("top", "right", "bottom", "left"))
        parts.append(f"pgMar={mar}")
    for ref_tag, name in (("w:headerReference", "hdr"), ("w:footerReference", "ftr")):
        types = {ref.get(qn("w:type")) for ref in sect_pr.findall(qn(ref_tag))}
        ordered = [t for t in HF_TYPES if t in types]
        if ordered:
            parts.append(f"{name}={','.join(ordered)}")
    if sect_pr.find(qn("w:titlePg")) is not None:
        parts.append("titlePg")
    return _fmt(parts)

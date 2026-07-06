"""Whitelist-сводки свойств OOXML для канонического дампа DOCX (P0-01).

Чистые функции lxml-Element -> str вида "{key=val;key2}". Дампятся только
ЯВНЫЕ (direct) свойства из фиксированного whitelist в каноническом порядке
ключей. Шум (rsid*, w:lang, w:proofErr, szCs/bCs/iCs и т.д.) не попадает
в сводку по построению: собираем по белому списку, а не фильтруем чёрный.

Полная спецификация формата дампа — в докстринге tests/golden/dump_docx.py.
"""

from __future__ import annotations

from lxml import etree

from docx.oxml.ns import qn

_FALSY = {"0", "false", "off", "none"}


def _fmt(parts: list[str]) -> str:
    """Собрать сводку: пустой список -> "{}" (значимо: нет явных свойств)."""
    return "{" + ";".join(parts) + "}"


def _bool_prop(el: etree._Element | None, tag: str) -> bool | None:
    """Тогл-свойство OOXML: None — отсутствует, True — вкл, False — явно выкл."""
    if el is None:
        return None
    child = el.find(qn(tag))
    if child is None:
        return None
    val = child.get(qn("w:val"))
    return not (val is not None and val.lower() in _FALSY)


def _add_toggle(parts: list[str], el: etree._Element | None, tag: str, name: str) -> None:
    """Явное вкл -> "name", явное выкл -> "name=off" (значимо: гасит стиль)."""
    state = _bool_prop(el, tag)
    if state is True:
        parts.append(name)
    elif state is False:
        parts.append(f"{name}=off")


def _sz_pt(half_points: str) -> str:
    """Полупункты OOXML -> пункты: 22 -> "11", 21 -> "10.5"."""
    half = int(half_points)
    return str(half // 2) if half % 2 == 0 else f"{half / 2:.1f}"


def rpr_summary(rpr: etree._Element | None, style_names: dict[str, str]) -> str:
    """Сводка rPr рана. Порядок: style,font,sz,b,i,u,strike,color,vertAlign,highlight."""
    parts: list[str] = []
    if rpr is None:
        return _fmt(parts)
    r_style = rpr.find(qn("w:rStyle"))
    if r_style is not None:
        sid = r_style.get(qn("w:val")) or ""
        parts.append(f"style={style_names.get(sid, sid)!r}")
    r_fonts = rpr.find(qn("w:rFonts"))
    if r_fonts is not None:
        ascii_f = r_fonts.get(qn("w:ascii"))
        hansi_f = r_fonts.get(qn("w:hAnsi"))
        if ascii_f and hansi_f and ascii_f != hansi_f:
            parts.append(f"font={ascii_f}/{hansi_f}")
        elif ascii_f or hansi_f:
            parts.append(f"font={ascii_f or hansi_f}")
    sz = rpr.find(qn("w:sz"))
    if sz is not None and sz.get(qn("w:val")):
        parts.append(f"sz={_sz_pt(sz.get(qn('w:val')))}")
    _add_toggle(parts, rpr, "w:b", "b")
    _add_toggle(parts, rpr, "w:i", "i")
    u = rpr.find(qn("w:u"))
    if u is not None:
        parts.append(f"u={u.get(qn('w:val')) or 'single'}")
    _add_toggle(parts, rpr, "w:strike", "strike")
    color = rpr.find(qn("w:color"))
    if color is not None and color.get(qn("w:val")):
        parts.append(f"color={color.get(qn('w:val')).upper()}")
    vert = rpr.find(qn("w:vertAlign"))
    if vert is not None and vert.get(qn("w:val")):
        parts.append(f"vertAlign={vert.get(qn('w:val'))}")
    hl = rpr.find(qn("w:highlight"))
    if hl is not None and hl.get(qn("w:val")):
        parts.append(f"highlight={hl.get(qn('w:val'))}")
    return _fmt(parts)


def _num_alias(num_id: str, num_aliases: dict[str, str]) -> str:
    """numId -> стабильный алиас numN по порядку первого использования."""
    if num_id not in num_aliases:
        num_aliases[num_id] = f"num{len(num_aliases) + 1}"
    return num_aliases[num_id]


def ppr_summary(
    ppr: etree._Element | None,
    style_names: dict[str, str],
    num_aliases: dict[str, str],
) -> str:
    """Сводка pPr параграфа. Порядок: style,jc,spacing,ind,num,pgbrk."""
    parts: list[str] = []
    if ppr is None:
        return _fmt(parts)
    p_style = ppr.find(qn("w:pStyle"))
    if p_style is not None:
        sid = p_style.get(qn("w:val")) or ""
        parts.append(f"style={style_names.get(sid, sid)!r}")
    jc = ppr.find(qn("w:jc"))
    if jc is not None and jc.get(qn("w:val")):
        parts.append(f"jc={jc.get(qn('w:val'))}")
    spacing = ppr.find(qn("w:spacing"))
    if spacing is not None:
        sp: list[str] = []
        line = spacing.get(qn("w:line"))
        if line:
            sp.append(f"line:{line}/{spacing.get(qn('w:lineRule')) or 'auto'}")
        for attr in ("before", "after"):
            val = spacing.get(qn(f"w:{attr}"))
            if val:
                sp.append(f"{attr}:{val}")
        if sp:
            parts.append("spacing=" + ",".join(sp))
    ind = ppr.find(qn("w:ind"))
    if ind is not None:
        # start/end — новые имена left/right в OOXML; нормализуем к left/right
        pairs = (("left", ("left", "start")), ("right", ("right", "end")),
                 ("firstLine", ("firstLine",)), ("hanging", ("hanging",)))
        ip: list[str] = []
        for name, attrs in pairs:
            for attr in attrs:
                val = ind.get(qn(f"w:{attr}"))
                if val is not None:
                    ip.append(f"{name}:{val}")
                    break
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
    if _bool_prop(ppr, "w:pageBreakBefore") is True:
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
        ordered = [t for t in ("default", "first", "even") if t in types]
        if ordered:
            parts.append(f"{name}={','.join(ordered)}")
    if sect_pr.find(qn("w:titlePg")) is not None:
        parts.append("titlePg")
    return _fmt(parts)

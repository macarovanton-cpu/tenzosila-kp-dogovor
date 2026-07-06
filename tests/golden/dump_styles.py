"""Шапка канонического дампа DOCX: [DEFAULTS] / [STYLE] / [NUM] / [MEDIA] (P0-01).

Делает дамп самодостаточным при том, что строки P/R несут только ЯВНЫЕ
свойства: провал форматирования в наследование виден как R{} в теле, а
то, ВО ЧТО он проваливается, — здесь ([DEFAULTS] и rPr/pPr стилей).

Стили дампятся по ИМЕНИ (w:name), не по styleId: docxcompose при склейке
переименовывает конфликтующие styleId, имена стабильны. Дампятся только
стили, реально использованные в документе (собирает walker). numId
нормализованы в алиасы num1, num2... по порядку первого использования.
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from lxml import etree

from docx.oxml.ns import qn

from tests.golden.dump_props import ppr_summary, rpr_summary


def build_style_names(styles_el: etree._Element | None) -> dict[str, str]:
    """Карта styleId -> имя стиля (w:name) из styles.xml."""
    names: dict[str, str] = {}
    if styles_el is None:
        return names
    for style in styles_el.findall(qn("w:style")):
        sid = style.get(qn("w:styleId"))
        name_el = style.find(qn("w:name"))
        if sid and name_el is not None and name_el.get(qn("w:val")):
            names[sid] = name_el.get(qn("w:val"))
    return names


def defaults_line(styles_el: etree._Element | None) -> str:
    """[DEFAULTS] — сводка docDefaults (куда проваливаются раны без явного rPr)."""
    rpr = ppr = None
    if styles_el is not None:
        defaults = styles_el.find(qn("w:docDefaults"))
        if defaults is not None:
            rpr_default = defaults.find(qn("w:rPrDefault"))
            if rpr_default is not None:
                rpr = rpr_default.find(qn("w:rPr"))
            ppr_default = defaults.find(qn("w:pPrDefault"))
            if ppr_default is not None:
                ppr = ppr_default.find(qn("w:pPr"))
    return f"[DEFAULTS] rPr{rpr_summary(rpr, {})} pPr{ppr_summary(ppr, {}, {})}"


def used_style_lines(
    styles_el: etree._Element | None,
    used_ids: set[str],
    style_names: dict[str, str],
    num_aliases: dict[str, str],
) -> list[str]:
    """[STYLE] — только использованные стили, отсортированы по имени."""
    lines: list[str] = []
    if styles_el is None or not used_ids:
        return lines
    for style in styles_el.findall(qn("w:style")):
        sid = style.get(qn("w:styleId"))
        if sid not in used_ids:
            continue
        name = style_names.get(sid, sid)
        based_el = style.find(qn("w:basedOn"))
        based = ""
        if based_el is not None and based_el.get(qn("w:val")):
            based_id = based_el.get(qn("w:val"))
            based = f" based={style_names.get(based_id, based_id)!r}"
        ppr = style.find(qn("w:pPr"))
        rpr = style.find(qn("w:rPr"))
        lines.append(
            f"[STYLE] {name!r}{based}"
            f" pPr{ppr_summary(ppr, style_names, num_aliases)}"
            f" rPr{rpr_summary(rpr, style_names)}"
        )
    return sorted(lines)


def num_lines_from_zip(docx_path: Path, num_aliases: dict[str, str]) -> list[str]:
    """[NUM] — семантика использованных нумераций (numFmt + lvlText по уровням).

    Читается из word/numbering.xml напрямую (zip): сырые numId в дамп не
    попадают — только алиасы и семантика, стабильные к переименованию
    docxcompose'ом.
    """
    if not num_aliases:
        return []
    try:
        with zipfile.ZipFile(docx_path) as zf:
            numbering = etree.fromstring(zf.read("word/numbering.xml"))
    except KeyError:
        return [f"[NUM] {alias} = ?" for alias in num_aliases.values()]
    abstract_by_id: dict[str, etree._Element] = {
        a.get(qn("w:abstractNumId")): a for a in numbering.findall(qn("w:abstractNum"))
    }
    num_to_abstract: dict[str, str] = {}
    for num in numbering.findall(qn("w:num")):
        ref = num.find(qn("w:abstractNumId"))
        if ref is not None:
            num_to_abstract[num.get(qn("w:numId"))] = ref.get(qn("w:val"))
    lines: list[str] = []
    for num_id, alias in num_aliases.items():  # insertion order = порядок использования
        abstract = abstract_by_id.get(num_to_abstract.get(num_id, ""))
        if abstract is None:
            lines.append(f"[NUM] {alias} = ?")
            continue
        levels: list[str] = []
        for lvl in abstract.findall(qn("w:lvl")):
            fmt_el = lvl.find(qn("w:numFmt"))
            text_el = lvl.find(qn("w:lvlText"))
            fmt = fmt_el.get(qn("w:val")) if fmt_el is not None else "?"
            text = text_el.get(qn("w:val")) if text_el is not None else ""
            levels.append(f"L{lvl.get(qn('w:ilvl'))}:{fmt}{text!r}")
        lines.append(f"[NUM] {alias} = " + " ".join(levels))
    return lines


def media_lines(docx_path: Path) -> list[str]:
    """[MEDIA] — sha1-хэши word/media/* (ловит подмену логотипа/картинок)."""
    lines: list[str] = []
    with zipfile.ZipFile(docx_path) as zf:
        for name in sorted(n for n in zf.namelist() if n.startswith("word/media/")):
            digest = hashlib.sha1(zf.read(name)).hexdigest()[:12]
            lines.append(f"[MEDIA] {name} sha1={digest}")
    return lines

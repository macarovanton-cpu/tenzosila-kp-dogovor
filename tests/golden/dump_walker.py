"""Рекурсивный обход block-уровня OOXML для канонического дампа DOCX (P0-01).

Единый walker для body / header / footer / w:txbxContent (textbox).
Обход строго в document order (python-docx paragraphs/tables теряют
взаимный порядок — поэтому прямая итерация XML-детей).

Обёртки-контейнеры (w:sdt content control, w:ins tracked-insert,
w:smartTag) разворачиваются прозрачно — их текст не должен молча
пропадать из дампа. w:del (удалённый текст рецензии) невидим в
итоговом документе и не дампится.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from lxml import etree

from docx.oxml.ns import qn

from tests.golden.dump_props import ppr_summary, sectpr_summary, tbl_summary, tcpr_summary, trpr_summary
from tests.golden.dump_runs import RunWalker

_IND = "  "


@dataclass
class DumpContext:
    """Сквозное состояние дампа: имена стилей, num-алиасы, использованные стили."""

    style_names: dict[str, str] = field(default_factory=dict)
    num_aliases: dict[str, str] = field(default_factory=dict)
    used_style_ids: set[str] = field(default_factory=set)

    def register_style(self, pr: etree._Element | None, tag: str) -> None:
        """Запомнить styleId (pStyle/rStyle) для секции [STYLE] шапки дампа."""
        if pr is None:
            return
        el = pr.find(qn(tag))
        if el is not None and el.get(qn("w:val")):
            self.used_style_ids.add(el.get(qn("w:val")))


def _sdt_content(el: etree._Element) -> etree._Element | None:
    return el.find(qn("w:sdtContent"))


def walk_block(parent: etree._Element, ctx: DumpContext, level: int = 0) -> list[str]:
    """Обойти block-level детей (w:p / w:tbl / w:sectPr / w:sdt) в document order."""
    lines: list[str] = []
    for child in parent:
        tag = child.tag
        if tag == qn("w:p"):
            lines.extend(_walk_paragraph(child, ctx, level))
        elif tag == qn("w:tbl"):
            lines.extend(_walk_table(child, ctx, level))
        elif tag == qn("w:sectPr"):
            lines.append(_IND * level + "SECT" + sectpr_summary(child))
        elif tag == qn("w:sdt"):
            content = _sdt_content(child)
            if content is not None:
                lines.extend(walk_block(content, ctx, level))
    return lines


def _walk_inline(children: etree._Element, runs: RunWalker) -> None:
    """Inline-дети параграфа: раны + прозрачные обёртки (hyperlink/sdt/ins/smartTag)."""
    for child in children:
        tag = child.tag
        if tag == qn("w:r"):
            runs.add_run(child)
        elif tag == qn("w:fldSimple"):
            runs.add_fld_simple(child)
        elif tag in (qn("w:hyperlink"), qn("w:ins"), qn("w:smartTag")):
            _walk_inline(child, runs)  # прозрачно; rId гиперссылки не дампим
        elif tag == qn("w:sdt"):
            content = _sdt_content(child)
            if content is not None:
                _walk_inline(content, runs)


def _walk_paragraph(p_el: etree._Element, ctx: DumpContext, level: int) -> list[str]:
    ppr = p_el.find(qn("w:pPr"))
    ctx.register_style(ppr, "w:pStyle")
    lines = [_IND * level + "P" + ppr_summary(ppr, ctx.style_names, ctx.num_aliases)]
    runs = RunWalker(ctx, level + 1, walk_block)
    _walk_inline(p_el, runs)
    runs.close()
    lines.extend(runs.lines)
    if ppr is not None:
        sect_pr = ppr.find(qn("w:sectPr"))
        if sect_pr is not None:
            # разрыв секции посреди документа живёт в pPr параграфа
            lines.append(_IND * level + "SECT" + sectpr_summary(sect_pr))
    return lines


def _iter_rows(tbl: etree._Element) -> Iterator[etree._Element]:
    """Строки таблицы, включая обёрнутые в w:sdt (repeating section)."""
    for child in tbl:
        if child.tag == qn("w:tr"):
            yield child
        elif child.tag == qn("w:sdt"):
            content = _sdt_content(child)
            if content is not None:
                yield from (c for c in content if c.tag == qn("w:tr"))


def _walk_table(tbl: etree._Element, ctx: DumpContext, level: int) -> list[str]:
    lines = [_IND * level + "TBL" + tbl_summary(tbl)]
    for tr in _iter_rows(tbl):
        lines.append(_IND * (level + 1) + "TR" + trpr_summary(tr))
        for tc in tr.findall(qn("w:tc")):
            lines.append(_IND * (level + 2) + "TC" + tcpr_summary(tc))
            # вложенные таблицы поддержаны рекурсией walk_block
            lines.extend(walk_block(tc, ctx, level + 3))
    return lines

"""Пост-процессинг таблицы спецификации после docxtpl.render().

В рендере docxtpl кладёт в третью ячейку строки текстовый маркер вида
``⟦MERGE:restart:24⟧`` или ``⟦MERGE:continue⟧`` (закодированный в
kp_generator.encode_term_days_marker). Здесь мы:

1. Находим таблицу спецификации (заголовок «Наименование»).
2. Для каждой content-row смотрим текст 3-й ячейки.
3. Если это маркер — снимаем его, на его место ставим финальный текст
   («24» либо ""), и в ``<w:tcPr>`` добавляем ``<w:vMerge w:val="restart"/>``
   или ``<w:vMerge/>`` (continue).

Маркеры выбраны так, чтобы заведомо не пересекаться с обычными значениями
сроков (только цифры/пустота).
"""
from __future__ import annotations

import re

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Маркеры, которые kp_generator кодирует в ячейку «term_days»:
#   ⟦MERGE:restart:24⟧
#   ⟦MERGE:continue⟧
_RESTART_RE = re.compile(r"^⟦MERGE:restart:(.*)⟧$")
_CONTINUE_TOKEN = "⟦MERGE:continue⟧"


def encode_term_days_marker(value: str, merge: str | None) -> str:
    """Закодировать значение и merge-стратегию в одну строку.

    merge="restart" → ⟦MERGE:restart:{value}⟧
    merge="continue" → ⟦MERGE:continue⟧
    merge=None       → value as-is
    """
    if merge == "restart":
        return f"⟦MERGE:restart:{value}⟧"
    if merge == "continue":
        return _CONTINUE_TOKEN
    return value


def _tc_text(tc) -> str:
    """Прочитать весь текст из ``<w:tc>`` (все runs всех параграфов)."""
    return "".join(t.text or "" for t in tc.iter(qn("w:t")))


def _set_tc_text(tc, text: str) -> None:
    """Заменить весь текст в ``<w:tc>``: оставить первый <w:r> с его rPr,
    переписать его <w:t>, удалить остальные runs.
    """
    runs = tc.findall(f".//{qn('w:r')}")
    if not runs:
        return
    first = runs[0]
    # Удалить все <w:t> в первом run-е, добавить один новый.
    for t_el in first.findall(qn("w:t")):
        first.remove(t_el)
    new_t = OxmlElement("w:t")
    new_t.text = text
    new_t.set(
        "{http://www.w3.org/XML/1998/namespace}space", "preserve"
    )
    first.append(new_t)
    # Удалить остальные runs (их форматирование нам не нужно).
    for r in runs[1:]:
        r.getparent().remove(r)


def _set_tc_vmerge(tc, val: str | None) -> None:
    """Добавить ``<w:vMerge>`` в ``<w:tcPr>`` уровня <w:tc>.

    val="restart" → ``<w:vMerge w:val="restart"/>``; val=None → continue.
    Существующий vMerge удаляется.
    """
    tcPr = tc.find(qn("w:tcPr"))
    if tcPr is None:
        tcPr = OxmlElement("w:tcPr")
        tc.insert(0, tcPr)
    for vm in tcPr.findall(qn("w:vMerge")):
        tcPr.remove(vm)
    vmerge = OxmlElement("w:vMerge")
    if val == "restart":
        vmerge.set(qn("w:val"), "restart")
    tcPr.append(vmerge)


def _find_spec_table(doc):
    """Найти таблицу спецификации по заголовку первой ячейки = 'Наименование'."""
    for table in doc.tables:
        if not table.rows or not table.rows[0].cells:
            continue
        header_text = "".join(
            r.text or ""
            for p in table.rows[0].cells[0].paragraphs
            for r in p.runs
        ).strip()
        if header_text == "Наименование":
            return table
    return None


def apply_spec_vmerge(doc) -> None:
    """Прогнать пост-обработку маркеров vMerge в таблице спецификации.

    Принимает python-docx ``Document`` (из ``DocxTemplate.docx``).
    Работает на уровне ``<w:tr>`` / ``<w:tc>`` — иначе ``row.cells`` после
    добавления vMerge в одной строке начинает «склеивать» merged-ячейки и
    возвращать ту же ячейку для соседних строк.
    """
    spec_table = _find_spec_table(doc)
    if spec_table is None:
        return

    tbl = spec_table._tbl
    for tr in tbl.findall(qn("w:tr")):
        tcs = tr.findall(qn("w:tc"))
        if len(tcs) < 3:
            continue
        tc = tcs[2]
        text = _tc_text(tc)

        if text == _CONTINUE_TOKEN:
            _set_tc_text(tc, "")
            _set_tc_vmerge(tc, None)
            continue

        m = _RESTART_RE.match(text)
        if m:
            _set_tc_text(tc, m.group(1))
            _set_tc_vmerge(tc, "restart")

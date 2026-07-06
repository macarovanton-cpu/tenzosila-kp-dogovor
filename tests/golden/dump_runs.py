"""Обход ранов одного параграфа для канонического дампа DOCX (P0-01).

Ключевая нормализация: соседние раны с одинаковой ЗНАЧИМОЙ rPr-сводкой
склеиваются в одну строку — Word/docxtpl дробят раны произвольно
(rsid/proofErr-границы), без склейки дифф эталонов шумел бы ложными
расхождениями. w:tab/w:br кодируются как \\t/\\n внутри текста рана
(склейку не рвут); разрыв страницы — отдельная строка [PAGEBREAK].

Принцип: текст НЕ должен молча пропадать из дампа — обрабатываются все
текстонесущие дети рана (t/tab/br/cr/noBreakHyphen/softHyphen/sym, поля,
объекты с textbox).
"""

from __future__ import annotations

from typing import Callable

from lxml import etree

from docx.oxml.ns import qn

from tests.golden.dump_props import rpr_summary

_IND = "  "
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"

# walk-callback: (parent, ctx, level) -> строки дампа (walk_block из dump_walker;
# передаётся параметром, чтобы не создавать циклический импорт)
WalkFn = Callable[[etree._Element, object, int], list[str]]


class RunWalker:
    """Накопитель ранов одного параграфа со склейкой по значимой rPr-сводке."""

    def __init__(self, ctx, level: int, walk: WalkFn) -> None:
        self.ctx = ctx
        self.level = level
        self._walk = walk
        self.lines: list[str] = []
        self._summary: str | None = None
        self._text: list[str] = []
        self._field: dict | None = None  # состояние w:fldChar begin..end

    @property
    def _prefix(self) -> str:
        return _IND * self.level

    def flush(self) -> None:
        """Выдать накопленный ран одной строкой (пустой текст не эмитится)."""
        joined = "".join(self._text)
        if joined:
            self.lines.append(f"{self._prefix}R{self._summary} {joined!r}")
        self._summary = None
        self._text = []

    def close(self) -> None:
        """Конец параграфа: доэмитить незакрытое поле (begin без end в этом
        параграфе — легальный OOXML, напр. TOC) и сбросить буфер ранов.
        Кэш поля из следующих параграфов дампится там как обычный текст —
        частично, но без тихой потери instr."""
        if self._field is not None:
            self._emit_field()
        self.flush()

    def _push(self, summary: str, text: str) -> None:
        """Текстонесущий фрагмент: внутрь активного поля или в буфер ранов."""
        if self._field is not None:
            stage = self._field["stage"]  # instr | cached
            self._field[stage].append(text)
            return
        if summary != self._summary:
            self.flush()
            self._summary = summary
        self._text.append(text)

    def add_run(self, r_el: etree._Element) -> None:
        rpr = r_el.find(qn("w:rPr"))
        self.ctx.register_style(rpr, "w:rStyle")
        summary = rpr_summary(rpr, self.ctx.style_names)
        for el in r_el:
            tag = el.tag
            if tag == qn("w:t"):
                self._push(summary, el.text or "")
            elif tag == qn("w:tab"):
                self._push(summary, "\t")
            elif tag in (qn("w:br"), qn("w:cr")):
                if el.get(qn("w:type")) == "page" and self._field is None:
                    self.flush()
                    self.lines.append(f"{self._prefix}[PAGEBREAK]")
                else:
                    self._push(summary, "\n")
            elif tag == qn("w:noBreakHyphen"):
                self._push(summary, "‑")  # неразрывный дефис
            elif tag == qn("w:softHyphen"):
                self._push(summary, "­")  # мягкий перенос
            elif tag == qn("w:sym"):
                font = el.get(qn("w:font")) or "?"
                self._push(summary, f"[SYM {font} {el.get(qn('w:char')) or '?'}]")
            elif tag == qn("w:fldChar"):
                self._on_fld_char(el, summary)
            elif tag == qn("w:instrText"):
                if self._field is not None:
                    self._field["instr"].append(el.text or "")
            elif tag == qn("w:drawing"):
                self._emit_object(el, summary, is_drawing=True)
            elif tag in (qn("w:pict"), qn("w:object")):
                self._emit_object(el, summary, is_drawing=False)
            elif tag == _MC + "AlternateContent":
                self._on_alternate(el, summary)

    def add_fld_simple(self, fld: etree._Element) -> None:
        """w:fldSimple: инструкция в атрибуте, кэш — вложенные раны."""
        self.flush()
        first_run = fld.find(qn("w:r"))
        rpr = first_run.find(qn("w:rPr")) if first_run is not None else None
        summary = rpr_summary(rpr, self.ctx.style_names)
        instr = (fld.get(qn("w:instr")) or "").strip()
        cached = "".join(t.text or "" for t in fld.findall(".//" + qn("w:t")))
        self.lines.append(f"{self._prefix}R{summary} [FIELD {instr!r}] cached={cached!r}")

    def _on_fld_char(self, el: etree._Element, summary: str) -> None:
        fld_type = el.get(qn("w:fldCharType"))
        if fld_type == "begin":
            if self._field is not None:  # вложенное поле — доэмитить внешнее
                self._emit_field()
            self.flush()
            self._field = {"instr": [], "cached": [], "stage": "instr", "summary": summary}
        elif fld_type == "separate" and self._field is not None:
            self._field["stage"] = "cached"
        elif fld_type == "end" and self._field is not None:
            self._emit_field()

    def _emit_field(self) -> None:
        instr = "".join(self._field["instr"]).strip()
        cached = "".join(self._field["cached"])
        self.lines.append(
            f"{self._prefix}R{self._field['summary']} [FIELD {instr!r}] cached={cached!r}"
        )
        self._field = None

    def _on_alternate(self, el: etree._Element, summary: str) -> None:
        """mc:AlternateContent: дампим только mc:Choice (Fallback — дубль
        того же содержимого в VML, иначе текст textbox удвоится)."""
        choice = el.find(_MC + "Choice")
        target = choice.find(qn("w:drawing")) if choice is not None else None
        if target is not None:
            self._emit_object(target, summary, is_drawing=True)
            return
        fallback = el.find(_MC + "Fallback")
        target = fallback.find(qn("w:pict")) if fallback is not None else None
        if target is not None:
            self._emit_object(target, summary, is_drawing=False)

    def _emit_object(self, el: etree._Element, summary: str, is_drawing: bool) -> None:
        """DRAWING/PICT + рекурсия в textbox (w:txbxContent не виден python-docx API)."""
        self.flush()
        if is_drawing:
            extent = el.find(".//" + qn("wp:extent"))
            dims = f" {extent.get('cx')}x{extent.get('cy')}" if extent is not None else ""
            self.lines.append(f"{self._prefix}R{summary} [DRAWING{dims}]")
        else:
            self.lines.append(f"{self._prefix}R{summary} [PICT]")
        for txbx in el.findall(".//" + qn("w:txbxContent")):
            self.lines.append(f"{self._prefix}{_IND}TXBX")
            self.lines.extend(self._walk(txbx, self.ctx, self.level + 2))

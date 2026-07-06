"""Канонический plain-text дамп DOCX для golden-master верификации (P0-01).

Использование:
    python -m tests.golden.dump_docx <файл.docx> [-o дамп.txt]
    from tests.golden.dump_docx import dump_docx   # API для P0-03/P0-04

Два прогона на одном DOCX дают байт-в-байт идентичный дамп; сравнение
эталонов — построчный pytest-diff.

СПЕЦИФИКАЦИЯ ФОРМАТА (=== DOCX-DUMP v1 ===). Изменение формата = инкремент
версии + перегенерация эталонов по процедуре migration_plan.md §2.4.

Шапка (самодостаточность дампа при явных-только свойствах в теле):
  [DEFAULTS] rPr{...} pPr{...}   — docDefaults (куда проваливается ран без rPr)
  [STYLE] 'Имя' based='Имя' pPr{...} rPr{...} — использованные стили, sort by name
  [NUM] num1 = L0:decimal'%1.' ... — семантика нумераций (алиасы по порядку)
  [MEDIA] word/media/... sha1=... — хэши картинок, sort by name

Тело (=== BODY ===), затем по секциям === HEADER/FOOTER <тип> (sect N) ===:
  P{style;jc;spacing;ind;num;pgbrk}       — параграф (явный pPr)
    R{style;font;sz;b;i;u;strike;color;vertAlign;highlight} 'текст'
    R{...} [FIELD 'PAGE ...'] cached='3'  — поле (instrText + кэш)
    R{...} [DRAWING WxH] / [PICT]         — объект; вложенный textbox:
      TXBX                                 + рекурсивно P/R
    [PAGEBREAK]                            — w:br type="page"
  TBL{cols;grid} / TR{h} / TC{vmerge|span} — таблицы, вложенность отступом
  SECT{pgSz;pgMar;hdr;ftr;titlePg}         — конец секции (в т.ч. из pPr)

Нормализации (источники ложных диффов):
  - соседние раны с одинаковой значимой rPr-сводкой склеены (Word дробит
    раны произвольно по rsid/proofErr-границам); w:tab/w:br -> \\t/\\n
  - текст в Python repr() — видны \\xa0, хвостовые пробелы, ёлочки
  - стили по имени, numId по алиасам (docxcompose переименовывает id)
  - никаких абсолютных индексов — позиция = порядок строк + отступ

Игнорируется (недетерминизм/шум): rsid*, w14:paraId/textId, w:proofErr,
w:bookmarkStart/End, w:lang, w:noProof, szCs/bCs/iCs, fldChar-границы,
все rId, имена/порядок ZIP-частей, docProps/* (не читаются), settings,
theme, fontTable, mc:Fallback (дубль mc:Choice).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docx import Document

from docx.oxml.ns import qn

from tests.golden.dump_styles import (
    build_style_names,
    defaults_line,
    media_lines,
    num_lines_from_zip,
    used_style_lines,
)
from tests.golden.dump_walker import DumpContext, walk_block

DUMP_VERSION = "v1"


def _header_footer_lines(doc, ctx: DumpContext) -> list[str]:
    """Колонтитулы по секциям в document order (sectPr из pPr и хвоста body).

    Часть резолвится через relationships (rId в дамп не попадает).
    Секция без собственного default-колонтитула наследует предыдущий —
    маркер linked-to-previous (для первой секции отсутствие = нет колонтитула).
    """
    lines: list[str] = []
    sect_prs = list(doc.element.body.iter(qn("w:sectPr")))
    for i, sect_pr in enumerate(sect_prs, start=1):
        for ref_tag, label in (("w:headerReference", "HEADER"), ("w:footerReference", "FOOTER")):
            refs = {
                ref.get(qn("w:type")): ref.get(qn("r:id"))
                for ref in sect_pr.findall(qn(ref_tag))
            }
            for hf_type in ("default", "first", "even"):
                r_id = refs.get(hf_type)
                if r_id is None:
                    if hf_type == "default" and i > 1:
                        lines += ["", f"=== {label} default (sect {i}) === linked-to-previous"]
                    continue
                part = doc.part.rels[r_id].target_part
                lines += ["", f"=== {label} {hf_type} (sect {i}) ==="]
                lines += walk_block(part.element, ctx)
    return lines


def dump_docx(path: Path) -> str:
    """Канонический дамп DOCX-файла. Чистая функция: байты файла -> текст."""
    doc = Document(str(path))
    styles_el = doc.styles.element
    ctx = DumpContext(style_names=build_style_names(styles_el))
    # сначала обход (собирает used_style_ids и num_aliases), потом шапка
    body_lines = walk_block(doc.element.body, ctx)
    hf_lines = _header_footer_lines(doc, ctx)
    lines = [f"=== DOCX-DUMP {DUMP_VERSION} ===", "", defaults_line(styles_el)]
    lines += used_style_lines(styles_el, ctx.used_style_ids, ctx.style_names, ctx.num_aliases)
    lines += num_lines_from_zip(path, ctx.num_aliases)
    lines += media_lines(path)
    lines += ["", "=== BODY ==="]
    lines += body_lines
    lines += hf_lines
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Канонический дамп DOCX (golden-master)")
    parser.add_argument("docx_path", type=Path, help="путь к DOCX-файлу")
    parser.add_argument("-o", "--out", type=Path, default=None,
                        help="файл дампа (по умолчанию stdout, utf-8, LF)")
    args = parser.parse_args(argv)
    text = dump_docx(args.docx_path)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))


if __name__ == "__main__":
    main()

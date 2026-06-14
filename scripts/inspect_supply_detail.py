"""Детальная инспекция body-элементов docs/source/Автовесы _Поставка.docx.

Выводит все элементы body в порядке следования (параграфы + таблицы).
Запуск: python scripts/inspect_supply_detail.py
"""
from docx import Document
from docx.oxml.ns import qn
from pathlib import Path

SRC = Path("docs/source/Автовесы _Поставка.docx")
OUT = Path("docs/source/inspect_supply_detail.txt")
doc = Document(str(SRC))

lines = []
body = doc.element.body
para_idx = 0
tbl_idx = 0

for child in body.iterchildren():
    tag = child.tag
    if tag == qn("w:p"):
        texts = [t.text or "" for t in child.findall(".//" + qn("w:t"))]
        text = "".join(texts).strip()
        if text:
            lines.append(f"P[{para_idx:3d}] {text[:120]}")
        else:
            lines.append(f"P[{para_idx:3d}] (пустой)")
        para_idx += 1
    elif tag == qn("w:tbl"):
        rows = child.findall(".//" + qn("w:tr"))
        lines.append(f"\n=== TABLE[{tbl_idx}] — {len(rows)} строк ===")
        for ri, row in enumerate(rows):
            cells = row.findall(".//" + qn("w:tc"))
            for ci, cell in enumerate(cells):
                texts = [t.text or "" for t in cell.findall(".//" + qn("w:t"))]
                cell_text = "".join(texts).strip()[:80]
                lines.append(f"  T[{tbl_idx}] Row{ri} Col{ci}: {cell_text}")
        lines.append("")
        tbl_idx += 1
    elif tag == qn("w:sectPr"):
        lines.append("[sectPr]")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"Готово: {OUT}")

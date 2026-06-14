"""Полный текст ключевых параграфов и ячеек для замены плейсхолдеров."""
from docx import Document
from docx.oxml.ns import qn
from pathlib import Path

SRC = Path("docs/source/Автовесы _Поставка.docx")
OUT = Path("docs/source/inspect_supply_full.txt")
doc = Document(str(SRC))

lines = []

# Полный текст параграфов по body-индексам
TARGET_PARAS = [7, 21, 22, 23, 36, 37, 38, 64, 65, 72]
body = doc.element.body
para_idx = 0
tbl_idx = 0

for child in body.iterchildren():
    tag = child.tag
    if tag == qn("w:p"):
        if para_idx in TARGET_PARAS:
            texts = [t.text or "" for t in child.findall(".//" + qn("w:t"))]
            full = "".join(texts)
            lines.append(f"\n=== P[{para_idx}] (полный) ===")
            lines.append(full)
            lines.append(f"--- runs ---")
            for ri, r in enumerate(child.findall(".//" + qn("w:r"))):
                rt = "".join(t.text or "" for t in r.findall(qn("w:t")))
                if rt:
                    lines.append(f"  Run[{ri}]: {repr(rt)}")
        para_idx += 1
    elif tag == qn("w:tbl"):
        if tbl_idx == 1:
            lines.append(f"\n=== TABLE[1] (полные ячейки) ===")
            rows = child.findall(".//" + qn("w:tr"))
            for ri, row in enumerate(rows):
                cells = row.findall(".//" + qn("w:tc"))
                for ci, cell in enumerate(cells):
                    texts = [t.text or "" for t in cell.findall(".//" + qn("w:t"))]
                    cell_text = "".join(texts)
                    if cell_text.strip():
                        lines.append(f"\n  T[1] Row{ri} Col{ci}:")
                        lines.append(f"  {cell_text}")
                        lines.append(f"  --- paragraphs ---")
                        for pi, cp in enumerate(cell.findall(".//" + qn("w:p"))):
                            pt = "".join(t.text or "" for t in cp.findall(".//" + qn("w:t")))
                            if pt.strip():
                                lines.append(f"    P[{pi}]: {pt}")
        tbl_idx += 1

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"Готово: {OUT}")

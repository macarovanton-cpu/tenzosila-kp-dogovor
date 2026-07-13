"""A8: снять Word-автонумерацию (numPr) с двух заголовков spec_v2.docx.

Заголовки «2. Порядок оплаты» и «3. Срок поставки…» несут И литеральный «2.»/
«3.» в тексте, И numPr (numId=1) — Word печатает оба номера: «2. 2. Порядок…».
Литеральный текст оставляем единственной нумерацией, снимаем numPr.

Код НЕ трогаем: строки оплаты (2.1, 2.2…) нумерует код, они корректны — numPr
только у этих двух заголовков (numId=1 их единственные члены).

Идемпотентность: _remove_num_pr вернёт False, если numPr уже нет → «already»,
файл не пересохраняется. Повторный прогон .docx не трогает.

Запускать из корня проекта:
    python scripts/patch_spec_v2_headings_numpr.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8")

TEMPLATE = Path("templates/contracts/spec_v2.docx")
BACKUP = Path("templates/contracts/backup") / "spec_v2.docx"

# Стабильные подстроки текста заголовков (до рендера плейсхолдеров).
NEEDLES = ("Порядок оплаты", "Срок поставки")


def _remove_num_pr(paragraph: Paragraph) -> bool:
    """Снять прямой numPr абзаца. True — если было что снимать (idempotent)."""
    p_pr = paragraph._p.pPr
    if p_pr is None or p_pr.numPr is None:
        return False
    p_pr.remove(p_pr.numPr)
    return True


def _has_foreign_element(paragraph: Paragraph) -> bool:
    """True, если в абзаце разрыв/картинка/поле — трогать нельзя (B4)."""
    p = paragraph._p
    for tag in ("w:drawing", "w:pict", "w:object", "w:br",
                "w:lastRenderedPageBreak", "w:fldChar", "w:fldSimple"):
        if p.find(f".//{qn(tag)}") is not None:
            return True
    return False


def main() -> None:
    if not TEMPLATE.exists():
        raise FileNotFoundError(TEMPLATE)
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(TEMPLATE, BACKUP)

    doc = Document(TEMPLATE)
    changed = 0
    for needle in NEEDLES:
        hits = [p for p in doc.paragraphs if needle in p.text]
        if not hits:
            raise RuntimeError(f"заголовок {needle!r} не найден в {TEMPLATE.name}")
        for para in hits:
            if _has_foreign_element(para):
                print(f"{needle!r}: ⚠️ STOP — разрыв/картинка/поле в абзаце, "
                      "не автопатчить.")
                sys.exit(2)
            if _remove_num_pr(para):
                changed += 1
                print(f"{needle!r}: numPr снят — {para.text.strip()[:60]!r}")
            else:
                print(f"{needle!r}: already (numPr нет) — {para.text.strip()[:60]!r}")

    if changed:
        doc.save(TEMPLATE)
    print(f"\nСнято numPr: {changed} (0 = уже без numPr, .docx не тронут).")
    print("Проверь: python -m pytest tests/contracts/test_templates.py -v")


if __name__ == "__main__":
    main()

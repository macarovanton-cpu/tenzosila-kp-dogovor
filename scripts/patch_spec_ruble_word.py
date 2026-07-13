"""A6: заменить статический литерал «рублей» в строке ИТОГО на плейсхолдер
слова-«рубль», который филлер согласует с числом.

  spec_v2.docx, spec_foundation_install.docx:
      «... ({{СПЕЦ_ИТОГО_ПРОПИСЬ}}) рублей ...»  →  «... {{СПЕЦ_ИТОГО_РУБ}} ...»
  supply_contract.docx:
      «... ({{СУММА_ПРОПИСЬЮ}}) рублей ...»       →  «... {{СУММА_РУБ}} ...»

Идемпотентность: сначала ПРОВЕРКА цели, запись файла — только если цель найдена
и ещё не пропатчена. Повторный прогон детектит 0 целей и .docx НЕ пересохраняет.

Запускать из корня проекта:
    python scripts/patch_spec_ruble_word.py
"""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8")

CONTRACTS = Path("templates/contracts")
BACKUP_DIR = CONTRACTS / "backup"


@dataclass(frozen=True)
class Target:
    file: str
    anchor_placeholder: str  # плейсхолдер прописи — опознаёт нужный параграф
    old: str                 # что заменяем (якорь: закр. скобка + рублей)
    new: str                 # плейсхолдер слова-«рубль»


TARGETS = (
    Target("spec_v2.docx", "{{СПЕЦ_ИТОГО_ПРОПИСЬ}}", ") рублей", ") {{СПЕЦ_ИТОГО_РУБ}}"),
    Target("spec_foundation_install.docx", "{{СПЕЦ_ИТОГО_ПРОПИСЬ}}", ") рублей", ") {{СПЕЦ_ИТОГО_РУБ}}"),
    Target("supply_contract.docx", "{{СУММА_ПРОПИСЬЮ}}", ") рублей", ") {{СУММА_РУБ}}"),
)


def _merge_runs(para: Paragraph) -> None:
    """Склеивает соседние runs с одинаковым rPr (idempotent).

    Плейсхолдер и «рублей» могут лежать в разных runs с общим форматированием —
    после склейки якорь ') рублей' оказывается в одном run.
    """
    runs = para.runs
    if len(runs) < 2:
        return
    i = 0
    while i < len(runs) - 1:
        curr, nxt = runs[i], runs[i + 1]
        curr_rpr = curr._r.find(qn("w:rPr"))
        nxt_rpr = nxt._r.find(qn("w:rPr"))
        cx = "" if curr_rpr is None else curr_rpr.xml
        nx = "" if nxt_rpr is None else nxt_rpr.xml
        if cx == nx:
            curr.text += nxt.text
            nxt._r.getparent().remove(nxt._r)
            runs = para.runs
        else:
            i += 1


def _has_foreign_element(para: Paragraph) -> bool:
    """True, если в параграфе есть разрыв/картинка/поле — трогать нельзя (B4)."""
    p = para._p
    for tag in ("w:drawing", "w:pict", "w:object", "w:br", "w:lastRenderedPageBreak",
                "w:fldChar", "w:fldSimple"):
        if p.find(f".//{qn(tag)}") is not None:
            return True
    return False


def _patch_file(path: Path, target: Target) -> tuple[str, str | None]:
    """Возвращает (status, para_text_after|None). status ∈ patched/already/foreign."""
    doc = Document(path)
    for para in doc.paragraphs:
        if target.anchor_placeholder not in para.text:
            continue
        if target.new.strip() in para.text:
            return "already", para.text
        if _has_foreign_element(para):
            return "foreign", para.text  # STOP-сигнал
        _merge_runs(para)
        for run in para.runs:
            if target.old in run.text:
                run.text = run.text.replace(target.old, target.new)
                doc.save(path)
                return "patched", para.text
        raise RuntimeError(
            f"{path.name}: якорь {target.old!r} не найден в параграфе с "
            f"{target.anchor_placeholder} (текст: {para.text!r})"
        )
    raise RuntimeError(f"{path.name}: параграф с {target.anchor_placeholder} не найден")


def main() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    changed = 0
    for t in TARGETS:
        path = CONTRACTS / t.file
        if not path.exists():
            raise FileNotFoundError(path)
        # бэкап один раз (до первой правки)
        bak = BACKUP_DIR / t.file
        if not bak.exists():
            shutil.copy2(path, bak)

        status, text = _patch_file(path, t)
        print(f"{t.file}: {status}")
        if text:
            print(f"    → {text!r}")
        if status == "patched":
            changed += 1
        elif status == "foreign":
            print("    ⚠️ STOP: в параграфе разрыв/картинка/поле — правка вручную, "
                  "не автопатчить.")
            sys.exit(2)

    print(f"\nИзменено файлов: {changed} (0 = уже пропатчено, .docx не тронуты).")
    print("Проверь: python -m pytest tests/contracts/test_templates.py -v")


if __name__ == "__main__":
    main()

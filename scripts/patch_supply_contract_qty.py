"""Разовый хирургический патч supply_contract.docx: количество товара в §1.1.

Меняет плейсхолдер {{ТОВАР_НАИМЕНОВАНИЕ}} → {{ТОВАР_НАИМЕНОВАНИЕ_КОЛВО}}
ТОЛЬКО в абзаце §1.1 («…обязуется передать Покупателю оборудование …»), где
нужно количество весов. Заголовки ТТХ/комплекта и «Приложение №2» продолжают
использовать {{ТОВАР_НАИМЕНОВАНИЕ}} (без количества) — их не трогаем.

Абзац §1.1 идентифицируется по уникальному якорю в тексте, НЕ по номеру абзаца:
проверено — якорь встречается ровно в одном абзаце, плейсхолдер целиком в одном
run. Guard: ровно один абзац-якорь и ровно одна замена, иначе raise.

Запуск: python scripts/patch_supply_contract_qty.py
"""
from pathlib import Path

from docx import Document

DST = Path("templates/contracts/supply_contract.docx")
ANCHOR = "обязуется передать Покупателю оборудование"
OLD = "{{ТОВАР_НАИМЕНОВАНИЕ}}"
NEW = "{{ТОВАР_НАИМЕНОВАНИЕ_КОЛВО}}"


def patch_supply_contract_qty() -> None:
    doc = Document(str(DST))
    targets = [p for p in doc.paragraphs if ANCHOR in p.text]
    if len(targets) != 1:
        raise ValueError(
            f"Ожидался ровно 1 абзац-якорь «{ANCHOR}», найдено {len(targets)}"
        )
    para = targets[0]
    replaced = 0
    for run in para.runs:
        if OLD in run.text:
            run.text = run.text.replace(OLD, NEW)
            replaced += 1
    if replaced != 1:
        raise ValueError(
            f"Ожидалась ровно 1 замена {OLD} в §1.1, выполнено {replaced} "
            "(плейсхолдер разбит по run'ам?)"
        )
    doc.save(str(DST))
    print(f"Пропатчен: {DST} (§1.1 → {NEW})")


if __name__ == "__main__":
    patch_supply_contract_qty()

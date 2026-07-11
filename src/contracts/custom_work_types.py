"""Типы работ произвольных позиций КП — единый источник для UI, snapshot, договора.

Расширение охвата: добавить запись в CUSTOM_WORK_TYPES → тип появляется в селекте
UI и начинает влиять на клаузы+оплату договора. Механизм трогать не нужно.
"""
from __future__ import annotations

from typing import NamedTuple


class WorkType(NamedTuple):
    label: str                 # что видит менеджер в селекте
    spec_id: str | None        # канонический id для clauses_context (None = без клауз)
    scope: str | None          # metadata["scope"] для этого типа
    payment_group: str | None  # бакет оплаты; None → по имени (_payment_group_by_name)


DEFAULT_WORK_TYPE = "other"  # старые снапшоты без поля + безопасный дефолт селекта

# Порядок ключей = порядок в селекте; "other" первый (нейтральный, без клауз).
CUSTOM_WORK_TYPES: dict[str, WorkType] = {
    "other": WorkType("Прочее", None, None, None),
    "installation": WorkType(
        "Монтаж", "installation", "full", "installation_and_verification"
    ),
    # future — раскомментировать при расширении охвата.
    # ⚠️ При раскомментировании сверить scope и payment_group со значениями,
    # которые кладёт соответствующая ОПЦИЯ (from_kp metadata + resolve_payment_group),
    # иначе ручная позиция и опция разойдутся в клаузах/оплате.
    # "foundation":   WorkType("Фундамент", "foundation", "contractor_full", "foundation"),
    # "verification": WorkType("Поверка", "verification", None, "installation_and_verification"),
    # "orion":        WorkType("ОРИОН", "orion", None, "scales"),
}

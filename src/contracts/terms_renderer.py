"""terms_renderer.py — динамические строки сроков для spec_v2."""
from __future__ import annotations

from src.contracts.clauses_context import build_clauses_context
from src.term_days import (
    TERM_DAYS_DEFAULTS,
    calculate_term_days_per_item,
    resolve_term_role,
)


def _role_days(spec_items: list[dict]) -> dict[str, int]:
    """item_key→days → role→days (первый item каждой роли)."""
    item_days, _ = calculate_term_days_per_item(spec_items)
    result: dict[str, int] = {}
    for item_key, days in item_days.items():
        if days is None:
            continue
        role = resolve_term_role(item_key)
        if role and role not in result:
            result[role] = days
    return result


def render_terms_section(deal: dict, spec_items: list[dict]) -> list[str]:
    """Сформировать строки блока «Сроки» для spec_v2.

    Возвращает list[str], каждый элемент — один параграф DOCX.
    """
    ctx = build_clauses_context(deal)
    days = _role_days(spec_items)

    scales_d = days.get("scales", TERM_DAYS_DEFAULTS["scales"])
    foundation_d = days.get("foundation", TERM_DAYS_DEFAULTS["foundation"])
    install_d = days.get("install", TERM_DAYS_DEFAULTS["install"])

    lines: list[str] = []

    lines.append(
        f"- поставка Весов: в течение {scales_d} рабочих дней "
        "с момента поступления предоплаты"
    )

    if ctx["foundation_scope"] in ("contractor_full", "contractor_with_materials"):
        lines.append(
            f"- строительство фундамента Весов: в течение {foundation_d} рабочих дней "
            "с момента поступления предоплаты"
        )

    if ctx["installation_scope"] != "none":
        lines.append(
            f"- монтаж Весов и поверка Весов: в течение {install_d} рабочих дней "
            "при условии получения Подрядчиком предоплаты"
        )

    return lines

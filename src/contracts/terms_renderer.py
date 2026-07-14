"""terms_renderer.py — динамические строки сроков для spec_v2."""
from __future__ import annotations

from src.contracts.clauses_context import build_clauses_context
from src.contracts.utils import days_genitive
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


def _format_work_days(days: int) -> str:
    return f"{days} ({days_genitive(days)}) рабочих дней"


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
    has_contractor_foundation = ctx["foundation_scope"] in (
        "contractor_full",
        "contractor_with_materials",
    )

    if has_contractor_foundation:
        lines.append(
            f"- строительство фундамента Весов: в течение {_format_work_days(foundation_d)} "
            "с момента поступления предоплаты. "
            "Работы по строительству фундамента Весов проводятся при условии "
            "среднесуточной температуры выше +5 °С."
        )

    payment_refs = "п.2.1 и п.2.2" if has_contractor_foundation else "п.2.1"
    lines.append(
        f"- поставка Весов: в течение {_format_work_days(scales_d)} "
        "с момента поступления предоплаты. "
        "Весы отгружаются Заказчику только после их полной оплаты "
        f"в соответствии с {payment_refs} настоящей Спецификации."
    )

    if ctx["installation_scope"] != "none":
        crew = (
            "строительной и монтажной бригад" if has_contractor_foundation
            else "монтажной бригады"
        )
        # B11: поверка называется в сроках только если она есть в сделке.
        subj = (
            "монтаж Весов и поверка Весов" if ctx["verification_scope"] != "none"
            else "монтаж Весов"
        )
        lines.append(
            f"- {subj}: в течение {_format_work_days(install_d)} "
            "при условии получения Подрядчиком предоплаты. "
            f"Выезд {crew} на Объект работ осуществляется при соблюдении "
            "вышеперечисленных условий и получения Подрядчиком письменного "
            "уведомления от Заказчика о готовности принять на площадку монтажа "
            "специалистов Подрядчика."
        )

    return lines

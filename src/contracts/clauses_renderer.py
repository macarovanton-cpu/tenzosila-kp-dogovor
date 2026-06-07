"""clauses_renderer.py — сборка применимых clauses с нумерацией и jinja-подстановкой."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import jinja2

from src.contracts.clauses_context import build_clauses_context
from src.contracts.clauses_loader import Clause, ClausesLibrary, load_clauses

_logger = logging.getLogger(__name__)

_LIBRARY: ClausesLibrary | None = None
_CLAUSES_PATH = Path("data/clauses.yaml")
_OBLIGATIONS_RANGE_EXCLUDED_IDS = {"customer_unable_to_accept_team_delays_work"}


@dataclass
class RenderedClause:
    id: str
    section: str
    auto_number: str
    text: str


def _get_library() -> ClausesLibrary:
    global _LIBRARY
    if _LIBRARY is None:
        _LIBRARY = load_clauses(_CLAUSES_PATH)
    return _LIBRARY


def _render_text(template_str: str, params: dict) -> str:
    env = jinja2.Environment(undefined=jinja2.Undefined)
    return env.from_string(template_str).render(**params)


def build_contract_clauses(deal: dict) -> dict[str, list[RenderedClause]]:
    """Собрать применимые clauses для deal. Возвращает section_id → [RenderedClause].

    Только непустые секции попадают в результат.
    """
    library = _get_library()
    context = build_clauses_context(deal)
    sections = library.get_sections()

    # Шаг 1: отфильтровать clauses по применимости
    applicable: dict[str, list[Clause]] = {}
    for section in sections:
        clauses = sorted(library.get_clauses_for_section(section.id), key=lambda c: c.order)
        filtered: list[Clause] = []
        for clause in clauses:
            try:
                if clause.applies_when.evaluate(context):
                    filtered.append(clause)
            except KeyError as e:
                _logger.warning("Clause %s: пропущена переменная %s", clause.id, e)
        if filtered:
            applicable[section.id] = filtered

    # Шаг 2: сквозная плоская нумерация clauses начиная с 4
    numbered: list[tuple[str, Clause, str]] = []
    current_number = 4
    for section in sections:
        for clause in applicable.get(section.id, []):
            numbered.append((section.id, clause, str(current_number)))
            current_number += 1

    # Шаг 3: вычислить obligations_range по плоской нумерации
    range_nums: list[str] = []
    for section_id, clause, auto_number in numbered:
        is_customer_obligation = (
            section_id == "obligations_customer"
            and clause.id not in _OBLIGATIONS_RANGE_EXCLUDED_IDS
        )
        if is_customer_obligation or section_id == "special_conditions":
            range_nums.append(auto_number)

    if len(range_nums) > 1:
        obligations_range = f"{range_nums[0]}-{range_nums[-1]}"
    elif range_nums:
        obligations_range = range_nums[0]
    else:
        obligations_range = ""

    # Шаг 4: jinja-параметры для подстановки в тексты
    items_by_id = {item["id"]: item for item in (deal.get("items") or [])}
    has_orion = context["has_orion"]
    foundation_scope = context["foundation_scope"]

    foundation_term = 60
    if "foundation" in items_by_id:
        foundation_term = int(
            items_by_id["foundation"].get("metadata", {}).get("construction_term_days_by_customer", 60)
        )

    jinja_params = {
        "foundation_term_days_by_customer": foundation_term,
        "scales_or_with_orion": "Весы и комплект ПАК «ОРИОН»" if has_orion else "Весы",
        "install_site_label": "месту установки" if foundation_scope == "rama" else "фундаменту",
        "obligations_range": obligations_range,
        "delivery_address_text": deal.get("delivery_address", ""),
    }

    # Шаг 5: рендеринг
    result: dict[str, list[RenderedClause]] = {}
    for section_id, clause, auto_number in numbered:
        result.setdefault(section_id, []).append(
            RenderedClause(
                id=clause.id,
                section=section_id,
                auto_number=auto_number,
                text=_render_text(clause.text.strip(), jinja_params),
            )
        )

    return result

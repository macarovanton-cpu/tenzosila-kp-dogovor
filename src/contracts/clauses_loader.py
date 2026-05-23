"""clauses_loader.py — загрузка и валидация data/clauses.yaml."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import strictyaml as _sy

from src.contracts.clauses_dsl import Expression, parse

_logger = logging.getLogger(__name__)


@dataclass
class Section:
    id: str
    title: str
    section_number: int = 0


@dataclass
class Clause:
    id: str
    section: str
    order: int
    applies_when: Expression
    text: str
    related_to: list[str] = field(default_factory=list)


class ClausesLibrary:
    def __init__(self, sections: list[Section], clauses: list[Clause]) -> None:
        self._sections_list = sections
        self._sections = {s.id: s for s in sections}
        self._clauses = clauses

    def get_sections(self) -> list[Section]:
        return list(self._sections_list)

    def get_clauses_for_section(self, section_id: str) -> list[Clause]:
        return [c for c in self._clauses if c.section == section_id]


def load_clauses(path: Path) -> ClausesLibrary:
    """Загрузить data/clauses.yaml. Raises ValueError на ошибки валидации."""
    data = _sy.load(path.read_text(encoding="utf-8"), _sy.Any()).data

    sections: list[Section] = []
    section_ids: set[str] = set()
    for s in data.get("sections", []):
        section_ids.add(s["id"])
        sections.append(Section(
            id=s["id"],
            title=str(s["title"]),
            section_number=int(s.get("section_number", 0)),
        ))

    clauses: list[Clause] = []
    seen_ids: set[str] = set()
    for c in data.get("clauses", []):
        cid = str(c["id"])
        if cid in seen_ids:
            raise ValueError(f"Дублирующийся id clause: {cid!r}")
        seen_ids.add(cid)

        sec = str(c["section"])
        if sec not in section_ids:
            raise ValueError(f"Clause {cid!r}: неизвестная section {sec!r}")

        applies_when_str = str(c.get("applies_when", "true"))
        try:
            applies_when = parse(applies_when_str)
        except ValueError as e:
            raise ValueError(f"Clause {cid!r}: ошибка applies_when: {e}") from e

        text = str(c.get("text", ""))
        placeholders = re.findall(r'\{\{\s*(\w+)\s*\}\}', text)
        if placeholders:
            _logger.debug("Clause %s требует jinja-параметры: %s", cid, placeholders)

        clauses.append(Clause(
            id=cid,
            section=sec,
            order=int(c.get("order", 0)),
            applies_when=applies_when,
            text=text,
            related_to=list(c.get("related_to") or []),
        ))

    return ClausesLibrary(sections, clauses)

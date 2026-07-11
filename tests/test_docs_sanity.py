"""Санити-чек docs/STATUS.md — карта документов и маркеры.

Ловит три механизма протухания (см. CLAUDE.md «Что НЕ писать в STATUS.md»):
битые пути в карте документов, потерянный маркер текущего шага,
пролезшие в STATUS статусы техдолга.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = (ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8")


def test_paths_in_status_exist() -> None:
    """Каждый упомянутый в STATUS путь docs/ или tests/ существует."""
    paths = re.findall(r"`((?:docs|tests)/[\w./-]+)`", STATUS)
    missing = [p for p in paths if "*" not in p and not (ROOT / p).exists()]
    assert not missing, f"Битые пути в STATUS.md: {missing}"


def test_single_current_marker() -> None:
    """Ровно один маркер текущего шага либо явное «нет активной задачи»."""
    markers = STATUS.count("← ТЕКУЩИЙ")
    assert markers == 1 or (markers == 0 and "(нет активной задачи" in STATUS), (
        f"Маркеров «← ТЕКУЩИЙ»: {markers}, строки «(нет активной задачи» нет"
    )


def test_no_debt_status_markers() -> None:
    """Статусы техдолга живут только в TECH_DEBT.md (один факт — один дом)."""
    leaked = [m for m in ("🔲", "🕵️", "✅ ЗАКРЫТО", "🔒 ОТЛОЖЕНО") if m in STATUS]
    assert not leaked, f"Маркеры статусов техдолга пролезли в STATUS.md: {leaked}"

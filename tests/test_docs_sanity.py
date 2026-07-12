"""Санити-чек docs/STATUS.md — карта документов и маркеры.

Ловит три механизма протухания (см. CLAUDE.md «Что НЕ писать в STATUS.md»):
битые пути в карте документов, потерянный маркер текущего шага,
пролезшие в STATUS статусы техдолга.
"""
import re
import subprocess
from pathlib import Path

import pytest

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


def test_status_date_not_stale() -> None:
    """Дата в шапке STATUS.md не должна отставать от последнего коммита в src/ или tests/."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=short", "--", "src/", "tests/"],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=5,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pytest.skip("git недоступен")
    last_code_change = result.stdout.strip()
    if not last_code_change:
        pytest.skip("нет коммитов, затрагивающих src/ или tests/")
    match = re.search(r"Обновлено: (\d{4}-\d{2}-\d{2})", STATUS)
    assert match, "В STATUS.md нет строки «Обновлено: YYYY-MM-DD»"
    status_date = match.group(1)
    assert status_date >= last_code_change, (
        f"STATUS.md обновлён {status_date}, но код менялся {last_code_change} — "
        "обнови дату и/или содержимое STATUS.md"
    )

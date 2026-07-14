"""Заморозка golden-master эталонов (P0-03).

Гонит фикстуры tests/golden/fixtures/*.json через реальный продакшн-путь
(tests.autoverify.runner.generate_all — зеркало кнопки «Сгенерировать» на
2_Договор.py) и кладёт DOCX + канонический дамп в tests/golden/expected/.

Эталон меняется ТОЛЬКО этим скриптом, отдельным коммитом с причиной
(MIGRATION_PLAN.md §2.4) — test_golden.py его не перегенерирует.

CLI: python -m tests.golden.freeze [fixture_id ...]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from tests.autoverify.runner import generate_all
from tests.golden.dump_buckets import buckets_section
from tests.golden.dump_docx import dump_docx
from tests.golden.fixtures import list_fixture_ids, load_fixture

EXPECTED_DIR = Path(__file__).parent / "expected"


def freeze_one(fixture_id: str) -> None:
    """Сгенерировать фикстуру и записать .docx + .dump.txt в expected/."""
    result = generate_all(load_fixture(fixture_id), EXPECTED_DIR)
    for kind, path in result.docx_paths.items():
        # kp — свой билдер (spec_builder), остальные — from_kp; расхождение
        # между ними это ровно то, что BUCKETS должен ловить (B11/B12).
        items = result.kp_items if kind == "kp" else result.items
        dump_path = path.with_suffix(".dump.txt")
        text = dump_docx(path) + buckets_section(items)
        dump_path.write_text(text, encoding="utf-8", newline="\n")
        print(f"{fixture_id}: {path.name} -> {dump_path.name}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Заморозка golden-master эталонов")
    parser.add_argument(
        "fixture_ids", nargs="*", help="id фикстур (по умолчанию — все)",
    )
    args = parser.parse_args(argv)
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    for fixture_id in args.fixture_ids or list_fixture_ids():
        freeze_one(fixture_id)


if __name__ == "__main__":
    main()

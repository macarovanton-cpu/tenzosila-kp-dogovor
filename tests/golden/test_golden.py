"""P0-04: текущий код против замороженных эталонов tests/golden/expected/.

Эталон меняется ТОЛЬКО через tests/golden/freeze.py, отдельным коммитом с
причиной (MIGRATION_PLAN.md §2.4) — этот тест ничего не перегенерирует.
"""
from __future__ import annotations

import pytest

from tests.autoverify.runner import generate_all
from tests.golden.dump_buckets import buckets_section
from tests.golden.dump_docx import dump_docx
from tests.golden.fixtures import list_fixture_ids, load_fixture
from tests.golden.freeze import EXPECTED_DIR


@pytest.mark.parametrize("fixture_id", list_fixture_ids())
def test_golden(fixture_id, tmp_path) -> None:
    """Дамп текущего вывода совпадает с замороженным эталоном по каждому DOCX."""
    result = generate_all(load_fixture(fixture_id), tmp_path)
    for kind, path in result.docx_paths.items():
        items = result.kp_items if kind == "kp" else result.items
        expected_path = (EXPECTED_DIR / path.name).with_suffix(".dump.txt")
        expected = expected_path.read_text(encoding="utf-8")
        actual = dump_docx(path) + buckets_section(items)
        assert actual == expected, (
            f"{fixture_id}: {path.name} разошёлся с эталоном {expected_path.name}"
        )

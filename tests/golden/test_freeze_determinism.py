"""P0-03: два прогона одной golden-фикстуры дают идентичные дампы."""
from __future__ import annotations

from tests.golden.dump_buckets import buckets_section
from tests.golden.dump_docx import dump_docx


def test_two_runs_identical(generated, generated_again) -> None:
    """dump_docx() + BUCKETS каждого документа совпадает прогон-к-прогону."""
    assert generated.docx_paths.keys() == generated_again.docx_paths.keys()
    for kind, path_a in generated.docx_paths.items():
        path_b = generated_again.docx_paths[kind]
        items_a = generated.kp_items if kind == "kp" else generated.items
        items_b = generated_again.kp_items if kind == "kp" else generated_again.items
        dump_a = dump_docx(path_a) + buckets_section(items_a)
        dump_b = dump_docx(path_b) + buckets_section(items_b)
        assert dump_a == dump_b, (
            f"{generated.fixture_id}/{kind}: дампы двух прогонов различаются"
        )

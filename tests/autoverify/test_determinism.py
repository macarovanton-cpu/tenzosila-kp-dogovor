"""Регрессия: два прогона одной фикстуры дают идентичные DOCX (по дампу)."""
from __future__ import annotations

from tests.autoverify.docx_text import dump_docx


def test_two_runs_identical(generated, generated_again) -> None:
    """dump_docx() каждого документа байт-в-байт совпадает прогон-к-прогону."""
    assert generated.docx_paths.keys() == generated_again.docx_paths.keys()
    for kind, path_a in generated.docx_paths.items():
        path_b = generated_again.docx_paths[kind]
        dump_a = dump_docx(path_a)
        dump_b = dump_docx(path_b)
        assert dump_a == dump_b, (
            f"{generated.fixture_id}/{kind}: дампы двух прогонов различаются"
        )

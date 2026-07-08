"""Дубли клауз в договоре — HARD fail (баг класса custom_N)."""
from __future__ import annotations


def test_no_duplicate_clause_ids(generated) -> None:
    """Один clause-id не может войти в договор дважды."""
    ids = [c.id for section in generated.clauses.values() for c in section]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    assert not dups, f"{generated.fixture_id}: дубли clause-id {dups}"


def test_clause_numbers_sequential(generated) -> None:
    """Сквозные номера клауз уникальны и непрерывны начиная с 4."""
    numbers = [
        int(c.auto_number)
        for section in generated.clauses.values()
        for c in section
    ]
    assert numbers, f"{generated.fixture_id}: клаузы не сгенерированы"
    assert sorted(numbers) == list(range(4, 4 + len(numbers))), (
        f"{generated.fixture_id}: нумерация клауз не сквозная: {sorted(numbers)}"
    )

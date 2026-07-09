"""Арифметика: суммы позиций, НДС 22%, покрытие графика оплаты."""
from __future__ import annotations

from src.ui.payment_lines_editor import _validate_rows
from tests.autoverify.docx_text import extract_text, find_spec_table, vat_rates

# Документы с таблицей спецификации (у договора spec-флоу её нет)
_TABLE_KINDS = ("kp", "spec", "supply")


def _expected_items_total(generated) -> int:
    """Σ позиций per-unit без customer_side — из входного контекста раннера."""
    return sum(
        int(it.get("total") or 0)
        for it in generated.items
        if not it.get("metadata", {}).get("customer_side")
    )


def test_spec_table_sums(generated) -> None:
    """Σ строк таблицы спецификации == ИТОГО в самом DOCX == Σ входных позиций."""
    for kind in _TABLE_KINDS:
        path = generated.docx_paths.get(kind)
        if path is None:
            continue
        table = find_spec_table(path)
        rows_sum = sum(value for _, value in table.rows)
        where = f"{generated.fixture_id}/{kind}"
        assert rows_sum == table.itogo_per_1, (
            f"{where}: Σ строк {rows_sum} != ИТОГО {table.itogo_per_1}"
        )
        # supply-спецификация агрегирует позиции (весы одной строкой, без работ)
        # — сверка с полным Σ входных позиций осмысленна только для kp/spec.
        if kind in ("kp", "spec"):
            # Инвариант: сумма КП == сумма договора (одни и те же позиции).
            expected = _expected_items_total(generated)
            assert table.itogo_per_1 == expected, (
                f"{where}: ИТОГО {table.itogo_per_1} != Σ позиций входа {expected}"
            )


def test_vat_is_22(generated) -> None:
    """Во всех документах НДС 22% (нормализованный матч) и нигде нет НДС 20%."""
    for kind, path in generated.docx_paths.items():
        rates = vat_rates(extract_text(path))
        where = f"{generated.fixture_id}/{kind}"
        assert 22 in rates, f"{where}: НДС 22% не найден (найдено: {rates})"
        assert 20 not in rates, f"{where}: найден НДС 20%"


def test_payment_rows_cover_total(generated) -> None:
    """График оплаты покрывает ИТОГО: Σ сумм == spec_total (допуск округления
    как в _validate_rows), без ошибок и предупреждений редактора.

    Примечание: инвариант «Σ% по каждой базе == 100» для split_by_items
    не выполняется by design (строки комбинируют бакеты с разными базами),
    поэтому проверяется покрытие суммами, а не процентами.
    """
    rows = generated.payment_rows
    assert rows, f"{generated.fixture_id}: строки оплаты не сгенерированы"

    amount_total = sum(int(r.get("Сумма, ₽") or 0) for r in rows)
    tolerance = max(len(rows), 1)  # ~рубль округления на строку
    diff = generated.spec_total - amount_total
    assert 0 <= diff <= tolerance, (
        f"{generated.fixture_id}: Σ оплат {amount_total} vs "
        f"ИТОГО {generated.spec_total} (diff {diff})"
    )

    error, warnings = _validate_rows(rows, generated.spec_total)
    assert error is None, f"{generated.fixture_id}: {error}"
    assert warnings == [], f"{generated.fixture_id}: {warnings}"

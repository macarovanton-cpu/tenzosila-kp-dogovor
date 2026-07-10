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


def test_qty_gt1_itogo_scales(generated) -> None:
    """При qty>1: ИТОГО за N == ИТОГО за 1 × qty в каждом документе и совпадает
    между КП и договором/спекой — инвариант КП==договор ×N."""
    if generated.model_qty <= 1:
        return
    itogo_ns: dict[str, int] = {}
    for kind in _TABLE_KINDS:
        path = generated.docx_paths.get(kind)
        if path is None:
            continue
        table = find_spec_table(path)
        where = f"{generated.fixture_id}/{kind}"
        assert table.itogo_n is not None, f"{where}: нет строки «ИТОГО за N весов»"
        assert table.itogo_n == table.itogo_per_1 * generated.model_qty, (
            f"{where}: ИТОГО за N {table.itogo_n} != "
            f"{table.itogo_per_1} × {generated.model_qty}"
        )
        itogo_ns[kind] = table.itogo_n
    assert len(set(itogo_ns.values())) == 1, (
        f"{generated.fixture_id}: ИТОГО за N расходится между документами: {itogo_ns}"
    )


_SUPPLY_HEADERS = (
    "Технические характеристики весов",
    "Комплект поставки весов",
    "Приложение №2",
)


def test_supply_headers_no_qty(generated) -> None:
    """Supply-заголовки (ТТХ/комплект/приложение №2) — всегда без «шт.».
    Количество несут только §1.1 и строка позиции, и только при qty>1."""
    if generated.flow != "supply":
        return
    lines = [l.strip() for l in extract_text(generated.docx_paths["supply"]).split("\n")]
    where = generated.fixture_id
    for header in _SUPPLY_HEADERS:
        for line in lines:
            if header in line:
                assert "шт." not in line, f"{where}: «шт.» в заголовке: {line!r}"
    if generated.model_qty > 1:
        need = f"в количестве {generated.model_qty}шт."
        s11 = next(
            (l for l in lines if "обязуется передать Покупателю оборудование" in l),
            None,
        )
        assert s11 and need in s11, f"{where}: §1.1 без «{need}»: {s11!r}"
        assert any(need in l for l in lines), f"{where}: строка позиции без «{need}»"


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

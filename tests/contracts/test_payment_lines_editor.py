"""Тесты pure-функций редактора строк оплаты."""

import pandas as pd
import pytest

from src.contracts.payment_line import (
    PaymentLine,
    PaymentTrigger,
    build_lines_from_snapshot,
)
from src.ui.payment_lines_editor import (
    _COLUMNS,
    _TRIGGER_LABELS,
    _line_to_row,
    _normalize_rows,
    _recompute_amounts,
    _row_to_line,
    _rows_amount_total,
    _validate_rows,
    render_payment_lines_editor,
)


@pytest.mark.parametrize("trigger", list(PaymentTrigger))
def test_line_to_row_round_trip(trigger: PaymentTrigger):
    line = PaymentLine(
        kind="доплата",
        share_pct=50.0,
        share_prep="от стоимости",
        share_object="Весов",
        amount=500_000,
        trigger=trigger,
        due=5,
        due_unit="банковских",
        base_amount=1_000_000,
    )

    assert _row_to_line(_line_to_row(line)) == line


def test_row_to_line_no_pct():
    row = {
        "Тип": "предоплата",
        "%": None,
        "Основа": "от стоимости",
        "Объект": "Весов и доставки",
        "Сумма, ₽": 1_200_000,
        "Событие": "Готовность к отгрузке",
        "Дней": 5,
        "Ед.": "банковских",
    }

    line = _row_to_line(row)

    assert line.share_pct is None
    assert line.share_prep is None


def test_trigger_labels_complete():
    assert set(_TRIGGER_LABELS.values()) == set(PaymentTrigger)


def test_rows_amount_total_allows_empty_amount():
    rows = [
        {"Сумма, ₽": 100_000},
        {"Сумма, ₽": None},
        {},
    ]

    assert _rows_amount_total(rows) == 100_000


class _FakeColumnConfig:
    def SelectboxColumn(self, *args, **kwargs):
        return ("selectbox", args, kwargs)

    def NumberColumn(self, *args, **kwargs):
        return ("number", args, kwargs)

    def TextColumn(self, *args, **kwargs):
        return ("text", args, kwargs)


class _FakeStreamlit:
    column_config = _FakeColumnConfig()

    def __init__(self, button_clicked: bool = False):
        self.button_clicked = button_clicked
        self.errors: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.session_state = {"contract": {"kp_payment_snapshot": {}}}

    def subheader(self, *args, **kwargs):
        pass

    def button(self, *args, **kwargs):
        return self.button_clicked

    def data_editor(self, data, *args, **kwargs):
        return data

    def error(self, message: str):
        self.errors.append(message)

    def info(self, message: str):
        self.infos.append(message)

    def warning(self, message: str):
        self.warnings.append(message)

    def caption(self, *args, **kwargs):
        pass

    def text(self, *args, **kwargs):
        pass

    def rerun(self):
        pass


def test_render_empty_editor_shows_info_instead_of_delta(monkeypatch):
    fake_st = _FakeStreamlit()
    monkeypatch.setattr("src.ui.payment_lines_editor.st", fake_st)
    monkeypatch.setattr("src.ui.payment_lines_editor.get_payment_lines", lambda: [])
    monkeypatch.setattr(
        "src.ui.payment_lines_editor.get_spec_items",
        lambda: [{"total": 4_649_000}],
    )
    monkeypatch.setattr("src.ui.payment_lines_editor.get_model_qty", lambda: 1)
    monkeypatch.setattr("src.ui.payment_lines_editor.set_payment_lines", lambda rows: None)

    render_payment_lines_editor()

    assert fake_st.infos == [
        "Строки оплаты не заполнены. Нажмите «Заполнить по умолчанию» "
        "или добавьте строки вручную."
    ]
    assert fake_st.errors == []


def test_render_undershoot_warns_not_errors(monkeypatch):
    """Недобор до ИТОГО → мягкий warning (не красный error), с разрядкой пробелами."""
    fake_st = _FakeStreamlit()
    rows = [{"Сумма, ₽": 0}]
    monkeypatch.setattr("src.ui.payment_lines_editor.st", fake_st)
    monkeypatch.setattr("src.ui.payment_lines_editor.get_payment_lines", lambda: rows)
    monkeypatch.setattr(
        "src.ui.payment_lines_editor.get_spec_items",
        lambda: [{"total": 4_649_000}],
    )
    monkeypatch.setattr("src.ui.payment_lines_editor.get_model_qty", lambda: 1)
    monkeypatch.setattr("src.ui.payment_lines_editor.set_payment_lines", lambda rows: None)

    render_payment_lines_editor()

    assert fake_st.errors == []
    assert any("4 649 000" in message for message in fake_st.warnings)
    assert all("4,649,000" not in message for message in fake_st.warnings)


def test_default_fill_warns_when_snapshot_preset_is_not_supported(monkeypatch):
    fake_st = _FakeStreamlit(button_clicked=True)
    monkeypatch.setattr("src.ui.payment_lines_editor.st", fake_st)
    monkeypatch.setattr("src.ui.payment_lines_editor.get_payment_lines", lambda: [])
    monkeypatch.setattr("src.ui.payment_lines_editor.get_spec_items", lambda: [])
    monkeypatch.setattr("src.ui.payment_lines_editor.get_model_qty", lambda: 1)
    monkeypatch.setattr("src.ui.payment_lines_editor.set_payment_lines", lambda rows: None)
    monkeypatch.setattr(
        "src.ui.payment_lines_editor.build_lines_from_snapshot",
        lambda payment, items, model_qty=1: [],
    )

    render_payment_lines_editor()

    assert fake_st.warnings == [
        "Пресет оплаты из КП не поддерживает автозаполнение. "
        "Заполните строки вручную."
    ]


# ---------------------------------------------------------------------------
# _recompute_amounts — «процент истина, сумма производная»
# ---------------------------------------------------------------------------

def _row(pct=None, base=None, amount=0, kind="предоплата",
         event="Подписание спецификации", prep="от стоимости",
         obj="", days=5, unit="банковских") -> dict:
    return {
        "Тип": kind, "%": pct, "Основа": prep, "Объект": obj,
        "База, ₽": base, "Сумма, ₽": amount, "Событие": event,
        "Дней": days, "Ед.": unit,
    }


def test_recompute_non_split_remainder_to_total():
    """Не-split: обе строки base=ИТОГО, Σ%=100 → последняя добирает остаток, Σ==ИТОГО."""
    rows = [_row(pct=33.0, base=1_000_001),
            _row(pct=67.0, base=1_000_001, kind="доплата")]
    out = _recompute_amounts(rows, 1_000_001)
    assert out[0]["Сумма, ₽"] == 330_000        # round(1_000_001 × 33/100)
    assert out[1]["Сумма, ₽"] == 670_001        # остаток
    assert out[0]["Сумма, ₽"] + out[1]["Сумма, ₽"] == 1_000_001


def test_recompute_blank_base_defaults_to_total():
    """Пустая база → ИТОГО."""
    out = _recompute_amounts([_row(pct=50.0, base=None)], 800_000)
    assert out[0]["База, ₽"] == 800_000
    assert out[0]["Сумма, ₽"] == 400_000


def test_recompute_split_bucket_remainder_per_base():
    """Split: разные базы; остаток внутри группы базы (iv 50/50), одиночная база без остатка."""
    rows = [
        _row(pct=50.0, base=3_000_000),                  # одиночная группа базы
        _row(pct=50.0, base=100_000),                    # iv prepay
        _row(pct=50.0, base=100_000, kind="доплата"),    # iv postpay
    ]
    out = _recompute_amounts(rows, 3_100_000)
    assert out[0]["Сумма, ₽"] == 1_500_000               # 50% от 3млн, без остатка (Σ%≠100)
    assert out[1]["Сумма, ₽"] + out[2]["Сумма, ₽"] == 100_000  # iv добран до базы


def test_recompute_does_not_close_remainder_when_pct_sum_over_tolerance():
    """Σ%=100.4 не считается «100%» и не добирает последнюю строку до базы."""
    rows = [
        _row(pct=60.2, base=1_000_000),
        _row(pct=40.2, base=1_000_000, kind="доплата"),
    ]

    out = _recompute_amounts(rows, 1_000_000)

    assert out[0]["Сумма, ₽"] == 602_000
    assert out[1]["Сумма, ₽"] == 402_000
    assert out[0]["Сумма, ₽"] + out[1]["Сумма, ₽"] == 1_004_000


def test_recompute_same_numeric_base_different_objects_does_not_share_remainder():
    """Одинаковая числовая база разных бакетов не создаёт общую группу остатка."""
    rows = [
        _row(pct=50.0, base=1_000_001, obj="Весов"),
        _row(pct=50.0, base=1_000_001, obj="фундамента Весов", kind="доплата"),
    ]

    out = _recompute_amounts(rows, 2_000_002)

    assert out[0]["Сумма, ₽"] == 500_000
    assert out[1]["Сумма, ₽"] == 500_000


def test_recompute_pct_none_keeps_amount():
    """Строка без процента не пересчитывается — сумма из bridge сохраняется."""
    out = _recompute_amounts(
        [_row(pct=None, base=2_200_000, amount=1_200_000, prep="—")], 2_200_000
    )
    assert out[0]["Сумма, ₽"] == 1_200_000


def test_recompute_none_to_pct_switches_to_derived():
    """Уточнение 2: ручной % в плоской строке → переход в режим пересчёта."""
    rows = [_row(pct=None, base=2_000_000, amount=1_200_000, prep="—")]
    rows[0]["%"] = 25.0                                  # менеджер вписал 25%
    out = _recompute_amounts(rows, 2_000_000)
    assert out[0]["Сумма, ₽"] == 500_000                 # round(25% × 2млн), не прежние 1.2млн


def test_recompute_idempotent():
    """recompute(recompute(rows)) == recompute(rows)."""
    rows = [_row(pct=30.0, base=1_000_000),
            _row(pct=70.0, base=1_000_000, kind="доплата")]
    once = _recompute_amounts(rows, 1_000_000)
    assert _recompute_amounts(once, 1_000_000) == once


# ---------------------------------------------------------------------------
# Типы / стабильность (уточнение 1 — защита от вечного rerun)
# ---------------------------------------------------------------------------

def test_normalize_idempotent():
    once = _normalize_rows([_row(pct=50.0, base=1_000_000, amount=500_000)])
    assert _normalize_rows(once) == once


def test_normalize_dataframe_round_trip_stable():
    """Прогон через pd.DataFrame (вносит numpy/NaN) → те же python-строки (synced!=rows сходится)."""
    rows = _normalize_rows([
        _row(pct=50.0, base=1_000_000, amount=500_000),
        _row(pct=None, base=2_000_000, amount=1_200_000, prep="—", kind="доплата"),
    ])
    df_records = pd.DataFrame(rows, columns=_COLUMNS).to_dict("records")
    assert _normalize_rows(df_records) == rows


def test_normalize_output_has_only_builtin_types():
    """В выходе только python int/float/None/str без NaN — иначе guard synced!=rows зациклит."""
    df_records = pd.DataFrame(
        [_row(pct=50.0, base=1_000_000, amount=500_000)], columns=_COLUMNS
    ).to_dict("records")
    out = _normalize_rows(df_records)
    for value in out[0].values():
        assert value is None or type(value).__module__ == "builtins"
        if isinstance(value, float):
            assert value == value  # не NaN


# ---------------------------------------------------------------------------
# _validate_rows — перебор (error) / недобор + сломанная база (warning)
# ---------------------------------------------------------------------------

def test_validate_over_100_per_base_errors():
    rows = [_row(pct=60.0, base=1_000_000),
            _row(pct=60.0, base=1_000_000, kind="доплата")]
    error, _ = _validate_rows(rows, 1_000_000)
    assert error is not None and "100" in error


def test_validate_pct_over_tolerance_errors():
    rows = [_row(pct=60.2, base=1_000_000, amount=602_000),
            _row(pct=40.2, base=1_000_000, amount=402_000, kind="доплата")]
    error, _ = _validate_rows(rows, 1_004_000)
    assert error is not None and "100" in error


def test_validate_amount_overrun_warns_even_one_ruble():
    rows = [_row(pct=None, base=1_000_000, amount=1_000_001, prep="—")]
    error, warnings = _validate_rows(rows, 1_000_000)
    assert error is None
    assert any("превышают" in w and "1" in w for w in warnings)


def test_validate_legit_split_remainder_does_not_warn():
    rows = _recompute_amounts([
        _row(pct=17.0, base=1_000_001),
        _row(pct=83.0, base=1_000_001, kind="доплата"),
    ], 1_000_001)

    error, warnings = _validate_rows(rows, 1_000_001)

    assert rows[0]["Сумма, ₽"] + rows[1]["Сумма, ₽"] == 1_000_001
    assert error is None
    assert warnings == []


def test_validate_same_numeric_base_different_objects_does_not_merge_pct():
    rows = [
        _row(pct=60.0, base=1_000_000, amount=600_000, obj="Весов"),
        _row(
            pct=60.0,
            base=1_000_000,
            amount=600_000,
            obj="фундамента Весов",
            kind="доплата",
        ),
    ]

    error, warnings = _validate_rows(rows, 1_200_000)

    assert error is None
    assert warnings == []


def test_validate_undershoot_warns():
    error, warnings = _validate_rows([_row(pct=50.0, base=1_000_000, amount=500_000)], 1_000_000)
    assert error is None
    assert any("не хватает" in w for w in warnings)


def test_validate_base_over_total_warns():
    _, warnings = _validate_rows([_row(pct=50.0, base=5_000_000, amount=2_500_000)], 1_000_000)
    assert any("больше ИТОГО" in w for w in warnings)


def test_validate_exact_match_clean():
    rows = [_row(pct=50.0, base=1_000_000, amount=500_000),
            _row(pct=50.0, base=1_000_000, amount=500_000, kind="доплата")]
    error, warnings = _validate_rows(rows, 1_000_000)
    assert error is None
    assert warnings == []


# ---------------------------------------------------------------------------
# Регресс: bridge split → editor-пересчёт даёт те же суммы
# ---------------------------------------------------------------------------

def test_recompute_preserves_bridge_split_amounts():
    spec_items = [
        {"item_key": "vesta", "payment_group": "scales",
         "price": 2_000_000, "qty": 1, "total": 2_000_000},
        {"item_key": "f", "payment_group": "foundation",
         "price": 1_000_000, "qty": 1, "total": 1_000_000},
        {"item_key": "d", "payment_group": "delivery",
         "price": 200_000, "qty": 1, "total": 200_000},
        {"item_key": "iv", "payment_group": "installation_and_verification",
         "price": 100_000, "qty": 1, "total": 100_000},
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": {
            "scales": {"prepay": 50, "postpay": 50},
            "foundation": {"prepay": 50, "postpay": 50},
            "delivery": {"prepay": 0, "postpay": 100},
            "installation_and_verification": {"prepay": 50, "postpay": 50},
        },
    }
    lines = build_lines_from_snapshot(payment, spec_items)
    bridge_amounts = [ln.amount for ln in lines]
    spec_total = sum(it["total"] for it in spec_items)
    rows = _recompute_amounts(
        _normalize_rows([_line_to_row(ln) for ln in lines]), spec_total
    )
    assert [r["Сумма, ₽"] for r in rows] == bridge_amounts

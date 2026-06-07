"""Тесты pure-функций редактора строк оплаты."""

import pytest

from src.contracts.payment_line import PaymentLine, PaymentTrigger
from src.ui.payment_lines_editor import (
    _TRIGGER_LABELS,
    _line_to_row,
    _row_to_line,
    _rows_amount_total,
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
    monkeypatch.setattr("src.ui.payment_lines_editor.set_payment_lines", lambda rows: None)

    render_payment_lines_editor()

    assert fake_st.infos == [
        "Строки оплаты не заполнены. Нажмите «Заполнить по умолчанию» "
        "или добавьте строки вручную."
    ]
    assert fake_st.errors == []


def test_render_delta_formats_thousands_with_spaces(monkeypatch):
    fake_st = _FakeStreamlit()
    rows = [{"Сумма, ₽": 0}]
    monkeypatch.setattr("src.ui.payment_lines_editor.st", fake_st)
    monkeypatch.setattr("src.ui.payment_lines_editor.get_payment_lines", lambda: rows)
    monkeypatch.setattr(
        "src.ui.payment_lines_editor.get_spec_items",
        lambda: [{"total": 4_649_000}],
    )
    monkeypatch.setattr("src.ui.payment_lines_editor.set_payment_lines", lambda rows: None)

    render_payment_lines_editor()

    assert any("4 649 000" in message for message in fake_st.errors)
    assert all("4,649,000" not in message for message in fake_st.errors)


def test_default_fill_warns_when_snapshot_preset_is_not_supported(monkeypatch):
    fake_st = _FakeStreamlit(button_clicked=True)
    monkeypatch.setattr("src.ui.payment_lines_editor.st", fake_st)
    monkeypatch.setattr("src.ui.payment_lines_editor.get_payment_lines", lambda: [])
    monkeypatch.setattr("src.ui.payment_lines_editor.get_spec_items", lambda: [])
    monkeypatch.setattr("src.ui.payment_lines_editor.set_payment_lines", lambda rows: None)
    monkeypatch.setattr(
        "src.ui.payment_lines_editor.build_lines_from_snapshot",
        lambda payment, items: [],
    )

    render_payment_lines_editor()

    assert fake_st.warnings == [
        "Пресет оплаты из КП не поддерживает автозаполнение. "
        "Заполните строки вручную."
    ]

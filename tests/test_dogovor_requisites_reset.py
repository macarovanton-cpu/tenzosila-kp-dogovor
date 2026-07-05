"""Регресс: повторное «Распознать» не оставляет реквизиты предыдущей карточки."""
from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "src" / "app.py")

_CARD_A = (
    'ИП Сидорова Мария Ивановна\n'
    'ИНН 500100732259\n'
    'Email: sidorova.ip@test.ru\n'
    'действующая на основании Свидетельства о регистрации\n'
)

_CARD_B = (
    'ЗАО "Вектор"\n'
    'ИНН 7707083893\n'
    'в лице директора Иванова Ивана Ивановича\n'
)


def _fresh_app() -> AppTest:
    return AppTest.from_file(APP_PATH, default_timeout=30).run()


def test_reparse_clears_fields_absent_from_new_card():
    at = _fresh_app()
    at.switch_page("pages/2_Договор.py").run()
    assert not at.exception, f"Page raised: {at.exception}"

    at.text_area(key="w_requisites_paste").set_value(_CARD_A).run()
    at.button(key="btn_parse_requisites").click().run()
    assert not at.exception, f"Page raised after 1st parse: {at.exception}"
    req = at.session_state["contract"]["requisites"]
    assert req["ЗАКАЗЧИК_EMAIL"] == "sidorova.ip@test.ru"
    assert "Свидетельства" in req["ЗАКАЗЧИК_ОСНОВАНИЕ"]

    at.text_area(key="w_requisites_paste").set_value(_CARD_B).run()
    at.button(key="btn_parse_requisites").click().run()
    assert not at.exception, f"Page raised after 2nd parse: {at.exception}"
    req = at.session_state["contract"]["requisites"]
    assert req["ЗАКАЗЧИК_EMAIL"] == ""
    assert req["ЗАКАЗЧИК_ОСНОВАНИЕ"] == ""
    assert at.session_state["w_ЗАКАЗЧИК_EMAIL"] == ""
    assert at.session_state["w_ЗАКАЗЧИК_ОСНОВАНИЕ"] == ""

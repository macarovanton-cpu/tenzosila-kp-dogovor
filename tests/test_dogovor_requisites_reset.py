"""Регресс: повторное «Распознать» НЕ затирает ручной ввод (merge, P1-8),
«Очистить реквизиты» — единственный осознанный полный сброс."""
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

# ФИО в именительном падеже («Директор: ...»): infer_director_gender
# определяет пол по именительному отчеству («в лице ...» парсер сохраняет
# родительный как есть — пол там не выводится, это отдельная известная щель)
_CARD_MALE_NOM = (
    'ООО "Вектор"\n'
    'ИНН 7707083893\n'
    'Директор: Иванов Иван Иванович\n'
)

_CARD_FEMALE_NOM = (
    'ООО "Астра"\n'
    'ИНН 7830002293\n'
    'Директор: Петрова Ольга Сергеевна\n'
)


def _fresh_app() -> AppTest:
    return AppTest.from_file(APP_PATH, default_timeout=30).run()


def _parse(at: AppTest, card: str) -> None:
    at.text_area(key="w_requisites_paste").set_value(card).run()
    at.button(key="btn_parse_requisites").click().run()
    assert not at.exception, f"Page raised: {at.exception}"


def test_reparse_preserves_fields_absent_from_new_card():
    """Поля из первой карточки, которых нет во второй, сохраняются (merge)."""
    at = _fresh_app()
    at.switch_page("pages/2_Договор.py").run()
    assert not at.exception, f"Page raised: {at.exception}"

    _parse(at, _CARD_A)
    req = at.session_state["contract"]["requisites"]
    assert req["ЗАКАЗЧИК_EMAIL"] == "sidorova.ip@test.ru"
    assert "Свидетельства" in req["ЗАКАЗЧИК_ОСНОВАНИЕ"]

    _parse(at, _CARD_B)
    req = at.session_state["contract"]["requisites"]
    assert req["ЗАКАЗЧИК_EMAIL"] == "sidorova.ip@test.ru"
    assert "Свидетельства" in req["ЗАКАЗЧИК_ОСНОВАНИЕ"]
    assert at.session_state["w_ЗАКАЗЧИК_EMAIL"] == "sidorova.ip@test.ru"
    # Распознанные заново поля при этом обновились
    assert req["ЗАКАЗЧИК_ИНН"] == "7707083893"


def test_clear_button_resets_all_fields():
    """«Очистить реквизиты» — полный сброс полей, w_-ключей и поля вставки."""
    at = _fresh_app()
    at.switch_page("pages/2_Договор.py").run()

    _parse(at, _CARD_A)
    assert at.session_state["contract"]["requisites"]["ЗАКАЗЧИК_ИНН"]

    at.button(key="btn_clear_requisites").click().run()
    assert not at.exception, f"Page raised: {at.exception}"
    req = at.session_state["contract"]["requisites"]
    assert req["ЗАКАЗЧИК_ИНН"] == ""
    assert req["ЗАКАЗЧИК_EMAIL"] == ""
    assert req["ЗАКАЗЧИК_ОСНОВАНИЕ"] == ""
    assert at.session_state["w_ЗАКАЗЧИК_ИНН"] == ""
    assert at.session_state["w_ЗАКАЗЧИК_EMAIL"] == ""
    assert at.session_state["w_requisites_paste"] == ""


def test_gender_reinferred_on_new_card():
    """Пол директора не залипает: смена карточки → пере-inference из нового ФИО."""
    at = _fresh_app()
    at.switch_page("pages/2_Договор.py").run()

    _parse(at, _CARD_MALE_NOM)  # Иванов Иван Иванович
    req = at.session_state["contract"]["requisites"]
    assert req["ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ"] == "male"

    _parse(at, _CARD_FEMALE_NOM)  # Петрова Ольга Сергеевна
    req = at.session_state["contract"]["requisites"]
    assert req["ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ"] == "female"
    assert at.session_state["w_ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ"] == "female"


def test_manual_derived_survives_reparse_of_same_card():
    """Ручная правка производного (ФИО_РП) переживает повторное распознавание
    той же карточки; при смене ФИО производное пересчитывается."""
    at = _fresh_app()
    at.switch_page("pages/2_Договор.py").run()

    _parse(at, _CARD_MALE_NOM)
    req = at.session_state["contract"]["requisites"]
    assert req["ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП"]  # автосклонение построено

    manual_rp = "Иванова Ивана Ивановича (правка менеджера)"
    at.text_input(key="w_ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП").set_value(manual_rp).run()
    assert (
        at.session_state["contract"]["requisites"]["ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП"]
        == manual_rp
    )

    _parse(at, _CARD_MALE_NOM)  # та же карточка — первичное ФИО не изменилось
    req = at.session_state["contract"]["requisites"]
    assert req["ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП"] == manual_rp

    _parse(at, _CARD_FEMALE_NOM)  # другое ФИО — производное обязано пересчитаться
    req = at.session_state["contract"]["requisites"]
    assert req["ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП"] != manual_rp
    assert "Петров" in req["ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП"]

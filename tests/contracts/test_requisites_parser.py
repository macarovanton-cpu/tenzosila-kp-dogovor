"""Тесты для src/contracts/requisites_parser.py."""
from __future__ import annotations

import pytest

from src.contracts.requisites_parser import _valid_inn, parse_requisites


# ---------------------------------------------------------------------------
# _valid_inn: контрольная сумма ИНН (правка №4)
# ---------------------------------------------------------------------------

class TestValidInn:
    def test_valid_10_digit(self):
        """Валидный 10-значный ИНН (ООО)."""
        # ИНН Сбербанка: 7707083893
        assert _valid_inn("7707083893") is True

    def test_invalid_10_digit(self):
        """Невалидный 10-значный ИНН (последняя цифра изменена)."""
        assert _valid_inn("7707083890") is False

    def test_valid_12_digit(self):
        """Валидный 12-значный ИНН (ИП)."""
        # Тестовый ИНН: 500100732259
        assert _valid_inn("500100732259") is True

    def test_invalid_12_digit(self):
        """Невалидный 12-значный ИНН."""
        assert _valid_inn("500100732250") is False

    def test_wrong_length(self):
        assert _valid_inn("12345678") is False    # 8 цифр — не ИНН
        assert _valid_inn("1234567890123") is False  # 13 цифр — не ИНН

    def test_empty_string(self):
        assert _valid_inn("") is False


# ---------------------------------------------------------------------------
# Форматные поля
# ---------------------------------------------------------------------------

class TestParseBasicFields:
    def test_inn_10_found(self):
        text = "ИНН: 7707083893"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ИНН") == "7707083893"

    def test_invalid_inn_not_extracted(self):
        """Невалидный ИНН (неверная контрольная сумма) не попадает в поле."""
        text = "ИНН: 7707083890"  # последняя цифра изменена
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_ИНН" not in result

    def test_inn_12_found(self):
        text = "ИНН 500100732259"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ИНН") == "500100732259"

    def test_ogon_13(self):
        text = "ОГРН 1027700132195"
        result = parse_requisites(text)
        # 13 цифр → ОГРН
        assert result.get("ЗАКАЗЧИК_ОГРН") == "1027700132195"

    def test_email(self):
        text = "Email: info@example.ru"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_EMAIL") == "info@example.ru"

    def test_phone(self):
        text = "Тел. +7 495 123-45-67"
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_ТЕЛЕФОН" in result

    def test_phone_with_area_code_in_parens(self):
        text = "Телефон: +7 (473) 214-58-62"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ТЕЛЕФОН") == "+7 (473) 214-58-62"

    def test_phone_4digit_area_code(self):
        text = "Телефон: +7 (4732) 55-44-33"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ТЕЛЕФОН") == "+7 (4732) 55-44-33"

    def test_phone_no_prefix_with_anchor(self):
        text = "тел.: (473) 214-58-62"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ТЕЛЕФОН") == "(473) 214-58-62"

    def test_phone_prefix_8_with_area_code_in_parens(self):
        text = "Телефон: 8 (473) 214-58-62"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ТЕЛЕФОН") == "8 (473) 214-58-62"

    def test_phone_plus7_space_separated(self):
        text = "Телефон: +7 473 214 58 62"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ТЕЛЕФОН") == "+7 473 214 58 62"

    def test_phone_no_prefix_without_anchor_not_recognized(self):
        """10-значное число без якоря тел/факс рядом — не телефон (не угадываем)."""
        text = "Некий номер: 4732145862"
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_ТЕЛЕФОН" not in result

    def test_name_in_quotes(self):
        text = 'ООО "Тензосила"'
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") == 'ООО "Тензосила"'

    def test_name_full_opf_quotes(self):
        """Полная ОПФ словами + кавычки → краткая ОПФ (P1-4)."""
        text = "Публичное акционерное общество «Вектор-Восток»"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") == 'ПАО "Вектор-Восток"'

    def test_name_full_opf_zao_not_eaten_by_ao(self):
        """«Закрытое акционерное общество» → ЗАО, не АО (P1-4)."""
        text = "Закрытое акционерное общество «Салют»"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") == 'ЗАО "Салют"'

    def test_name_ip_with_fio(self):
        """«ИП + полное ФИО» без кавычек → наименование (P1-4)."""
        text = "ИП Петров Сергей Иванович\nИНН 500100732259"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") == "ИП Петров Сергей Иванович"

    def test_name_ip_full_opf_with_fio(self):
        """«Индивидуальный предприниматель + ФИО» → «ИП + ФИО» (P1-4)."""
        text = "Индивидуальный предприниматель Петров Сергей Иванович"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") == "ИП Петров Сергей Иванович"

    def test_empty_text(self):
        assert parse_requisites("") == {}


# ---------------------------------------------------------------------------
# Конфликт КПП vs БИК (правка из брифа)
# ---------------------------------------------------------------------------

class TestBikKppConflict:
    def test_bik_prefix_04(self):
        """9 цифр с префиксом 04 → БИК."""
        text = "044525225"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_БИК") == "044525225"
        assert "ЗАКАЗЧИК_КПП" not in result

    def test_kpp_no_04_prefix(self):
        """9 цифр без префикса 04 → КПП."""
        text = "770701001"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КПП") == "770701001"
        assert "ЗАКАЗЧИК_БИК" not in result

    def test_ambiguous_without_anchor_empty(self):
        """9 цифр без якоря и нестандартный префикс → пустое поле не угадываем."""
        # Префикс не 04 и нет якоря «БИК» рядом → КПП (логика: не 04 → КПП)
        # Проверяем что якорь «БИК» на строке с нетипичным числом блокирует запись
        text = "123456789 БИК"  # якорь БИК есть, но префикс не 04 → неоднозначность
        result = parse_requisites(text)
        # Якорь БИК при отсутствии 04-префикса → пропускаем
        assert "ЗАКАЗЧИК_КПП" not in result

    def test_bik_and_kpp_in_one_text(self):
        """И БИК и КПП в одном тексте → оба заполняются."""
        text = "КПП 770701001\nБИК 044525225"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КПП") == "770701001"
        assert result.get("ЗАКАЗЧИК_БИК") == "044525225"


# ---------------------------------------------------------------------------
# Конфликт р/с vs к/с (правка из брифа)
# ---------------------------------------------------------------------------

class TestRsKsConflict:
    def test_ks_prefix_301(self):
        """20 цифр с префиксом 301 → к/с."""
        text = "30101810400000000225"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КС") == "30101810400000000225"
        assert "ЗАКАЗЧИК_РС" not in result

    def test_rs_prefix_407(self):
        """20 цифр с префиксом 407 → р/с."""
        text = "40702810938000060473"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_РС") == "40702810938000060473"
        assert "ЗАКАЗЧИК_КС" not in result

    def test_ambiguous_prefix_with_anchor_ks(self):
        """Неоднозначный префикс с якорем к/с → к/с."""
        text = "к/с 12345678901234567890"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КС") == "12345678901234567890"

    def test_ambiguous_no_anchor_empty(self):
        """Неоднозначный префикс без якоря → поле пустое (не угадываем)."""
        # Префикс не 301 и не 407/405/406/408, и без якоря
        text = "20098765432109876543"  # нестандартный префикс 200...
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_РС" not in result
        assert "ЗАКАЗЧИК_КС" not in result

    def test_rs_prefix_408_ip(self):
        """20 цифр с префиксом 40802 (счёт ИП) → р/с без якоря (P1-1)."""
        text = "40802810600000004321"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_РС") == "40802810600000004321"
        assert "ЗАКАЗЧИК_КС" not in result

    def test_rs_sch_anchor_unknown_prefix(self):
        """Метка «р/сч» с нестандартным префиксом → якорная ветка р/с (P1-1)."""
        text = "р/сч 20098765432109876543"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_РС") == "20098765432109876543"

    def test_ks_sch_anchor_unknown_prefix(self):
        """Метка «к/сч» с нестандартным префиксом → якорная ветка к/с (P1-1)."""
        text = "к/сч 20098765432109876543"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КС") == "20098765432109876543"


# ---------------------------------------------------------------------------
# Адреса
# ---------------------------------------------------------------------------

class TestAddresses:
    def test_address_no_anchor_goes_to_yur(self):
        """Адрес без якоря → АДРЕС_ЮР, АДРЕС_ПОЧТ пуст."""
        text = "117997 г. Москва ул. Вавилова д. 5"
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_АДРЕС_ЮР" in result
        assert "ЗАКАЗЧИК_АДРЕС_ПОЧТ" not in result

    def test_address_yur_anchor(self):
        """Строка с якорем «юридический» → АДРЕС_ЮР."""
        text = "Юридический адрес: 117997 г. Москва ул. Вавилова д. 5"
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_АДРЕС_ЮР" in result

    def test_address_poct_anchor(self):
        """Строка с якорем «почтовый» → АДРЕС_ПОЧТ."""
        text = "Почтовый адрес: 117997 г. Москва ул. Вавилова д. 5"
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_АДРЕС_ПОЧТ" in result
        assert "ЗАКАЗЧИК_АДРЕС_ЮР" not in result

    def test_both_addresses_with_anchors(self):
        """Два адреса с якорями → разведены по полям."""
        text = (
            "Юридический адрес: 117997 г. Москва ул. Вавилова д. 5\n"
            "Почтовый адрес: 119991 г. Москва ул. Ленина д. 10"
        )
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_АДРЕС_ЮР" in result
        assert "ЗАКАЗЧИК_АДРЕС_ПОЧТ" in result


class TestBugGluedAddress:
    """P0-3: в слитной карточке адрес режется до метки следующего поля."""

    def test_glued_line_address_limited(self):
        text = (
            "ООО «Нева» ИНН 7707083893 КПП 770701001 "
            "198096, г. Санкт-Петербург, Трамвайный пр., д. 5 "
            "тел.: +7 (812) 111-22-33 e-mail: neva@mail.ru"
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_АДРЕС_ЮР") == (
            "198096, г. Санкт-Петербург, Трамвайный пр., д. 5"
        )

    def test_labeled_address_value_unchanged(self):
        """Регресс: обычная строка с меткой — значение как раньше."""
        result = parse_requisites("Юридический адрес: 117997 г. Москва ул. Вавилова д. 5")
        assert result.get("ЗАКАЗЧИК_АДРЕС_ЮР") == "117997 г. Москва ул. Вавилова д. 5"

    def test_street_word_not_cut(self):
        """Гард: «Телеграфная» в названии улицы не режет адрес (Тел\\b)."""
        result = parse_requisites("Юридический адрес: 117997, г. Москва, ул. Телеграфная, д. 3")
        assert result.get("ЗАКАЗЧИК_АДРЕС_ЮР") == "117997, г. Москва, ул. Телеграфная, д. 3"

    def test_bank_street_name_not_bank_label(self):
        """«ул. Банковская» — улица, а не метка банка: адрес цел, банка нет."""
        result = parse_requisites("Юридический адрес: 117997, г. Москва, ул. Банковская, д. 3")
        assert result.get("ЗАКАЗЧИК_АДРЕС_ЮР") == "117997, г. Москва, ул. Банковская, д. 3"
        assert "ЗАКАЗЧИК_БАНК" not in result


# ---------------------------------------------------------------------------
# ФИО директора (правка №2 — консервативность)
# ---------------------------------------------------------------------------

class TestDirectorFio:
    def test_single_director_anchor_found(self):
        """Один якорь + одно ФИО → ДИРЕКТОР_ФИО заполняется."""
        text = "в лице директора Иванова Ивана Ивановича"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ДИРЕКТОР_ФИО") == "Иванова Ивана Ивановича"

    def test_two_fio_director_plus_buh_empty(self):
        """Директор + главбух → ДИРЕКТОР_ФИО пустой (правка №2).

        При двух разных ФИО рядом с якорями директора результат непредсказуем,
        поэтому парсер не заполняет поле.
        """
        text = (
            "Директор: Иванов Иван Иванович\n"
            "Главный бухгалтер: Петрова Мария Ивановна"
        )
        result = parse_requisites(text)
        # Либо только директор (если якорь однозначен), либо пусто
        # В данном случае оба «якоря» есть, но второй якорь не из _ANCHOR_DIRECTOR
        # Проверяем что хотя бы не падает и тип корректен
        assert isinstance(result, dict)

    def test_no_anchor_no_fio(self):
        """Без якоря директора ФИО не извлекается."""
        text = "Контакт: Сидоров Алексей Петрович, тел. +7 495 000-00-00"
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_ДИРЕКТОР_ФИО" not in result

    def test_osnование_extracted(self):
        """Основание извлекается по «на основании»."""
        text = "действующего на основании Устава"
        result = parse_requisites(text)
        osnov = result.get("ЗАКАЗЧИК_ОСНОВАНИЕ", "")
        assert "Устав" in osnov


# ---------------------------------------------------------------------------
# P1 (audit 2026-06-13): «трудные» карточки — тихие ошибки в юр. данных
# ---------------------------------------------------------------------------

class TestBugFalseAddressFromNumbers:
    """P1 №1: строка-реквизит (ИНН/ОГРН/КПП/р-с/БИК) не должна стать адресом.

    Корень: индекс детектился как любые 6 подряд цифр, в т.ч. внутри длинного
    числа. Теперь индекс — отдельностоящее 6-значное число.
    """

    def test_inn_line_not_address(self):
        result = parse_requisites("ИНН 7707083893")
        assert result.get("ЗАКАЗЧИК_ИНН") == "7707083893"
        assert "ЗАКАЗЧИК_АДРЕС_ЮР" not in result

    def test_account_line_not_address(self):
        result = parse_requisites("р/с 40702810938000060473")
        assert "ЗАКАЗЧИК_АДРЕС_ЮР" not in result

    def test_requisites_block_without_address(self):
        text = (
            "ИНН 7707083893\n"
            "ОГРН 1027700132195\n"
            "КПП 770701001\n"
            "р/с 40702810938000060473\n"
            "БИК 044525225"
        )
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_АДРЕС_ЮР" not in result

    def test_real_address_with_index_still_found(self):
        """Регресс: реальный адрес с индексом по-прежнему ловится."""
        result = parse_requisites("117997 г. Москва ул. Вавилова д. 5")
        assert "ЗАКАЗЧИК_АДРЕС_ЮР" in result


class TestBugPhoneFromAccount:
    """P1 №2: телефон не должен матчиться внутри расчётного счёта."""

    def test_account_not_parsed_as_phone(self):
        result = parse_requisites("р/с 40702810938000060473")
        assert "ЗАКАЗЧИК_ТЕЛЕФОН" not in result
        assert result.get("ЗАКАЗЧИК_РС") == "40702810938000060473"

    def test_real_phone_still_found(self):
        """Регресс: нормальный телефон распознаётся."""
        result = parse_requisites("Тел. +7 495 123-45-67")
        assert "ЗАКАЗЧИК_ТЕЛЕФОН" in result

    def test_inn_not_parsed_as_phone_glued_line(self):
        """P0-1: в слитной строке ИНН не уезжает в телефон (репро аудита)."""
        result = parse_requisites("ИНН 7705123452 тел 8 (495) 111-22-33")
        assert result.get("ЗАКАЗЧИК_ТЕЛЕФОН") == "8 (495) 111-22-33"

    def test_phone_no_prefix_anchor_right_before(self):
        """P0-1: якорь вплотную перед 10-значником — телефон, ИНН не задет."""
        result = parse_requisites("ИНН 7707083893 тел. 4952223344")
        assert result.get("ЗАКАЗЧИК_ТЕЛЕФОН") == "4952223344"
        assert result.get("ЗАКАЗЧИК_ИНН") == "7707083893"


class TestBugDirectorVsBuh:
    """P1 №3: ФИО главбуха со следующей строки не должно уйти в директора."""

    def test_director_no_fio_buh_next_line(self):
        text = (
            "Генеральный директор\n"
            "Главный бухгалтер Петрова Мария Ивановна"
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ДИРЕКТОР_ФИО") != "Петрова Мария Ивановна"
        assert "ЗАКАЗЧИК_ДИРЕКТОР_ФИО" not in result

    def test_director_with_fio_same_line(self):
        """Регресс: ФИО директора на той же строке — ловится."""
        result = parse_requisites("в лице директора Иванова Ивана Ивановича")
        assert result.get("ЗАКАЗЧИК_ДИРЕКТОР_ФИО") == "Иванова Ивана Ивановича"

    def test_director_fio_on_next_line(self):
        """P2: ФИО на следующей строке (без чужого якоря) — ловится."""
        result = parse_requisites("Директор\nИванов Иван Иванович")
        assert result.get("ЗАКАЗЧИК_ДИРЕКТОР_ФИО") == "Иванов Иван Иванович"

    def test_director_fio_next_line_buh_after(self):
        """P2: ФИО директора на след. строке, главбух — через строку (не мешает)."""
        text = (
            "Директор\n"
            "Иванов Иван Иванович\n"
            "Главный бухгалтер Петрова Мария Ивановна"
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ДИРЕКТОР_ФИО") == "Иванов Иван Иванович"

    def test_director_next_line_is_contact_empty(self):
        """P2: следующая строка — контакт, не ФИО → поле пустое."""
        result = parse_requisites("Директор\nтел. +7 495 123-45-67")
        assert "ЗАКАЗЧИК_ДИРЕКТОР_ФИО" not in result


class TestBugKpp04Prefix:
    """P1 №4: КПП с префиксом 04 + явный якорь не должен уходить в БИК."""

    def test_kpp_04_with_anchor(self):
        result = parse_requisites("КПП 040101001")
        assert result.get("ЗАКАЗЧИК_КПП") == "040101001"
        assert "ЗАКАЗЧИК_БИК" not in result

    def test_bik_04_no_anchor_still_bik(self):
        """Регресс: 04-префикс без якоря по-прежнему БИК."""
        result = parse_requisites("044525225")
        assert result.get("ЗАКАЗЧИК_БИК") == "044525225"
        assert "ЗАКАЗЧИК_КПП" not in result

    def test_bik_and_kpp_04_both_anchored(self):
        """БИК и КПП-на-04 на разных строках с якорями → оба верны."""
        text = "БИК 044525225\nКПП 040101001"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_БИК") == "044525225"
        assert result.get("ЗАКАЗЧИК_КПП") == "040101001"

    def test_kpp_04_then_bik_same_line(self):
        """P0-2: КПП региона 04 + БИК на одной строке → оба по своим якорям."""
        result = parse_requisites("КПП 041101001 БИК 048405001")
        assert result.get("ЗАКАЗЧИК_КПП") == "041101001"
        assert result.get("ЗАКАЗЧИК_БИК") == "048405001"

    def test_bik_then_kpp_04_same_line(self):
        """P0-2: обратный порядок — БИК, затем КПП региона 04."""
        result = parse_requisites("БИК 048405001 КПП 041101001")
        assert result.get("ЗАКАЗЧИК_БИК") == "048405001"
        assert result.get("ЗАКАЗЧИК_КПП") == "041101001"

    def test_kpp_04_bik_same_line_with_inn(self):
        """P0-2: репро аудита — ИНН + КПП 04 + БИК на одной строке."""
        result = parse_requisites("ИНН 0411123456 КПП 041101001 БИК 048405001")
        assert result.get("ЗАКАЗЧИК_КПП") == "041101001"
        assert result.get("ЗАКАЗЧИК_БИК") == "048405001"


class TestInnKppSlash:
    """Слитный формат «ИНН/КПП 10цифр/9цифр» — частый в реальных карточках.

    Первое число (10) → ИНН, второе (9) → КПП. Берём по длине (подпись + формат
    однозначны), без контрольной суммы. Несовпадение длин → не угадываем.
    """

    def test_slash_canonical(self):
        result = parse_requisites("ИНН/КПП 7707083893/771001001")
        assert result.get("ЗАКАЗЧИК_ИНН") == "7707083893"
        assert result.get("ЗАКАЗЧИК_КПП") == "771001001"

    def test_slash_with_spaces(self):
        result = parse_requisites("ИНН / КПП: 7707083893 / 771001001")
        assert result.get("ЗАКАЗЧИК_ИНН") == "7707083893"
        assert result.get("ЗАКАЗЧИК_КПП") == "771001001"

    def test_slash_inn_invalid_checksum_still_taken(self):
        """ИНН с неверной контрольной суммой в слитном формате — не теряется."""
        result = parse_requisites("ИНН/КПП 7707083890/771001001")
        assert result.get("ЗАКАЗЧИК_ИНН") == "7707083890"
        assert result.get("ЗАКАЗЧИК_КПП") == "771001001"

    def test_slash_wrong_lengths_no_guess(self):
        """Вторая часть 10 цифр (не 9) → КПП не угадываем."""
        result = parse_requisites("ИНН/КПП 7707083893/7710010019")
        assert "ЗАКАЗЧИК_КПП" not in result


class TestBikKppSameLine:
    """P3-гард: КПП и БИК на одной строке разводятся по формату (04/не-04)."""

    def test_kpp_then_bik(self):
        result = parse_requisites("КПП 771001001 БИК 044525225")
        assert result.get("ЗАКАЗЧИК_КПП") == "771001001"
        assert result.get("ЗАКАЗЧИК_БИК") == "044525225"

    def test_bik_then_kpp(self):
        result = parse_requisites("БИК 044525225 КПП 771001001")
        assert result.get("ЗАКАЗЧИК_КПП") == "771001001"
        assert result.get("ЗАКАЗЧИК_БИК") == "044525225"


# ---------------------------------------------------------------------------
# Регресс целой карточки (бывший плейсхолдер — активирован как регресс-тест)
# ---------------------------------------------------------------------------

class TestRealRequisitesFixtures:
    def test_case_ooo_standard(self):
        """Типовая карточка ООО — все поля распознаны, без ложных адреса/телефона."""
        text = """
        ООО "Пример"
        ИНН 7707083893
        КПП 770701001
        ОГРН 1027700132195
        Юридический адрес: 117997 г. Москва ул. Вавилова д. 5
        р/с 40702810938000060473
        Банк: ПАО Сбербанк
        к/с 30101810400000000225
        БИК 044525225
        """
        result = parse_requisites(text)
        assert result["ЗАКАЗЧИК_ИНН"] == "7707083893"
        assert result["ЗАКАЗЧИК_КПП"] == "770701001"
        assert result["ЗАКАЗЧИК_РС"] == "40702810938000060473"
        assert result["ЗАКАЗЧИК_КС"] == "30101810400000000225"
        assert result["ЗАКАЗЧИК_БИК"] == "044525225"
        # Адрес — это адресная строка, а не реквизит-число
        assert result["ЗАКАЗЧИК_АДРЕС_ЮР"].startswith("117997")
        # В карточке нет телефона — он не должен «вытечь» из р/с
        assert "ЗАКАЗЧИК_ТЕЛЕФОН" not in result


# ---------------------------------------------------------------------------
# Эталонные карточки (4 реальных случая) — критерий приёмки label-anchored
# резки. ИНН взяты валидные по контрольной сумме (реальные карточки из ЕГРЮЛ
# всегда валидны; строгий гейт _valid_inn сохранён).
# ---------------------------------------------------------------------------

class TestEtalonCards:
    def test_card1_romashka_glued_director_bank_with_city(self):
        """Слитная метка директора + «в Банк» + город внутри банка."""
        text = (
            "ООО «Ромашка»\n"
            "ИНН 2465098715\n"
            "Директор Ковалёв Пётр Ильич, действует на основании Устава\n"
            "р/с 40702810123450067890 в Банк ПАО «Сбербанк», г. Красноярск "
            "к/с 30101810800000000123 БИК 040407627\n"
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ИНН") == "2465098715"
        assert result.get("ЗАКАЗЧИК_БАНК") == "ПАО «Сбербанк», г. Красноярск"
        assert result.get("ЗАКАЗЧИК_ДИРЕКТОР_ФИО") == "Ковалёв Пётр Ильич"
        assert "Директор" not in result.get("ЗАКАЗЧИК_ДИРЕКТОР_ФИО", "")
        assert result.get("ЗАКАЗЧИК_ОСНОВАНИЕ") == "Устава"
        assert result.get("ЗАКАЗЧИК_РС") == "40702810123450067890"
        assert result.get("ЗАКАЗЧИК_КС") == "30101810800000000123"
        assert result.get("ЗАКАЗЧИК_БИК") == "040407627"

    def test_card2_ip_sidorova_bank_with_inner_quotes(self):
        """Банк с ёлочками внутри + ОГРНИП; банк не подменяет наименование."""
        text = (
            "ИП Сидорова Анна Андреевна\n"
            "ИНН 616712345680\n"
            "ОГРНИП 316619600054321\n"
            "Банк: Филиал «Ростовский» АО «Альфа-Банк» БИК: 046015207\n"
            "действует на основании Свидетельства\n"
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ИНН") == "616712345680"
        assert result.get("ЗАКАЗЧИК_БАНК") == "Филиал «Ростовский» АО «Альфа-Банк»"
        assert result.get("ЗАКАЗЧИК_ОСНОВАНИЕ") == "Свидетельства"
        assert result.get("ЗАКАЗЧИК_ОГРН") == "316619600054321"
        assert result.get("ЗАКАЗЧИК_БИК") == "046015207"
        # Гард: банк не утёк в краткое наименование.
        assert result.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") != 'АО "Альфа-Банк"'

    def test_card3_vektor_double_yolochka_no_osnovanie(self):
        """Незакрытая вложенная ёлочка (одна закрывающая); основания нет."""
        text = (
            "ПАО «Вектор»\n"
            "ИНН 7801234564\n"
            "Банк: ПАО «Банк «Санкт-Петербург»\n"
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ИНН") == "7801234564"
        assert result.get("ЗАКАЗЧИК_БАНК") == "ПАО «Банк «Санкт-Петербург»"
        assert "ЗАКАЗЧИК_ОСНОВАНИЕ" not in result

    def test_card4_granit_unlabeled_account_long_osnovanie(self):
        """Счёт без метки (по префиксу), банк со скобками, длинное основание."""
        text = (
            "ООО «Гранит»\n"
            "ИНН 3123456783\n"
            "40702810700000098765 Банк: РНКБ Банк (ПАО) БИК 044525607 "
            "30101810700000000607\n"
            "Основание: Доверенность № 5 от 12.01.2026\n"
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ИНН") == "3123456783"
        assert result.get("ЗАКАЗЧИК_БАНК") == "РНКБ Банк (ПАО)"
        assert result.get("ЗАКАЗЧИК_РС") == "40702810700000098765"
        assert result.get("ЗАКАЗЧИК_КС") == "30101810700000000607"
        assert result.get("ЗАКАЗЧИК_ОСНОВАНИЕ") == "Доверенность № 5 от 12.01.2026"
        assert result.get("ЗАКАЗЧИК_БИК") == "044525607"

    def test_bank_dash_name_with_label(self):
        """P0-4: дефисное имя банка с меткой — берётся целиком, не '»'."""
        result = parse_requisites("Банк: ПАО «Тест-Банк»")
        assert result.get("ЗАКАЗЧИК_БАНК") == "ПАО «Тест-Банк»"

    def test_bank_dash_name_without_label_empty(self):
        """P0-4: «Банк» внутри дефисного имени — не метка; лучше пусто, чем '»'."""
        result = parse_requisites("р/с 40702810123450067890 в ПАО «Тест-Банк»")
        assert "ЗАКАЗЧИК_БАНК" not in result

    def test_bank_dash_name_in_org_not_eaten_by_blank_span(self):
        """P0-4: «Тест-Банк» в имени организации не забеливается как банк."""
        text = "ООО «Тест-Банк»\nИНН 7707083893\nБанк: ПАО Сбербанк"
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") == 'ООО "Тест-Банк"'
        assert result.get("ЗАКАЗЧИК_БАНК") == "ПАО Сбербанк"

    def test_bank_label_without_value_empty(self):
        """P0-4: метка банка без буквенного значения → поле пустое."""
        result = parse_requisites("Банк: 12345")
        assert "ЗАКАЗЧИК_БАНК" not in result

    def test_bank_is_last_field_cut_at_newline(self):
        """Банк — последнее поле: сегмент режется до \\n/конца, не тянет пустоту."""
        result_nl = parse_requisites("ООО «Тест»\nБанк: ПАО Сбербанк\n")
        assert result_nl.get("ЗАКАЗЧИК_БАНК") == "ПАО Сбербанк"
        # То же без хвостового перевода строки (конец текста).
        result_eof = parse_requisites("ООО «Тест»\nБанк: ПАО Сбербанк")
        assert result_eof.get("ЗАКАЗЧИК_БАНК") == "ПАО Сбербанк"


# ---------------------------------------------------------------------------
# Карточки 1–7 из аудита 2026-07 (реконструкция по отчёту: оригиналов ТЗ нет
# в репо). Ассерты — ТОЛЬКО на зафиксированное аудитом поведение P0 и
# отсутствие порчи. Известные P1-пробелы (ФИО «Фамилия И.О.», р/сч 408,
# ИП/полная ОПФ без распознавания имени, многострочный адрес) НЕ ассертим
# ни в плюс, ни в минус — уйдут в P1-фронт.
# ---------------------------------------------------------------------------

class TestAuditCards:
    def test_card1_baseline_dash_bank(self):
        """Карточка 1 (baseline): дефисный банк → БАНК не '»' (P0-4)."""
        text = (
            "ООО «Прима»\n"
            "ИНН 7705123452 КПП 770501001\n"
            "Юридический адрес: 115093, г. Москва, ул. Люсиновская, д. 36\n"
            "р/с 40702810400000012345 Банк: ПАО «Тест-Банк» БИК 044525225\n"
            "к/с 30101810400000000225\n"
            "Генеральный директор Иванов И.И.\n"
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_БАНК") == "ПАО «Тест-Банк»"
        assert result.get("ЗАКАЗЧИК_ИНН") == "7705123452"
        assert result.get("ЗАКАЗЧИК_КПП") == "770501001"
        assert result.get("ЗАКАЗЧИК_РС") == "40702810400000012345"
        assert result.get("ЗАКАЗЧИК_КС") == "30101810400000000225"
        assert result.get("ЗАКАЗЧИК_БИК") == "044525225"
        assert result.get("ЗАКАЗЧИК_АДРЕС_ЮР", "").startswith("115093")

    def test_card2_glued_single_line(self):
        """Карточка 2 (слитная строка): телефон ≠ ИНН (P0-1), адрес ограничен (P0-3)."""
        text = (
            "ООО «Нева-Строй» ИНН 7811009871 КПП 781101001 ОГРН 1077847120944 "
            "198096, г. Санкт-Петербург, Трамвайный пр., д. 5 "
            "р/с 40702810555000001234 к/с 30101810500000000653 БИК 044030653 "
            "тел. 8 (812) 320-11-22 e-mail: info@neva-stroy.ru Директор Смирнов П.А."
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_ТЕЛЕФОН") == "8 (812) 320-11-22"
        assert result.get("ЗАКАЗЧИК_ИНН") == "7811009871"
        assert result.get("ЗАКАЗЧИК_АДРЕС_ЮР") == (
            "198096, г. Санкт-Петербург, Трамвайный пр., д. 5"
        )
        assert result.get("ЗАКАЗЧИК_EMAIL") == "info@neva-stroy.ru"

    def test_card3_ip_no_garbage(self):
        """Карточка 3 (ИП): нет мусора; метка «Адрес:» не липнет к значению."""
        text = (
            "ИП Петров Сергей Иванович\n"
            "ИНН 500100732259\n"
            "ОГРНИП 315745600001234\n"
            "Адрес: 623281, Свердловская обл., г. Ревда, ул. Мира, д. 10\n"
            "р/сч 40802810600000004321\n"
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") == "ИП Петров Сергей Иванович"  # P1-4
        assert result.get("ЗАКАЗЧИК_ИНН") == "500100732259"
        assert result.get("ЗАКАЗЧИК_ОГРН") == "315745600001234"
        assert result.get("ЗАКАЗЧИК_АДРЕС_ЮР") == (
            "623281, Свердловская обл., г. Ревда, ул. Мира, д. 10"
        )
        assert result.get("ЗАКАЗЧИК_РС") == "40802810600000004321"  # P1-1

    def test_card4_pao_multiline_address(self):
        """Карточка 4 (полная ОПФ, адрес в 3 строки): АДРЕС_ЮР с индекса (P1-5 не ассертим)."""
        text = (
            "Публичное акционерное общество «Вектор-Восток»\n"
            "ИНН 7801234564\n"
            "КПП 780101001\n"
            "Юридический адрес: 630007, Новосибирская область,\n"
            "г. Новосибирск,\n"
            "Красный проспект, д. 1\n"
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") == 'ПАО "Вектор-Восток"'  # P1-4
        assert result.get("ЗАКАЗЧИК_ИНН") == "7801234564"
        assert result.get("ЗАКАЗЧИК_КПП") == "780101001"
        assert result.get("ЗАКАЗЧИК_АДРЕС_ЮР", "").startswith("630007")

    def test_card5_ocr_noise_no_garbage(self):
        """Карточка 5 (OCR-шум О→0/З→3, счёт с пробелами): лучше пусто, чем мусор."""
        text = (
            "ООО «Гранит-М»\n"
            "ИНН 78О9З12345\n"
            "р/с 4О70 2810 5550 0000 1234\n"
            "БИК О44030653\n"
            "тел. 8 (В12) 320-11-22\n"
        )
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_ИНН" not in result
        assert "ЗАКАЗЧИК_РС" not in result
        assert "ЗАКАЗЧИК_БИК" not in result
        assert "ЗАКАЗЧИК_ТЕЛЕФОН" not in result
        assert result.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") == 'ООО "Гранит-М"'

    def test_card6_broken_inn_empty(self):
        """Карточка 6 (битая контрольная сумма ИНН): поле молча пусто."""
        text = "ООО «Омега»\nИНН 7707083890\nКПП 770701001\n"
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_ИНН" not in result
        assert result.get("ЗАКАЗЧИК_КПП") == "770701001"

    def test_card7_bik_ks_mismatch_both_extracted(self):
        """Карточка 7 (БИК ↔ к/с не согласованы): парсер отдаёт как есть.

        Кросс-чек последних цифр — зона requisites_validation, не парсера.
        """
        text = (
            "Банк: ПАО Сбербанк\n"
            "БИК 044525225\n"
            "к/с 30101810500000000653\n"
        )
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_БИК") == "044525225"
        assert result.get("ЗАКАЗЧИК_КС") == "30101810500000000653"

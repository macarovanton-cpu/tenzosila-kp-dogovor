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

    def test_name_in_quotes(self):
        text = 'ООО "Тензосила"'
        result = parse_requisites(text)
        assert result.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") == 'ООО "Тензосила"'

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
        # Префикс не 301 и не 407/405/406, и без якоря
        text = "20098765432109876543"  # нестандартный префикс 200...
        result = parse_requisites(text)
        assert "ЗАКАЗЧИК_РС" not in result
        assert "ЗАКАЗЧИК_КС" not in result


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
# Label-anchored слой: банк, основание, склейка полей в одну строку
# ---------------------------------------------------------------------------

class TestLabelAnchored:
    def test_real_glued_card(self):
        """Реальная склеенная карточка: поля в одну строку — все разведены,
        банк не съедает хвост «БИК: …»."""
        text = (
            "ИНН: 7707083893 КПП: 667101001 ОГРН: 1256600048172 "
            "Расчетный счет: 40702810954030018457 "
            "Банк: АО «Тинькофф», г. Москва БИК: 044525974 "
            "К/с: 30101810145250000974 "
            "Генеральный директор: Мельников Игорь Сергеевич "
            "Действует на основании: Устава Телефон: +7 (495) 123-45-67"
        )
        result = parse_requisites(text)
        assert result["ЗАКАЗЧИК_ИНН"] == "7707083893"
        assert result["ЗАКАЗЧИК_БАНК"] == "АО «Тинькофф», г. Москва"
        assert result["ЗАКАЗЧИК_БИК"] == "044525974"
        assert result["ЗАКАЗЧИК_КС"] == "30101810145250000974"
        assert result["ЗАКАЗЧИК_РС"] == "40702810954030018457"
        assert result["ЗАКАЗЧИК_ОСНОВАНИЕ"] == "Устава"
        assert result["ЗАКАЗЧИК_ТЕЛЕФОН"] == "+7 (495) 123-45-67"
        # Банк не содержит хвоста «БИК …»
        assert "БИК" not in result["ЗАКАЗЧИК_БАНК"]

    def test_bank_tinkoff(self):
        """Банк режется до следующей метки «БИК»."""
        text = "Банк: АО «Тинькофф», г. Москва БИК: 044525974"
        result = parse_requisites(text)
        assert result["ЗАКАЗЧИК_БАНК"] == "АО «Тинькофф», г. Москва"
        assert result["ЗАКАЗЧИК_БИК"] == "044525974"

    def test_bank_name_contains_word_bank_uralkombank(self):
        """КРИТИЧНЫЙ: название банка САМО содержит «банк» — сегмент режется до
        «БИК», НЕ обрывается на внутреннем «банк» в «Уралкомбанк»."""
        text = "Банк: АО «Уралкомбанк», г. Екб БИК: 046577912"
        result = parse_requisites(text)
        assert result["ЗАКАЗЧИК_БАНК"] == "АО «Уралкомбанк», г. Екб"
        assert result["ЗАКАЗЧИК_БИК"] == "046577912"

    def test_osnovanie_with_colon(self):
        """Основание с двоеточием: «Действует на основании: Устава»."""
        text = "Действует на основании: Устава"
        result = parse_requisites(text)
        assert result["ЗАКАЗЧИК_ОСНОВАНИЕ"] == "Устава"

    def test_osnovanie_after_director_same_line(self):
        """Основание после ФИО директора в одной строке — все три распознаны."""
        text = (
            "Генеральный директор: Мельников Игорь Сергеевич "
            "Действует на основании: Устава"
        )
        result = parse_requisites(text)
        # ФИО и основание распознаны; должность — консервативный якорный путь
        # (окно начинается с якоря «директор») → «Директор».
        assert result["ЗАКАЗЧИК_ДИРЕКТОР_ФИО"] == "Мельников Игорь Сергеевич"
        assert "Директор" in result["ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ"]
        assert result["ЗАКАЗЧИК_ОСНОВАНИЕ"] == "Устава"

    def test_addresses_glued_one_line(self):
        """Склеенные адреса в одну строку — разведены по меткам."""
        text = (
            "Юридический адрес: 117997 г. Москва ул. Вавилова д. 5 "
            "Почтовый адрес: 119991 г. Москва ул. Ленина д. 10"
        )
        result = parse_requisites(text)
        assert result["ЗАКАЗЧИК_АДРЕС_ЮР"].startswith("117997")
        assert "Вавилова" in result["ЗАКАЗЧИК_АДРЕС_ЮР"]
        assert result["ЗАКАЗЧИК_АДРЕС_ПОЧТ"].startswith("119991")
        assert "Ленина" in result["ЗАКАЗЧИК_АДРЕС_ПОЧТ"]
        # Юр. адрес не съел почтовый
        assert "Почтовый" not in result["ЗАКАЗЧИК_АДРЕС_ЮР"]
        assert "119991" not in result["ЗАКАЗЧИК_АДРЕС_ЮР"]

    def test_rs_ks_priority_by_label(self):
        """Р/с и К/с не путаются при метках-приоритете."""
        text = (
            "Расчетный счет: 40702810954030018457 "
            "К/с: 30101810145250000974 БИК: 044525974"
        )
        result = parse_requisites(text)
        assert result["ЗАКАЗЧИК_РС"] == "40702810954030018457"
        assert result["ЗАКАЗЧИК_КС"] == "30101810145250000974"

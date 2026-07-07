"""Тесты validate_requisites()."""
from __future__ import annotations

from src.contracts.requisites_parser import parse_requisites
from src.contracts.requisites_transforms import derive_requisites
from src.contracts.requisites_validation import validate_requisites


def _parse_and_validate(text: str) -> tuple[dict, list[str], list[str]]:
    """Повторить флоу «Распознать»: parse → derive → validate merged dict."""
    parsed = parse_requisites(text)
    derived, _ = derive_requisites(parsed)
    full = {**parsed, **derived}
    errors, warnings = validate_requisites(full)
    return full, errors, warnings


def _valid_fields() -> dict[str, str]:
    """Полностью валидный набор реквизитов — ни errors, ни warnings."""
    return {
        "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": "ООО «Ромашка»",
        "ЗАКАЗЧИК_ИНН": "7707083893",
        "ЗАКАЗЧИК_КПП": "770701001",
        "ЗАКАЗЧИК_ОГРН": "1027700132195",
        "ЗАКАЗЧИК_АДРЕС_ЮР": "117312, г. Москва, ул. Вавилова, д. 19",
        "ЗАКАЗЧИК_РС": "40702810900000012345",
        "ЗАКАЗЧИК_БАНК": "ПАО Сбербанк",
        "ЗАКАЗЧИК_КС": "30101810400000000225",
        "ЗАКАЗЧИК_БИК": "044525225",
        "ЗАКАЗЧИК_ДИРЕКТОР_ФИО": "Иванов Иван Иванович",
        "ЗАКАЗЧИК_ОСНОВАНИЕ": "Устава",
    }


def test_valid_fields_clean():
    errors, warnings = validate_requisites(_valid_fields())
    assert errors == []
    assert warnings == []


def test_empty_name_blocks():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ"] = "   "
    errors, _ = validate_requisites(fields)
    assert any("наименование" in e for e in errors)


def test_empty_inn_blocks():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_ИНН"] = ""
    errors, _ = validate_requisites(fields)
    assert any("ИНН" in e and "заполнен" in e for e in errors)


def test_empty_rs_blocks():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_РС"] = ""
    errors, _ = validate_requisites(fields)
    assert any("расчётный счёт" in e.lower() for e in errors)


def test_broken_inn_checksum_blocks():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_ИНН"] = "7707083894"  # последняя цифра бита
    errors, _ = validate_requisites(fields)
    assert any("контрольн" in e for e in errors)


def test_inn_non_digits_blocks():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_ИНН"] = "77070838ab"
    errors, _ = validate_requisites(fields)
    assert any("контрольн" in e for e in errors)


def test_rs_wrong_length_blocks():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_РС"] = "4070281090000001234"  # 19 цифр
    errors, _ = validate_requisites(fields)
    assert any("Расчётный счёт" in e and "20" in e for e in errors)


def test_ks_wrong_length_blocks():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_КС"] = "3010181040000000022"  # 19 цифр
    errors, _ = validate_requisites(fields)
    assert any("Корреспондентский счёт" in e and "20" in e for e in errors)


def test_bik_wrong_length_blocks():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_БИК"] = "04452522"  # 8 цифр
    errors, _ = validate_requisites(fields)
    assert any("БИК" in e and "9" in e for e in errors)


def test_empty_bik_warns():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_БИК"] = ""
    errors, warnings = validate_requisites(fields)
    assert errors == []
    assert any("БИК" in w for w in warnings)


def test_empty_bank_warns():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_БАНК"] = ""
    _, warnings = validate_requisites(fields)
    assert any("банк" in w for w in warnings)


def test_empty_address_warns():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_АДРЕС_ЮР"] = ""
    _, warnings = validate_requisites(fields)
    assert any("юридический адрес" in w for w in warnings)


def test_empty_director_fio_warns():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_ДИРЕКТОР_ФИО"] = ""
    _, warnings = validate_requisites(fields)
    assert any("ФИО" in w for w in warnings)


def test_empty_osnovanie_warns():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_ОСНОВАНИЕ"] = ""
    _, warnings = validate_requisites(fields)
    assert any("основание" in w for w in warnings)


def test_ip_fields_clean():
    """ИП: 12-значный ИНН + ОГРНИП 15 знаков, без КПП — чисто."""
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ"] = "ИП Петров Сергей Иванович"
    fields["ЗАКАЗЧИК_ИНН"] = "500100732259"
    fields["ЗАКАЗЧИК_ОГРН"] = "304500116000157"
    fields["ЗАКАЗЧИК_КПП"] = ""
    errors, warnings = validate_requisites(fields)
    assert errors == []
    assert warnings == []


def test_broken_ogrn13_blocks():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_ОГРН"] = "1027700132196"  # контрольная цифра бита
    errors, _ = validate_requisites(fields)
    assert any("ОГРН" in e and "контрольн" in e for e in errors)


def test_broken_ogrnip15_blocks():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_ИНН"] = "500100732259"
    fields["ЗАКАЗЧИК_ОГРН"] = "304500116000158"  # контрольная цифра бита
    errors, _ = validate_requisites(fields)
    assert any("ОГРН" in e and "контрольн" in e for e in errors)


def test_ogrn_wrong_length_blocks():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_ОГРН"] = "10277001321"  # 11 цифр
    errors, _ = validate_requisites(fields)
    assert any("ОГРН" in e for e in errors)


def test_bik_ks_mismatch_blocks():
    """P0-5: рассинхрон БИК ↔ к/с (последние 3 цифры)."""
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_КС"] = "30101810400000000653"  # …653 при БИК …225
    errors, _ = validate_requisites(fields)
    assert any("БИК" in e and "согласован" in e for e in errors)


def test_bik_ks_mismatch_not_doubled_on_bad_length():
    """Кривая длина к/с даёт error длины, но не сверку БИК↔к/с."""
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_КС"] = "301018104000000006"  # 18 цифр
    errors, _ = validate_requisites(fields)
    assert not any("согласован" in e for e in errors)


def test_inn10_ogrnip15_warns():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_ОГРН"] = "304500116000157"  # ОГРНИП при ИНН юрлица
    errors, warnings = validate_requisites(fields)
    assert errors == []
    assert any("форму контрагента" in w for w in warnings)


def test_inn12_ogrn13_warns():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_ИНН"] = "500100732259"  # ИНН ИП при ОГРН юрлица
    errors, warnings = validate_requisites(fields)
    assert errors == []
    assert any("форму контрагента" in w for w in warnings)


def test_kpp_wrong_length_warns():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_КПП"] = "77070100"  # 8 знаков
    errors, warnings = validate_requisites(fields)
    assert errors == []
    assert any("КПП" in w for w in warnings)


def test_kpp_bad_reason_code_warns():
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_КПП"] = "7707ab001"  # строчные буквы в коде причины
    _, warnings = validate_requisites(fields)
    assert any("КПП" in w for w in warnings)


def test_kpp_letter_reason_code_clean():
    """Заглавные латинские буквы в позициях 5-6 допустимы (крупнейшие н/п)."""
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_КПП"] = "7707AB001"
    errors, warnings = validate_requisites(fields)
    assert errors == []
    assert warnings == []


def test_empty_kpp_ogrn_phone_silent():
    """Пустые КПП/ОГРН/телефон/email — молча, не критично для договора."""
    fields = _valid_fields()
    fields["ЗАКАЗЧИК_КПП"] = ""
    fields["ЗАКАЗЧИК_ОГРН"] = ""
    fields["ЗАКАЗЧИК_ТЕЛЕФОН"] = ""
    fields["ЗАКАЗЧИК_EMAIL"] = ""
    errors, warnings = validate_requisites(fields)
    assert errors == []
    assert warnings == []


# ---------------------------------------------------------------------------
# Интеграция parse → derive → validate: синтетические карточки с семантикой
# примеров 1-4 ТЗ (чистые) и 6-7 (битые). Контрольные суммы валидные,
# формат — тот, который парсер надёжно берёт (метки, ОПФ+кавычки, полное ФИО).
# ---------------------------------------------------------------------------

class TestSyntheticCards:
    def test_clean_card_full_jurlico(self):
        """Полное юрлицо — все критичные поля распознаны, чисто."""
        text = (
            "ООО «Ромашка»\n"
            "ИНН 7707083893\n"
            "КПП: 770701001\n"
            "ОГРН 1027700132195\n"
            "Юридический адрес: 117312, г. Москва, ул. Вавилова, д. 19\n"
            "р/с 40702810900000012345 в Банк ПАО «Сбербанк», г. Москва "
            "к/с 30101810400000000225 БИК 044525225\n"
            "Директор Иванов Иван Иванович, действует на основании Устава\n"
        )
        _, errors, warnings = _parse_and_validate(text)
        assert errors == []
        assert warnings == []

    def test_clean_card_unlabeled_accounts(self):
        """Счета без меток (по префиксу), длинное основание — errors пусты."""
        text = (
            "ООО «Гранит»\n"
            "ИНН 3123456783\n"
            "Юридический адрес: 308000, г. Белгород, пр. Славы, д. 35\n"
            "40702810700000098765 Банк: РНКБ Банк (ПАО) БИК 044525607 "
            "30101810700000000607\n"
            "Директор Кузнецов Андрей Викторович\n"
            "Основание: Доверенность № 5 от 12.01.2026\n"
        )
        _, errors, _ = _parse_and_validate(text)
        assert errors == []

    def test_clean_card_labeled_bank(self):
        """Юрлицо с меткой «Банк:» — errors пусты."""
        text = (
            "ПАО «Вектор»\n"
            "ИНН 7801234564\n"
            "Юридический адрес: 190000, г. Санкт-Петербург, Невский пр., д. 1\n"
            "р/с 40702810500000011111\n"
            "Банк: ПАО «Банк «Санкт-Петербург»\n"
            "к/с 30101810500000000207 БИК 046015207\n"
            "Директор Смирнова Ольга Петровна, действует на основании Устава\n"
        )
        _, errors, _ = _parse_and_validate(text)
        assert errors == []

    def test_ip_card_name_recognized_no_errors(self):
        """ИП без кавычек: после P1-4 наименование распознаётся парсером,
        валидатор ошибок не даёт (раньше пропуск закрывался ручным вводом)."""
        text = (
            "ИП Сидорова Анна Андреевна\n"
            "ИНН 500100732259\n"
            "ОГРНИП 304500116000157\n"
            "Юридический адрес: 141002, г. Мытищи, ул. Мира, д. 7\n"
            "р/с 40802810900000054321\n"
            "Банк: АО «Альфа-Банк» к/с 30101810200000000593 БИК 044525593\n"
            "действует на основании Свидетельства\n"
        )
        full, errors, _ = _parse_and_validate(text)
        assert full.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") == "ИП Сидорова Анна Андреевна"
        assert errors == []

    def test_broken_inn_card_is_loud(self):
        """Аналог примера 6: битый ИНН парсер отбрасывает → поле пусто →
        error «не заполнен» — тихий отказ стал громким."""
        text = (
            "ООО «Ромашка»\n"
            "ИНН 7707083894\n"  # контрольная сумма бита
            "р/с 40702810900000012345 Банк: ПАО Сбербанк "
            "к/с 30101810400000000225 БИК 044525225\n"
        )
        full, errors, _ = _parse_and_validate(text)
        assert not full.get("ЗАКАЗЧИК_ИНН")
        assert any("ИНН" in e for e in errors)

    def test_bik_ks_mismatch_card_is_loud(self):
        """Аналог примера 7: БИК и к/с из разных банков → error (P0-5)."""
        text = (
            "ООО «Ромашка»\n"
            "ИНН 7707083893\n"
            "р/с 40702810900000012345 Банк: ПАО Сбербанк "
            "к/с 30101810800000000653 БИК 044525225\n"  # …653 при БИК …225
        )
        full, errors, _ = _parse_and_validate(text)
        assert full.get("ЗАКАЗЧИК_КС") == "30101810800000000653"
        assert full.get("ЗАКАЗЧИК_БИК") == "044525225"
        assert any("согласован" in e for e in errors)

    def test_broken_ogrn_card_is_loud(self):
        """Битый ОГРН парсер принимает (длина совпала) → валидатор ловит."""
        text = (
            "ООО «Ромашка»\n"
            "ИНН 7707083893\n"
            "ОГРН 1027700132196\n"  # контрольная цифра бита
            "р/с 40702810900000012345 Банк: ПАО Сбербанк "
            "к/с 30101810400000000225 БИК 044525225\n"
        )
        full, errors, _ = _parse_and_validate(text)
        assert full.get("ЗАКАЗЧИК_ОГРН") == "1027700132196"
        assert any("ОГРН" in e for e in errors)

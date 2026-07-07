"""Тесты validate_requisites()."""
from __future__ import annotations

from src.contracts.requisites_validation import validate_requisites


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

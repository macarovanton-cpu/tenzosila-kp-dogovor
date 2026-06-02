"""Тесты форматтера PaymentLine."""

import pytest

from src.contracts.payment_line import (
    PaymentLine,
    PaymentTrigger,
    format_payment_line,
)


# ---------------------------------------------------------------------------
# Фундамент + монтаж (Автовесы_фундамент_монтаж_gemini.md, пп. 2.1–2.5)
# ---------------------------------------------------------------------------

def test_fundament_2_1_predoplata_vesy_i_fundament():
    line = PaymentLine(
        kind="предоплата",
        share_pct=50.0,
        share_prep="от стоимости",
        share_object="Весов и фундамента Весов",
        amount=1_335_000,
        trigger=PaymentTrigger.SPEC_SIGNED,
        due=5,
        due_unit="банковских",
    )
    expected = (
        "1. Предоплата 50% от стоимости Весов и фундамента Весов в размере "
        "1 335 000 (один миллион триста тридцать пять тысяч) рублей, "
        "в т.ч. НДС 22%, в течение 5 (пяти) банковских дней "
        "с момента подписания настоящей Спецификации."
    )
    assert format_payment_line(line, 1) == expected


def test_fundament_2_2_doplata_fundament():
    line = PaymentLine(
        kind="доплата",
        share_pct=50.0,
        share_prep="от стоимости",
        share_object="фундамента Весов",
        amount=550_000,
        trigger=PaymentTrigger.FOUNDATION_ACT,
        due=5,
        due_unit="банковских",
    )
    expected = (
        "2. Доплата 50% от стоимости фундамента Весов в размере "
        "550 000 (пятьсот пятьдесят тысяч) рублей, "
        "в т.ч. НДС 22%, в течение 5 (пяти) банковских дней "
        "с момента подписания Акта выполненных работ по строительству фундамента."
    )
    assert format_payment_line(line, 2) == expected


def test_fundament_2_3_doplata_vesy_i_dostavka():
    line = PaymentLine(
        kind="доплата",
        share_pct=50.0,
        share_prep="от стоимости",
        share_object="Весов и доставки",
        amount=915_000,
        trigger=PaymentTrigger.SHIPMENT_READY,
        due=5,
        due_unit="банковских",
    )
    expected = (
        "3. Доплата 50% от стоимости Весов и доставки в размере "
        "915 000 (девятьсот пятнадцать тысяч) рублей, "
        "в т.ч. НДС 22%, в течение 5 (пяти) банковских дней "
        "с момента получения уведомления о готовности Весов к отгрузке."
    )
    assert format_payment_line(line, 3) == expected


def test_fundament_2_4_predoplata_montazh():
    line = PaymentLine(
        kind="предоплата",
        share_pct=50.0,
        share_prep="от стоимости",
        share_object="монтажных работ и поверки",
        amount=110_000,
        trigger=PaymentTrigger.BRIGADE_READY,
        due=5,
        due_unit="банковских",
    )
    expected = (
        "4. Предоплата 50% от стоимости монтажных работ и поверки в размере "
        "110 000 (сто десять тысяч) рублей, "
        "в т.ч. НДС 22%, в течение 5 (пяти) банковских дней "
        "с момента уведомления о готовности принять монтажную бригаду на месте монтажа."
    )
    assert format_payment_line(line, 4) == expected


def test_fundament_2_5_doplata_montazh():
    line = PaymentLine(
        kind="доплата",
        share_pct=50.0,
        share_prep="от стоимости",
        share_object="монтажных работ и поверки",
        amount=110_000,
        trigger=PaymentTrigger.WORK_ACT,
        due=5,
        due_unit="банковских",
    )
    expected = (
        "5. Доплата 50% от стоимости монтажных работ и поверки в размере "
        "110 000 (сто десять тысяч) рублей, "
        "в т.ч. НДС 22%, в течение 5 (пяти) банковских дней "
        "с момента подписания Акта выполненных работ по настоящей Спецификации."
    )
    assert format_payment_line(line, 5) == expected


# ---------------------------------------------------------------------------
# Рама (Автовесы_рама_монтаж_gemini.md, пп. 2.1 и 2.3)
# ---------------------------------------------------------------------------

def test_rama_2_1_flat_bez_protsenta():
    """Flat-кейс: share_pct=None — процент и предлог не печатаются."""
    line = PaymentLine(
        kind="предоплата",
        share_pct=None,
        share_prep=None,
        share_object="",
        amount=1_000_000,
        trigger=PaymentTrigger.SPEC_SIGNED,
        due=5,
        due_unit="банковских",
    )
    expected = (
        "1. Предоплата в размере "
        "1 000 000 (один миллион) рублей, "
        "в т.ч. НДС 22%, в течение 5 (пяти) банковских дней "
        "с момента подписания настоящей Спецификации."
    )
    assert format_payment_line(line, 1) == expected


def test_rama_2_3_za_montazh_i_poverku():
    """«50% за монтаж и поверку» — предлог «за», не «от стоимости»."""
    line = PaymentLine(
        kind="предоплата",
        share_pct=50.0,
        share_prep="за",
        share_object="монтаж и поверку",
        amount=75_000,
        trigger=PaymentTrigger.BRIGADE_READY,
        due=5,
        due_unit="банковских",
    )
    expected = (
        "2. Предоплата 50% за монтаж и поверку в размере "
        "75 000 (семьдесят пять тысяч) рублей, "
        "в т.ч. НДС 22%, в течение 5 (пяти) банковских дней "
        "с момента уведомления о готовности принять монтажную бригаду на месте монтажа."
    )
    assert format_payment_line(line, 2) == expected


# ---------------------------------------------------------------------------
# Пропись дней — все 6 допустимых значений
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("due,word", [
    (3,  "трёх"),
    (5,  "пяти"),
    (10, "десяти"),
    (14, "четырнадцати"),
    (20, "двадцати"),
    (30, "тридцати"),
])
def test_due_words_all_valid(due: int, word: str):
    line = PaymentLine(
        kind="предоплата",
        share_pct=None,
        share_prep=None,
        share_object="",
        amount=100_000,
        trigger=PaymentTrigger.SPEC_SIGNED,
        due=due,
    )
    result = format_payment_line(line, 1)
    assert f"({word})" in result


def test_due_invalid_raises():
    line = PaymentLine(
        kind="предоплата",
        share_pct=None,
        share_prep=None,
        share_object="",
        amount=100_000,
        trigger=PaymentTrigger.SPEC_SIGNED,
        due=7,
    )
    with pytest.raises(ValueError):
        format_payment_line(line, 1)

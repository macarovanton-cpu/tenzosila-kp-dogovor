"""Тесты форматтера PaymentLine."""

import pytest

from src.contracts.payment_line import (
    PaymentLine,
    PaymentTrigger,
    build_lines_from_snapshot,
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


# ---------------------------------------------------------------------------
# build_lines_from_snapshot — bridge snapshot.payment → list[PaymentLine]
# Суммы синтетические, проверка арифметики %×bucket_total.
# ---------------------------------------------------------------------------

def _item(item_key: str, payment_group: str | None, price: int, qty: int = 1) -> dict:
    return {
        "item_key": item_key,
        "payment_group": payment_group,
        "price": price,
        "qty": qty,
        "total": price * qty,
        "customer_side": False,
    }


def _split(scales=(50, 50), foundation=(50, 50), delivery=(0, 100), iv=(0, 100)) -> dict:
    return {
        "scales":                        {"prepay": scales[0],     "postpay": scales[1]},
        "foundation":                    {"prepay": foundation[0], "postpay": foundation[1]},
        "delivery":                      {"prepay": delivery[0],   "postpay": delivery[1]},
        "installation_and_verification": {"prepay": iv[0],         "postpay": iv[1]},
    }


def test_bridge_full_scenario():
    """scales+foundation+delivery+i&v (i&v 50/50) → 5 строк."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 2_000_000),
        _item("foundation_s_f_18", "foundation", 1_000_000),
        _item("delivery_default", "delivery", 200_000),
        _item("install_default", "installation_and_verification", 100_000),
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(iv=(50, 50)),
    }
    lines = build_lines_from_snapshot(payment, spec_items)
    assert len(lines) == 5

    l1, l2, l3, l4, l5 = lines
    # L1 — предоплата за весы + фундамент
    assert l1.kind == "предоплата"
    assert l1.trigger == PaymentTrigger.SPEC_SIGNED
    assert l1.share_object == "Весов и фундамента Весов"
    assert l1.amount == 1_500_000  # 50% от 2млн + 50% от 1млн
    # L2 — доплата за фундамент
    assert l2.kind == "доплата"
    assert l2.trigger == PaymentTrigger.FOUNDATION_ACT
    assert l2.share_object == "фундамента Весов"
    assert l2.amount == 500_000
    # L3 — доплата за весы + доставка
    assert l3.kind == "доплата"
    assert l3.trigger == PaymentTrigger.SHIPMENT_READY
    assert l3.share_object == "Весов и доставки"
    assert l3.amount == 1_200_000  # 50% от 2млн + 100% от 200к
    # L4 — предоплата монтажа
    assert l4.kind == "предоплата"
    assert l4.trigger == PaymentTrigger.BRIGADE_READY
    assert l4.share_object == "монтажных работ и поверки"
    assert l4.amount == 50_000
    # L5 — доплата монтажа
    assert l5.kind == "доплата"
    assert l5.trigger == PaymentTrigger.WORK_ACT
    assert l5.amount == 50_000

    assert all(ln.share_prep == "от стоимости" for ln in lines)
    assert all(ln.due == 5 for ln in lines)


def test_bridge_only_scales_uses_default_fallback():
    """Только весы, split_state пустой → fallback 50/50 → 2 строки."""
    spec_items = [_item("vesta-c-60-18", "scales", 1_000_000)]
    payment = {"preset_id": "split_by_items", "days": 5, "split_state": {}}
    lines = build_lines_from_snapshot(payment, spec_items)
    assert len(lines) == 2
    assert lines[0].kind == "предоплата"
    assert lines[0].trigger == PaymentTrigger.SPEC_SIGNED
    assert lines[0].share_object == "Весов"
    assert lines[0].amount == 500_000
    assert lines[1].kind == "доплата"
    assert lines[1].trigger == PaymentTrigger.SHIPMENT_READY
    assert lines[1].share_object == "Весов"
    assert lines[1].amount == 500_000


def test_bridge_scales_and_iv_no_foundation():
    """scales + i&v (50/50), без фундамента и доставки → 4 строки."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 1_000_000),
        _item("install_default", "installation_and_verification", 100_000),
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(iv=(50, 50)),
    }
    lines = build_lines_from_snapshot(payment, spec_items)
    assert len(lines) == 4
    assert [ln.trigger for ln in lines] == [
        PaymentTrigger.SPEC_SIGNED,
        PaymentTrigger.SHIPMENT_READY,
        PaymentTrigger.BRIGADE_READY,
        PaymentTrigger.WORK_ACT,
    ]
    assert all("фундамент" not in ln.share_object for ln in lines)
    assert all("доставк" not in ln.share_object for ln in lines)


@pytest.mark.parametrize("preset_id", [
    "v1_prepay_postpay",
    "v2_prepay_preship_postpay",
    "v3_postpay_only",
    "prepay_100",
    "custom",
])
def test_bridge_non_split_presets_return_empty(preset_id: str):
    spec_items = [_item("vesta-c-60-18", "scales", 1_000_000)]
    payment = {"preset_id": preset_id, "days": 5, "split_state": _split()}
    assert build_lines_from_snapshot(payment, spec_items) == []


def test_bridge_has_orion_in_object():
    """Позиция orion_* → объект L1 содержит «(включая ПАК ОРИОН)»."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 1_000_000),
        _item("orion_pak", "scales", 0),
    ]
    payment = {"preset_id": "split_by_items", "days": 5, "split_state": _split()}
    lines = build_lines_from_snapshot(payment, spec_items)
    assert lines[0].share_object == "Весов (включая ПАК ОРИОН)"


def test_bridge_prepay_zero_skips_prepay_line():
    """scales prepay=0 → строка предоплаты (SPEC_SIGNED) не создаётся."""
    spec_items = [_item("vesta-c-60-18", "scales", 1_000_000)]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(scales=(0, 100)),
    }
    lines = build_lines_from_snapshot(payment, spec_items)
    assert len(lines) == 1
    assert lines[0].kind == "доплата"
    assert lines[0].trigger == PaymentTrigger.SHIPMENT_READY
    assert all(ln.trigger != PaymentTrigger.SPEC_SIGNED for ln in lines)

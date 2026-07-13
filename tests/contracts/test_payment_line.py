"""Тесты форматтера PaymentLine."""

import pytest

from src.contracts.payment_line import (
    PaymentCoverageError,
    PaymentLine,
    PaymentTrigger,
    build_lines_from_snapshot,
    format_payment_line,
    orion_poles_without_foundation,
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
    (7,  "семи"),
    (10, "десяти"),
    (14, "четырнадцати"),
    (20, "двадцати"),
    (21, "двадцати одного"),
    (30, "тридцати"),
    (45, "сорока пяти"),
    (90, "девяноста"),
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


def test_due_any_day_no_error():
    """days=7 больше не бросает ValueError — любой день 0–90 валиден."""
    line = PaymentLine(
        kind="предоплата",
        share_pct=None,
        share_prep=None,
        share_object="",
        amount=100_000,
        trigger=PaymentTrigger.SPEC_SIGNED,
        due=7,
    )
    result = format_payment_line(line, 1)
    assert "(семи)" in result


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
    # L3 — доплата за весы + доставка (delivery дефолт 0/100 ≠ scales 50/50)
    assert l3.kind == "доплата"
    assert l3.trigger == PaymentTrigger.SHIPMENT_READY
    assert l3.share_object == "Весов и доставки"
    assert l3.amount == 1_200_000  # 50% от 2млн + 100% от 200к
    assert l3.share_pct is None     # защёлка: разные % → процент не печатается
    assert l3.share_prep is None
    # L4 — предоплата монтажа
    assert l4.kind == "предоплата"
    assert l4.trigger == PaymentTrigger.BRIGADE_READY
    assert l4.share_object == "монтажных работ и поверки"
    assert l4.amount == 50_000
    # L5 — доплата монтажа
    assert l5.kind == "доплата"
    assert l5.trigger == PaymentTrigger.WORK_ACT
    assert l5.amount == 50_000

    # L1/L2/L4/L5 — одинаковые проценты или одиночные бакеты → «от стоимости»
    assert all(ln.share_prep == "от стоимости" for ln in [l1, l2, l4, l5])
    assert all(ln.due == 5 for ln in lines)

    # base_amount — комбинированный итог бакетов строки
    assert l1.base_amount == 3_000_000  # весы 2млн + фундамент 1млн
    assert l2.base_amount == 1_000_000  # фундамент
    assert l3.base_amount == 2_200_000  # весы 2млн + доставка 200к
    assert l4.base_amount == 100_000    # монтаж+поверка
    assert l5.base_amount == 100_000


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


@pytest.mark.parametrize("preset_id", ["custom", "unknown_preset"])
def test_bridge_non_split_presets_return_empty(preset_id: str):
    """Только custom и неизвестные пресеты → []. v1/v2/v3/prepay_100 теперь возвращают строки."""
    spec_items = [_item("vesta-c-60-18", "scales", 1_000_000)]
    payment = {"preset_id": preset_id, "days": 5, "split_state": _split()}
    assert build_lines_from_snapshot(payment, spec_items) == []


# ---------------------------------------------------------------------------
# Не-split пресеты — v1 / v2 / v3 / prepay_100
# ---------------------------------------------------------------------------

def test_bridge_v1_default_50_50():
    """v1 prepay=50 → 2 строки; 50/50; SPEC_SIGNED/WORK_ACT; Σ == ИТОГО."""
    spec_items = [_item("vesta-c-60-18", "scales", 1_000_000)]
    payment = {"preset_id": "v1_prepay_postpay", "days": 5, "v1_prepay": 50}
    lines = build_lines_from_snapshot(payment, spec_items)
    assert len(lines) == 2
    l1, l2 = lines
    assert l1.kind == "предоплата"
    assert l1.share_pct == 50.0
    assert l1.share_prep == "от"
    assert l1.share_object == "общей цены договора"
    assert l1.trigger == PaymentTrigger.SPEC_SIGNED
    assert l1.amount == 500_000
    assert l2.kind == "доплата"
    assert l2.share_pct == 50.0
    assert l2.trigger == PaymentTrigger.WORK_ACT
    assert l2.amount == 500_000
    assert l1.amount + l2.amount == 1_000_000
    # не-split: база каждой строки = ИТОГО спецификации
    assert l1.base_amount == 1_000_000
    assert l2.base_amount == 1_000_000


def test_bridge_v1_custom_30_70():
    """v1 prepay=30 → суммы 300 000 / 700 000."""
    spec_items = [_item("vesta-c-60-18", "scales", 1_000_000)]
    payment = {"preset_id": "v1_prepay_postpay", "days": 5, "v1_prepay": 30}
    lines = build_lines_from_snapshot(payment, spec_items)
    assert len(lines) == 2
    assert lines[0].amount == 300_000
    assert lines[1].amount == 700_000
    assert lines[0].amount + lines[1].amount == 1_000_000


def test_bridge_v2_30_40_30():
    """v2 prepay=30 preship=40 → 3 строки; pct [30,40,30]; SPEC_SIGNED/SHIPMENT_READY/WORK_ACT; Σ == ИТОГО."""
    spec_items = [_item("vesta-c-60-18", "scales", 1_000_000)]
    payment = {
        "preset_id": "v2_prepay_preship_postpay",
        "days": 5,
        "v2_prepay": 30,
        "v2_preship": 40,
    }
    lines = build_lines_from_snapshot(payment, spec_items)
    assert len(lines) == 3
    l1, l2, l3 = lines
    assert [ln.share_pct for ln in lines] == [30.0, 40.0, 30.0]
    assert [ln.trigger for ln in lines] == [
        PaymentTrigger.SPEC_SIGNED,
        PaymentTrigger.SHIPMENT_READY,
        PaymentTrigger.WORK_ACT,
    ]
    assert [ln.kind for ln in lines] == ["предоплата", "доплата", "доплата"]
    assert l1.amount + l2.amount + l3.amount == 1_000_000


def test_bridge_v2_preship_zero_is_not_defaulted():
    """v2 preship=0 сохраняется как 0, а не подменяется дефолтом 40."""
    spec_items = [_item("vesta-c-60-18", "scales", 1_000_000)]
    payment = {
        "preset_id": "v2_prepay_preship_postpay",
        "days": 5,
        "v2_prepay": 30,
        "v2_preship": 0,
    }

    lines = build_lines_from_snapshot(payment, spec_items)

    assert len(lines) == 2
    assert [ln.share_pct for ln in lines] == [30.0, 70.0]
    assert [ln.trigger for ln in lines] == [
        PaymentTrigger.SPEC_SIGNED,
        PaymentTrigger.WORK_ACT,
    ]
    assert all(ln.trigger != PaymentTrigger.SHIPMENT_READY for ln in lines)
    assert sum(ln.amount for ln in lines) == 1_000_000


def test_bridge_v3_after_installation():
    """v3 after_installation → 1 строка; kind=оплата; trigger=WORK_ACT; due==v3_days; amount==ИТОГО."""
    spec_items = [_item("vesta-c-60-18", "scales", 1_200_000)]
    payment = {
        "preset_id": "v3_postpay_only",
        "v3_days": 15,
        "v3_trigger_id": "after_installation",
    }
    lines = build_lines_from_snapshot(payment, spec_items)
    assert len(lines) == 1
    ln = lines[0]
    assert ln.kind == "оплата"
    assert ln.share_pct == 100.0
    assert ln.trigger == PaymentTrigger.WORK_ACT
    assert ln.due == 15
    assert ln.amount == 1_200_000


def test_bridge_v3_after_delivery():
    """v3 after_delivery → trigger=DELIVERED."""
    spec_items = [_item("vesta-c-60-18", "scales", 500_000)]
    payment = {
        "preset_id": "v3_postpay_only",
        "v3_days": 30,
        "v3_trigger_id": "after_delivery",
    }
    lines = build_lines_from_snapshot(payment, spec_items)
    assert len(lines) == 1
    assert lines[0].trigger == PaymentTrigger.DELIVERED
    assert lines[0].amount == 500_000


def test_bridge_prepay_100():
    """prepay_100 → 1 строка; предоплата; pct=100; W7 — триггер с основанием «счёт»."""
    spec_items = [_item("vesta-c-60-18", "scales", 800_000)]
    payment = {"preset_id": "prepay_100", "days": 5}
    lines = build_lines_from_snapshot(payment, spec_items)
    assert len(lines) == 1
    ln = lines[0]
    assert ln.kind == "предоплата"
    assert ln.share_pct == 100.0
    assert ln.trigger == PaymentTrigger.SPEC_SIGNED_INVOICE
    assert ln.amount == 800_000
    text = format_payment_line(ln, 1)
    assert text.endswith(
        "с момента подписания настоящей Спецификации, "
        "на основании выставленного Поставщиком счёта."
    )


def test_bridge_non_split_remainder_exact():
    """Последняя строка добирает остаток — Σ точно равна ИТОГО при нецелом делении."""
    spec_items = [_item("vesta-c-60-18", "scales", 1_000_001)]
    payment = {"preset_id": "v1_prepay_postpay", "days": 5, "v1_prepay": 33}
    lines = build_lines_from_snapshot(payment, spec_items)
    assert len(lines) == 2
    assert lines[0].amount == 330_000      # round(1_000_001 × 33/100)
    assert lines[1].amount == 670_001      # остаток
    assert lines[0].amount + lines[1].amount == 1_000_001


def test_bridge_non_split_format_text():
    """format_payment_line для не-split строки читается «X% от общей цены договора»."""
    from src.contracts.payment_line import format_payment_line
    spec_items = [_item("vesta-c-60-18", "scales", 1_000_000)]
    payment = {"preset_id": "v1_prepay_postpay", "days": 5, "v1_prepay": 50}
    lines = build_lines_from_snapshot(payment, spec_items)
    text = format_payment_line(lines[0], 1)
    assert text.startswith("1. Предоплата 50% от общей цены договора в размере")
    assert "от общей цены договора" in text
    assert "от стоимости" not in text


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
    assert lines[0].kind == "оплата"  # W3: единичный платёж (только postpay) → «оплата»
    assert lines[0].trigger == PaymentTrigger.SHIPMENT_READY
    assert all(ln.trigger != PaymentTrigger.SPEC_SIGNED for ln in lines)


def test_bridge_split_foundation_prepay_survives_when_scales_prepay_zero():
    """Предоплата фундамента не теряется, если у весов prepay=0."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 1_000_000),
        _item("foundation_s_f_18", "foundation", 1_000_000),
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(scales=(0, 100), foundation=(50, 50)),
    }

    lines = build_lines_from_snapshot(payment, spec_items)
    l1 = next(ln for ln in lines if ln.trigger == PaymentTrigger.SPEC_SIGNED)

    assert l1.amount == 500_000
    assert l1.share_pct is None
    assert l1.share_prep is None
    assert "фундамента" in l1.share_object


def test_bridge_split_delivery_postpay_survives_when_scales_postpay_zero():
    """Доплата доставки не теряется, если у весов postpay=0."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 1_000_000),
        _item("delivery_default", "delivery", 200_000),
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(scales=(100, 0), delivery=(0, 100)),
    }

    lines = build_lines_from_snapshot(payment, spec_items)
    l3 = next(ln for ln in lines if ln.trigger == PaymentTrigger.SHIPMENT_READY)

    assert l3.amount == 200_000
    assert l3.share_pct is None
    assert l3.share_prep is None
    assert "доставк" in l3.share_object


# ---------------------------------------------------------------------------
# W9 — опоры/кабель-трассы ОРИОН и рама/пандусы называются в объекте
# ---------------------------------------------------------------------------

def test_bridge_w9_orion_poles_object_and_trigger():
    """orion_cable_poles → объект доплаты фундамента с опорами + расширенный триггер."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 2_000_000),
        _item("orion_standard", "scales", 500_000),
        _item("foundation_s_f_18", "foundation", 1_000_000),
        _item("orion_cable_poles", "foundation", 125_000),
    ]
    payment = {"preset_id": "split_by_items", "days": 5, "split_state": _split()}
    lines = build_lines_from_snapshot(payment, spec_items)
    l2 = next(ln for ln in lines if ln.trigger in
              (PaymentTrigger.FOUNDATION_ACT, PaymentTrigger.FOUNDATION_ACT_POLES))
    assert l2.trigger == PaymentTrigger.FOUNDATION_ACT_POLES
    assert l2.share_object == (
        "фундамента Весов и установку опор и кабель-трасс для ПАК ОРИОН"
    )
    assert l2.amount == 562_500  # 50% от (1 000 000 + 125 000)
    text = format_payment_line(l2, 2)
    assert text.endswith(
        "с момента подписания Акта выполненных работ по строительству "
        "фундамента и установке опор и кабель-трасс."
    )


def test_bridge_w9_no_poles_keeps_plain_foundation():
    """Без опор — обычный объект и обычный триггер FOUNDATION_ACT."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 2_000_000),
        _item("foundation_s_f_18", "foundation", 1_000_000),
    ]
    payment = {"preset_id": "split_by_items", "days": 5, "split_state": _split()}
    lines = build_lines_from_snapshot(payment, spec_items)
    l2 = next(ln for ln in lines if ln.share_object == "фундамента Весов")
    assert l2.trigger == PaymentTrigger.FOUNDATION_ACT


def test_bridge_rama_ramps_named_in_scales_object():
    """Рама + пандусы называются в объекте весов (L1 и L3)."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 800_000),
        _item("frame_18", "scales", 150_000),
        _item("ramp_set_4", "scales", 50_000),
        _item("delivery_default", "delivery", 100_000),
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(delivery=(0, 100)),  # доставка целиком по факту (страж A9)
    }
    lines = build_lines_from_snapshot(payment, spec_items)
    l1 = next(ln for ln in lines if ln.trigger == PaymentTrigger.SPEC_SIGNED)
    l3 = next(ln for ln in lines if ln.trigger == PaymentTrigger.SHIPMENT_READY)
    assert l1.share_object == "Весов, комплекта пандусов и рамы"
    assert l3.share_object == "Весов, комплекта пандусов, рамы и доставки"


def test_bridge_frame_only_no_ramps():
    """Только рама без пандусов → «Весов и рамы» (пандусы не упоминаются)."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 800_000),
        _item("frame_18", "scales", 150_000),
    ]
    payment = {"preset_id": "split_by_items", "days": 5, "split_state": _split()}
    lines = build_lines_from_snapshot(payment, spec_items)
    assert lines[0].share_object == "Весов и рамы"


# ---------------------------------------------------------------------------
# W6 — шеф-монтаж в объекте оплаты (installation_scope из снапшота КП)
# ---------------------------------------------------------------------------

def test_bridge_w6_shefmontazh_object():
    """installation_scope='shefmontazh' → «шеф-монтажных работ и поверки» в обеих фазах."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 1_000_000),
        _item("install_default", "installation_and_verification", 100_000),
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(iv=(50, 50)),
    }
    lines = build_lines_from_snapshot(
        payment, spec_items, installation_scope="shefmontazh"
    )
    iv_lines = [ln for ln in lines if ln.trigger in
                (PaymentTrigger.BRIGADE_READY, PaymentTrigger.WORK_ACT)]
    assert len(iv_lines) == 2
    assert all(ln.share_object == "шеф-монтажных работ и поверки" for ln in iv_lines)


def test_bridge_w6_default_scope_keeps_montazh():
    """Без scope (или full) — обычный объект «монтажных работ и поверки»."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 1_000_000),
        _item("install_default", "installation_and_verification", 100_000),
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(iv=(50, 50)),
    }
    for scope in (None, "full"):
        lines = build_lines_from_snapshot(
            payment, spec_items, installation_scope=scope
        )
        iv_lines = [ln for ln in lines if ln.trigger in
                    (PaymentTrigger.BRIGADE_READY, PaymentTrigger.WORK_ACT)]
        assert all(ln.share_object == "монтажных работ и поверки" for ln in iv_lines)


# ---------------------------------------------------------------------------
# P1 — процент в составных строках
# ---------------------------------------------------------------------------

def test_bridge_delivery_prepay_undershoots_raises():
    """A9: delivery 50/50 — фантомный prepay. Бакет доставки недобирается (движок
    читает только postpay), Σ строк не покрывает Σ бакетов → страж падает.

    Раньше тест `test_bridge_delivery_equal_pct_keeps_percent` ЗАКРЕПЛЯЛ баг:
    ассертил amount 1 100 000 (50%·2млн + 50%·200к) как норму. Теперь это
    нелегальное состояние: доставка платится целиком по факту, prepay у неё
    фантом (см. Слой 1 — поле read-only в UI).
    """
    spec_items = [
        _item("vesta-c-60-18", "scales", 2_000_000),
        _item("delivery_default", "delivery", 200_000),
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(delivery=(50, 50)),
    }
    with pytest.raises(PaymentCoverageError):
        build_lines_from_snapshot(payment, spec_items)


def test_bridge_delivery_default_covers_total():
    """Компаньон стража: delivery дефолт 0/100 → строки покрывают Σ бакетов,
    страж молчит. Защита от ложного срабатывания."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 2_000_000),
        _item("delivery_default", "delivery", 200_000),
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(),  # delivery 0/100
    }
    lines = build_lines_from_snapshot(payment, spec_items)
    assert sum(ln.amount for ln in lines) == 2_200_000  # 2млн весы + 200к доставка


def test_bridge_foundation_diff_pct_drops_percent():
    """foundation 70/30 ≠ scales 50/50 → L1 share_pct=None, сумма корректна."""
    spec_items = [
        _item("vesta-c-60-18", "scales", 2_000_000),
        _item("foundation_s_f_18", "foundation", 1_000_000),
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(foundation=(70, 30)),
    }
    lines = build_lines_from_snapshot(payment, spec_items)
    l1 = next(ln for ln in lines if ln.trigger == PaymentTrigger.SPEC_SIGNED)
    assert l1.share_pct is None
    assert l1.share_prep is None
    assert l1.amount == 1_700_000  # 50% от 2млн + 70% от 1млн


def test_bridge_format_flat_line():
    """L3 с разными процентами (delivery 0/100, scales 50/50) → flat-формат без %.

    W1 (печать 50% + объект в этой строке) отложена в Стадию 2 вместе с правкой
    пересчёта графика — см. комментарий в build_lines_from_snapshot (L3).
    """
    spec_items = [
        _item("vesta-c-60-18", "scales", 2_000_000),
        _item("delivery_default", "delivery", 200_000),
    ]
    payment = {
        "preset_id": "split_by_items",
        "days": 5,
        "split_state": _split(),  # delivery дефолт 0/100, scales 50/50
    }
    lines = build_lines_from_snapshot(payment, spec_items)
    l3 = next(ln for ln in lines if ln.trigger == PaymentTrigger.SHIPMENT_READY)
    text = format_payment_line(l3, 3)
    assert text.startswith("3. Доплата в размере 1 200 000")
    assert "от стоимости" not in text  # flat-формат: процент не печатается


# ---------------------------------------------------------------------------
# orion_poles_without_foundation — опоры ОРИОН без реального фундамента
# ---------------------------------------------------------------------------

def test_orion_poles_without_foundation_bare_poles():
    items = [{"id": "orion_poles", "payment_group": "foundation"}]
    assert orion_poles_without_foundation(items) is True


def test_orion_poles_without_foundation_with_real_foundation():
    items = [
        {"id": "foundation", "payment_group": "foundation"},
        {"id": "orion_poles", "payment_group": "foundation"},
    ]
    assert orion_poles_without_foundation(items) is False


def test_orion_poles_without_foundation_foundation_only():
    items = [{"id": "foundation", "payment_group": "foundation"}]
    assert orion_poles_without_foundation(items) is False


def test_orion_poles_without_foundation_neither():
    items = [{"id": "delivery", "payment_group": "delivery"}]
    assert orion_poles_without_foundation(items) is False

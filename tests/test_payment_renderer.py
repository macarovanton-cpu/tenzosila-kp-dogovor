"""Тесты render_payment_block: 6 пресетов (v1/v2/v3 + prepay_100 + split + custom).

Целевые формулировки — docs/PAYMENT_SPEC.md (эталон, формы 1–11):
«— <Название> <%> <база> <предлог+событие> (<N дней>).» + сноска
«Сроки указаны в банковских днях.» под блоком.
"""
from __future__ import annotations

from src.generators.payment_renderer import (
    FOOTNOTE,
    get_active_payment_groups,
    render_payment_block,
)


def _item(item_key: str, payment_group: str) -> dict:
    return {"item_key": item_key, "payment_group": payment_group, "qty": 1, "price": 100}


def _state(preset_id: str, **kwargs) -> dict:
    base = {
        "payment_preset_id": preset_id,
        "payment_split_state": {},
        "payment_percents": {},
        "payment_days": 5,
        "payment_custom_text": "",
        "payment_v1_prepay": 50,
        "payment_v2_prepay": 30,
        "payment_v2_preship": 40,
        "payment_v3_days": 15,
        "payment_v3_trigger_id": "after_installation",
    }
    base.update(kwargs)
    return base


def _lines(text: str) -> list[str]:
    """Строки платежей блока (без сноски и пустых строк)."""
    return [ln for ln in text.split("\n") if ln.startswith("— ")]


# --- get_active_payment_groups ---


def test_active_groups_only_scales():
    items = [_item("vesta-с-60-18", "scales")]
    a = get_active_payment_groups(items)
    assert a["groups"] == {
        "scales": True, "foundation": False,
        "delivery": False, "installation_and_verification": False,
    }
    assert a["has_orion"] is False


def test_active_groups_with_orion_flag():
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("orion_standard", "scales"),
    ]
    a = get_active_payment_groups(items)
    assert a["has_orion"] is True


def test_active_groups_full_set():
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("foundation_s_f_18", "foundation"),
        _item("delivery_default", "delivery"),
        _item("install_default", "installation_and_verification"),
    ]
    a = get_active_payment_groups(items)
    assert all(a["groups"].values())


# --- Сноска (эталон): под каждым сгенерированным блоком, кроме custom ---


def test_footnote_appended_to_all_generated_presets(payment_terms):
    for preset_id in (
        "split_by_items", "prepay_100", "v1_prepay_postpay",
        "v2_prepay_preship_postpay", "v3_postpay_only",
    ):
        items = [_item("vesta-с-60-18", "scales")]
        text = render_payment_block(_state(preset_id), items, payment_terms)
        assert text.endswith(f"\n\n{FOOTNOTE}"), f"{preset_id}: {text!r}"


# --- prepay_100 (форма 2 эталона; W3 — «Оплата», не «Предоплата») ---


def test_prepay_100(payment_terms):
    state = _state("prepay_100", payment_days=10)
    text = render_payment_block(state, [], payment_terms)
    assert _lines(text) == [
        "— Оплата 100% общей стоимости при подписании Договора (10 дней)."
    ]
    # Фраза «Производство начинается…» удалена целиком (реш. Антона).
    assert "Производство" not in text


def test_prepay_100_no_invoice_phrase_in_kp(payment_terms):
    """W7 — только full-регистр: фраза про счёт НЕ протекает в КП (lite)."""
    state = _state("prepay_100")
    text = render_payment_block(state, [], payment_terms)
    assert "счёта" not in text
    assert "счета" not in text


# --- Variant 1: Аванс + Постоплата (форма 3) ---


def test_v1_default_50_50(payment_terms):
    """Дефолтные значения: prepay=50, postpay=100−50=50, days=5."""
    state = _state("v1_prepay_postpay")
    text = render_payment_block(state, [], payment_terms)
    assert _lines(text) == [
        "— Предоплата 50% общей стоимости при подписании Договора (5 дней).",
        "— Доплата 50% общей стоимости по Акту выполненных работ (5 дней).",
    ]


def test_v1_custom_30_70(payment_terms):
    """Менеджер ввёл prepay=30 → postpay должен быть 70."""
    state = _state("v1_prepay_postpay", payment_v1_prepay=30)
    text = render_payment_block(state, [], payment_terms)
    assert "Предоплата 30% общей стоимости" in text
    assert "Доплата 70% общей стоимости" in text


def test_v1_extreme_99_1(payment_terms):
    """Граничный случай — 99/1."""
    state = _state("v1_prepay_postpay", payment_v1_prepay=99)
    text = render_payment_block(state, [], payment_terms)
    assert "Предоплата 99%" in text
    assert "Доплата 1%" in text


# --- Variant 2: Аванс + Перед отгрузкой + Постоплата (форма 4) ---


def test_v2_default_30_40_30(payment_terms):
    """Дефолт: prepay=30, preship=40, postpay=100−70=30. «Перед отгрузкой» —
    не название платежа (эталон): промежуточный платёж — «Доплата»."""
    state = _state("v2_prepay_preship_postpay")
    text = render_payment_block(state, [], payment_terms)
    assert _lines(text) == [
        "— Предоплата 30% общей стоимости при подписании Договора (5 дней).",
        "— Доплата 40% общей стоимости по готовности весов к отгрузке (5 дней).",
        "— Доплата 30% общей стоимости по Акту выполненных работ (5 дней).",
    ]


def test_v2_custom_10_30_60(payment_terms):
    """Менеджер ввёл prepay=10, preship=30 → postpay=60."""
    state = _state(
        "v2_prepay_preship_postpay",
        payment_v2_prepay=10, payment_v2_preship=30,
    )
    text = render_payment_block(state, [], payment_terms)
    assert "Предоплата 10%" in text
    assert "Доплата 30% общей стоимости по готовности весов к отгрузке" in text
    assert "Доплата 60% общей стоимости по Акту выполненных работ" in text


# --- Variant 3: 100% постоплата (форма 5) ---


def test_v3_default_15d_after_installation(payment_terms):
    """Дефолт: 15 дней, точка отсчёта — завершение монтажа."""
    state = _state("v3_postpay_only")
    text = render_payment_block(state, [], payment_terms)
    assert _lines(text) == [
        "— Оплата 100% общей стоимости по завершении монтажа (15 дней)."
    ]


def test_v3_custom_30d_after_act(payment_terms):
    """30 дней от Акта выполненных работ."""
    state = _state(
        "v3_postpay_only",
        payment_v3_days=30, payment_v3_trigger_id="after_act",
    )
    text = render_payment_block(state, [], payment_terms)
    assert "по Акту выполненных работ (30 дней)" in text


def test_v3_after_delivery(payment_terms):
    """trigger=after_delivery → «по поставке весов»."""
    state = _state(
        "v3_postpay_only", payment_v3_trigger_id="after_delivery",
    )
    text = render_payment_block(state, [], payment_terms)
    assert "по поставке весов" in text


# --- split_by_items: формы 1, 6–9 эталона ---


def test_split_base_scenario_matches_spec(payment_terms):
    """Базовый сценарий (весы+фундамент+доставка+монтаж+поверка) —
    дословно форма 1 PAYMENT_SPEC: хронология (фундамент раньше отгрузки),
    база в каждой строке, срок «(5 дней)», сноска под блоком."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("foundation_s_f_18", "foundation"),
        _item("delivery_default", "delivery"),
        _item("install_default", "installation_and_verification"),
        _item("verification_default", "installation_and_verification"),
    ]
    state = _state("split_by_items")
    text = render_payment_block(state, items, payment_terms)
    assert text == (
        "— Предоплата 50% стоимости весов и фундамента при подписании Договора (5 дней).\n"
        "— Доплата 50% стоимости фундамента по Акту строительства фундамента (5 дней).\n"
        "— Доплата 50% стоимости весов и доставки по готовности весов к отгрузке (5 дней).\n"
        "— Монтаж и поверка: предоплата 50% по готовности к монтажу, "
        "доплата 50% по Акту выполненных работ (5 дней).\n"
        "\n"
        "Сроки указаны в банковских днях."
    )


def test_split_full_set(payment_terms):
    """A: весы + ОРИОН + фундамент + доставка + монтаж/поверка → 4 строки."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("orion_standard", "scales"),
        _item("foundation_s_f_18", "foundation"),
        _item("delivery_default", "delivery"),
        _item("install_default", "installation_and_verification"),
        _item("verification_default", "installation_and_verification"),
    ]
    state = _state("split_by_items")
    lines = _lines(render_payment_block(state, items, payment_terms))
    assert len(lines) == 4
    assert "Предоплата 50%" in lines[0]
    assert "ПАК ОРИОН" in lines[0]
    assert "фундамента" in lines[0]
    assert lines[0].endswith("при подписании Договора (5 дней).")
    assert "Доплата 50% стоимости фундамента" in lines[1]
    assert lines[1].endswith("по Акту строительства фундамента (5 дней).")
    assert "Доплата 50% стоимости весов (включая ПАК ОРИОН) и доставки" in lines[2]
    assert lines[2].endswith("по готовности весов к отгрузке (5 дней).")
    assert "Монтаж и поверка" in lines[3]
    assert "по готовности к монтажу" in lines[3]
    assert lines[3].endswith("по Акту выполненных работ (5 дней).")


def test_split_only_scales(payment_terms):
    """B (форма 6): только весы → база «стоимости весов» в обеих строках
    (термин «проект» эталоном запрещён)."""
    items = [_item("vesta-с-60-18", "scales")]
    state = _state("split_by_items")
    text = render_payment_block(state, items, payment_terms)
    lines = _lines(text)
    assert lines == [
        "— Предоплата 50% стоимости весов при подписании Договора (5 дней).",
        "— Доплата 50% стоимости весов по готовности весов к отгрузке (5 дней).",
    ]
    assert "проект" not in text


def test_split_scales_plus_install(payment_terms):
    """C (формы 7/10): весы + монтаж (без поверки/фундамента/доставки) → 3 строки.

    Бакет iv = только монтаж → B11-объект «Монтаж» (без «и поверка»).
    """
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("install_default", "installation_and_verification"),
    ]
    state = _state("split_by_items")
    lines = _lines(render_payment_block(state, items, payment_terms))
    assert len(lines) == 3
    assert "Предоплата 50%" in lines[0]
    assert "Доплата 50% стоимости весов" in lines[1]
    assert "доставки" not in lines[1]
    assert lines[2].startswith("— Монтаж: предоплата 50%")
    assert "поверка" not in lines[2]


def test_split_scales_with_orion_no_others(payment_terms):
    """D: весы + ОРИОН без фундамента/доставки/монтажа → 2 строки,
    база с ПАК ОРИОН в обеих (эталон: база в каждой строке)."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("orion_standard", "scales"),
    ]
    state = _state("split_by_items")
    lines = _lines(render_payment_block(state, items, payment_terms))
    assert lines == [
        "— Предоплата 50% стоимости весов (включая ПАК ОРИОН) "
        "при подписании Договора (5 дней).",
        "— Доплата 50% стоимости весов (включая ПАК ОРИОН) "
        "по готовности весов к отгрузке (5 дней).",
    ]


def test_split_with_overrides(payment_terms):
    """split_by_items берёт проценты из state['payment_split_state']."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("foundation_s_f_18", "foundation"),
    ]
    state = _state(
        "split_by_items",
        payment_split_state={
            "scales": {"prepay": 70, "postpay": 30},
            "foundation": {"prepay": 40, "postpay": 60},
        },
    )
    text = render_payment_block(state, items, payment_terms)
    assert "70%" in text
    assert "40%" in text
    assert "30%" in text
    assert "60%" in text


def test_split_iv_single_phase_word_is_oplata(payment_terms):
    """W3: монтаж 0/100 → единичный платёж, слово «оплата», одна фаза в строке."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("install_default", "installation_and_verification"),
    ]
    state = _state(
        "split_by_items",
        payment_split_state={
            "installation_and_verification": {"prepay": 0, "postpay": 100},
        },
    )
    lines = _lines(render_payment_block(state, items, payment_terms))
    # Бакет iv = только монтаж (без поверки) → B11-объект «Монтаж».
    assert lines[-1] == "— Монтаж: оплата 100% по Акту выполненных работ (5 дней)."


def test_split_zero_prepay_skips_line(payment_terms):
    """W3: scales prepay=0 → строка предоплаты не печатается, доплата — «Оплата»
    (база печатается и здесь — эталон: база в каждой строке)."""
    items = [_item("vesta-с-60-18", "scales")]
    state = _state(
        "split_by_items",
        payment_split_state={"scales": {"prepay": 0, "postpay": 100}},
    )
    lines = _lines(render_payment_block(state, items, payment_terms))
    assert lines == [
        "— Оплата 100% стоимости весов по готовности весов к отгрузке (5 дней)."
    ]


def test_split_w9_orion_poles_object_and_trigger(payment_terms):
    """W9 lite: опоры ОРИОН — род. падеж в объекте («и установки опор»),
    триггер «по Акту строительства фундамента и установки опор»."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("orion_standard", "scales"),
        _item("foundation_s_f_18", "foundation"),
        _item("orion_cable_poles", "foundation"),
    ]
    state = _state("split_by_items")
    text = render_payment_block(state, items, payment_terms)
    f_line = next(ln for ln in _lines(text) if "фундамента" in ln and "Доплата" in ln)
    assert (
        "стоимости фундамента и установки опор и кабель-трасс для ПАК ОРИОН" in f_line
    )
    assert f_line.endswith(
        "по Акту строительства фундамента и установки опор (5 дней)."
    )


def test_split_rama_ramps_named(payment_terms):
    """Рама/пандусы называются в объекте весов (lite, род. падеж везде)."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("frame_18", "scales"),
        _item("ramp_set_4", "scales"),
        _item("delivery_default", "delivery"),
    ]
    state = _state("split_by_items")
    lines = _lines(render_payment_block(state, items, payment_terms))
    assert "50% стоимости весов, комплекта пандусов и рамы" in lines[0]
    assert (
        "Доплата 50% стоимости весов, комплекта пандусов, рамы и доставки"
        in lines[1]
    )


def test_split_shefmontazh_label(payment_terms):
    """W6: is_shefmontazh → строка монтажа получает шеф-префикс.

    Бакет iv = только монтаж (без поверки) → B11-объект «Шеф-монтаж».
    """
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("install_default", "installation_and_verification"),
    ]
    state = _state("split_by_items", is_shefmontazh=True)
    lines = _lines(render_payment_block(state, items, payment_terms))
    assert lines[-1].startswith("— Шеф-монтаж: предоплата 50%")
    assert "поверка" not in lines[-1]


def test_split_term_in_brackets_unit_in_footnote(payment_terms):
    """Эталон: срок печатается «(N дней)» в каждой строке; «в течение» нет,
    «банковских» — только в сноске."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("foundation_s_f_18", "foundation"),
    ]
    state = _state("split_by_items", payment_days=10)
    text = render_payment_block(state, items, payment_terms)
    for line in _lines(text):
        assert line.endswith("(10 дней)."), line
        assert "банковских" not in line
    assert "в течение" not in text
    assert text.endswith(FOOTNOTE)


def test_days_singular_agrees_in_brackets(payment_terms):
    """days=1 → «(1 день)», не «(1 дней)» (согласование в новом формате)."""
    items = [_item("vesta-с-60-18", "scales")]
    for preset_id in ("split_by_items", "prepay_100"):
        state = _state(preset_id, payment_days=1)
        text = render_payment_block(state, items, payment_terms)
        assert "(1 день)." in text, f"{preset_id}: {text!r}"
        assert "(1 дней)" not in text


# --- custom и edge ---


def test_custom_returns_custom_text(payment_terms):
    """Freeform — без сноски: менеджер сам управляет текстом целиком."""
    state = _state("custom", payment_custom_text="Свободный текст")
    text = render_payment_block(state, [], payment_terms)
    assert text == "Свободный текст"


def test_custom_empty_returns_dash(payment_terms):
    state = _state("custom", payment_custom_text="   ")
    text = render_payment_block(state, [], payment_terms)
    assert text == "—"


def test_unknown_preset_id_returns_dash(payment_terms):
    state = _state("nonexistent_preset_id")
    text = render_payment_block(state, [], payment_terms)
    assert text == "—"


# --- Маркер списка «— » расставляется вручную (1.5b-fix3) ---


def test_all_payment_lines_have_dash_prefix(payment_terms):
    """Каждая строка платежа начинается с «— » (docx-путь Listing);
    сноска и пустая строка перед ней — без маркера."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("foundation_s_f_18", "foundation"),
        _item("delivery_default", "delivery"),
        _item("install_default", "installation_and_verification"),
    ]
    for preset_id in (
        "split_by_items", "prepay_100", "v1_prepay_postpay",
        "v2_prepay_preship_postpay", "v3_postpay_only",
    ):
        state = _state(preset_id)
        text = render_payment_block(state, items, payment_terms)
        body = text.split(f"\n\n{FOOTNOTE}")[0]
        for line in body.split("\n"):
            assert line.startswith("— "), f"{preset_id}: missing dash prefix: {line!r}"

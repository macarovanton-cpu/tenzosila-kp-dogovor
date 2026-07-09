"""Тесты render_payment_block: 6 пресетов (v1/v2/v3 + prepay_100 + split + custom)."""
from __future__ import annotations

from src.generators.payment_renderer import (
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


# --- prepay_100 (единственный оставшийся «простой» пресет) ---


def test_prepay_100(payment_terms):
    state = _state("prepay_100", payment_days=10)
    text = render_payment_block(state, [], payment_terms)
    assert "100%" in text
    assert "10 банковских дней" in text


def test_prepay_100_no_invoice_phrase_in_kp(payment_terms):
    """W7 — только full-регистр: фраза про счёт НЕ протекает в КП (lite)."""
    state = _state("prepay_100")
    text = render_payment_block(state, [], payment_terms)
    assert "счёта" not in text
    assert "счета" not in text


# --- Variant 1: Аванс + Постоплата ---


def test_v1_default_50_50(payment_terms):
    """Дефолтные значения: prepay=50, postpay=100−50=50, days=5."""
    state = _state("v1_prepay_postpay")
    text = render_payment_block(state, [], payment_terms)
    assert "Предоплата: 50%" in text
    assert "Доплата: 50%" in text
    assert "5 банковских дней" in text


def test_v1_custom_30_70(payment_terms):
    """Менеджер ввёл prepay=30 → postpay должен быть 70."""
    state = _state("v1_prepay_postpay", payment_v1_prepay=30)
    text = render_payment_block(state, [], payment_terms)
    assert "Предоплата: 30%" in text
    assert "Доплата: 70%" in text


def test_v1_extreme_99_1(payment_terms):
    """Граничный случай — 99/1."""
    state = _state("v1_prepay_postpay", payment_v1_prepay=99)
    text = render_payment_block(state, [], payment_terms)
    assert "Предоплата: 99%" in text
    assert "Доплата: 1%" in text


# --- Variant 2: Аванс + Перед отгрузкой + Постоплата ---


def test_v2_default_30_40_30(payment_terms):
    """Дефолт: prepay=30, preship=40, postpay=100−70=30."""
    state = _state("v2_prepay_preship_postpay")
    text = render_payment_block(state, [], payment_terms)
    assert "Предоплата: 30%" in text
    assert "Перед отгрузкой: 40%" in text
    assert "Доплата: 30%" in text


def test_v2_custom_10_30_60(payment_terms):
    """Менеджер ввёл prepay=10, preship=30 → postpay=60."""
    state = _state(
        "v2_prepay_preship_postpay",
        payment_v2_prepay=10, payment_v2_preship=30,
    )
    text = render_payment_block(state, [], payment_terms)
    assert "Предоплата: 10%" in text
    assert "Перед отгрузкой: 30%" in text
    assert "Доплата: 60%" in text


# --- Variant 3: 100% постоплата ---


def test_v3_default_15d_after_installation(payment_terms):
    """Дефолт: 15 дней после монтажа."""
    state = _state("v3_postpay_only")
    text = render_payment_block(state, [], payment_terms)
    assert "100% оплаты в течение 15 банковских дней" in text
    assert "после выполнения монтажа" in text


def test_v3_custom_30d_after_act(payment_terms):
    """30 дней после подписания акта приёмки."""
    state = _state(
        "v3_postpay_only",
        payment_v3_days=30, payment_v3_trigger_id="after_act",
    )
    text = render_payment_block(state, [], payment_terms)
    assert "30 банковских дней" in text
    assert "после подписания акта приёмки" in text


def test_v3_after_delivery(payment_terms):
    """trigger=after_delivery → «после доставки весов»."""
    state = _state(
        "v3_postpay_only", payment_v3_trigger_id="after_delivery",
    )
    text = render_payment_block(state, [], payment_terms)
    assert "после доставки весов" in text


# --- split_by_items: lite-форма из FIX_SPEC ---


def test_split_base_scenario_matches_fix_spec(payment_terms):
    """Базовый сценарий (весы+фундамент+доставка+монтаж+поверка) —
    дословно блок «КП (lite)» из FIX_SPEC (системные дефолты, монтаж 50/50)."""
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
        "— Предоплата: 50% стоимости весов + 50% стоимости фундамента — "
        "в течение 5 банковских дней с момента подписания Договора.\n"
        "— Доплата за весы и доставку: 50% — в течение 5 банковских дней "
        "после уведомления о готовности Весов к отгрузке.\n"
        "— Доплата за фундамент: 50% — в течение 5 банковских дней "
        "после подписания Акта выполненных работ по строительству фундамента.\n"
        "— Монтаж и поверка: 50% предоплата — в течение 5 банковских дней "
        "после уведомления о готовности к монтажу; 50% доплата — "
        "в течение 5 банковских дней после подписания Акта выполненных работ."
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
    text = render_payment_block(state, items, payment_terms)
    lines = text.split("\n")
    assert len(lines) == 4
    assert "Предоплата:" in lines[0]
    assert "ПАК ОРИОН" in lines[0]
    assert "фундамента" in lines[0]
    assert "с момента подписания Договора" in lines[0]
    assert "Доплата за весы (включая ПАК ОРИОН) и доставку" in lines[1]
    assert "после уведомления о готовности Весов к отгрузке" in lines[1]
    assert "Доплата за фундамент" in lines[2]
    assert "после подписания Акта выполненных работ по строительству фундамента" in lines[2]
    assert "Монтаж и поверка" in lines[3]
    assert "после уведомления о готовности к монтажу" in lines[3]
    assert "после подписания Акта выполненных работ." in lines[3]


def test_split_only_scales(payment_terms):
    """B: только весы (без фундамента/доставки/монтажа/ОРИОН) →
    «стоимости проекта»."""
    items = [_item("vesta-с-60-18", "scales")]
    state = _state("split_by_items")
    text = render_payment_block(state, items, payment_terms)
    lines = text.split("\n")
    assert len(lines) == 2
    assert "стоимости проекта" in lines[0]
    assert lines[1] == (
        "— Доплата: 50% — в течение 5 банковских дней "
        "после уведомления о готовности Весов к отгрузке."
    )


def test_split_scales_plus_install(payment_terms):
    """C: весы + монтаж, без фундамента и доставки → 3 строки."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("install_default", "installation_and_verification"),
    ]
    state = _state("split_by_items")
    text = render_payment_block(state, items, payment_terms)
    lines = text.split("\n")
    assert len(lines) == 3
    assert "Предоплата:" in lines[0]
    assert "Доплата за весы:" in lines[1]
    assert "доставку" not in lines[1]
    assert "Монтаж и поверка" in lines[2]


def test_split_scales_with_orion_no_others(payment_terms):
    """D: весы + ОРИОН без фундамента/доставки/монтажа → 2 строки.
    Предоплата упоминает ПАК ОРИОН; Доплата — упрощённая (без «за весы»),
    т.к. кроме весов в сделке ничего нет.
    """
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("orion_standard", "scales"),
    ]
    state = _state("split_by_items")
    text = render_payment_block(state, items, payment_terms)
    lines = text.split("\n")
    assert len(lines) == 2
    assert "ПАК ОРИОН" in lines[0]
    assert "Доплата:" in lines[1]
    assert "после уведомления о готовности Весов к отгрузке" in lines[1]


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
    text = render_payment_block(state, items, payment_terms)
    iv_line = text.split("\n")[-1]
    assert iv_line == (
        "— Монтаж и поверка: 100% оплата — в течение 5 банковских дней "
        "после подписания Акта выполненных работ."
    )
    assert "готовности к монтажу" not in iv_line


def test_split_zero_prepay_skips_line(payment_terms):
    """W3: scales prepay=0 → строка предоплаты не печатается, доплата — «Оплата»."""
    items = [_item("vesta-с-60-18", "scales")]
    state = _state(
        "split_by_items",
        payment_split_state={"scales": {"prepay": 0, "postpay": 100}},
    )
    text = render_payment_block(state, items, payment_terms)
    lines = text.split("\n")
    assert len(lines) == 1
    assert lines[0].startswith("— Оплата: 100% —")


def test_split_w9_orion_poles_object_and_trigger(payment_terms):
    """W9 lite: опоры ОРИОН названы в доплате за фундамент + расширенный триггер."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("orion_standard", "scales"),
        _item("foundation_s_f_18", "foundation"),
        _item("orion_cable_poles", "foundation"),
    ]
    state = _state("split_by_items")
    text = render_payment_block(state, items, payment_terms)
    f_line = next(ln for ln in text.split("\n") if "за фундамент" in ln)
    assert "за фундамент и установку опор и кабель-трасс для ПАК ОРИОН" in f_line
    assert f_line.endswith(
        "после подписания Акта выполненных работ по строительству "
        "фундамента и установке опор и кабель-трасс."
    )


def test_split_rama_ramps_named(payment_terms):
    """Рама/пандусы называются в объекте весов (lite, оба падежа)."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("frame_18", "scales"),
        _item("ramp_set_4", "scales"),
        _item("delivery_default", "delivery"),
    ]
    state = _state("split_by_items")
    text = render_payment_block(state, items, payment_terms)
    lines = text.split("\n")
    assert "50% стоимости весов, комплекта пандусов и рамы" in lines[0]
    assert "Доплата за весы, комплект пандусов, раму и доставку:" in lines[1]


def test_split_shefmontazh_label(payment_terms):
    """W6: is_shefmontazh → строка монтажа называется «Шеф-монтаж и поверка»."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("install_default", "installation_and_verification"),
    ]
    state = _state("split_by_items", is_shefmontazh=True)
    text = render_payment_block(state, items, payment_terms)
    iv_line = text.split("\n")[-1]
    assert iv_line.startswith("— Шеф-монтаж и поверка:")
    assert "Монтаж и поверка:" not in iv_line


def test_split_days_from_state(payment_terms):
    """Срок печатается в каждой строке и берётся из state['payment_days']."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("foundation_s_f_18", "foundation"),
    ]
    state = _state("split_by_items", payment_days=10)
    text = render_payment_block(state, items, payment_terms)
    for line in text.split("\n"):
        assert "в течение 10 банковских дней" in line


# --- custom и edge ---


def test_custom_returns_custom_text(payment_terms):
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


def test_split_has_dash_prefix(payment_terms):
    """split_by_items: каждая строка начинается с «— » (docx-путь Listing)."""
    items = [
        _item("vesta-с-60-18", "scales"),
        _item("foundation_s_f_18", "foundation"),
        _item("delivery_default", "delivery"),
        _item("install_default", "installation_and_verification"),
    ]
    state = _state("split_by_items")
    text = render_payment_block(state, items, payment_terms)
    for line in text.split("\n"):
        assert line.startswith("— "), f"Missing dash prefix: {line!r}"


def test_v1_v2_have_dash_prefix(payment_terms):
    """V1 и V2 (многострочные) — каждая строка с «— »."""
    for preset_id in ("v1_prepay_postpay", "v2_prepay_preship_postpay"):
        state = _state(preset_id)
        text = render_payment_block(state, [], payment_terms)
        for line in text.split("\n"):
            assert line.startswith("— "), (
                f"{preset_id}: missing dash prefix: {line!r}"
            )


def test_v3_has_dash_prefix(payment_terms):
    """V3 — одна строка, начинается с «— »."""
    state = _state("v3_postpay_only")
    text = render_payment_block(state, [], payment_terms)
    assert text.startswith("— ")

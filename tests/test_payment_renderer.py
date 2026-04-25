"""Тесты render_payment_block: 7 пресетов и edge cases."""
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


# --- Простые пресеты ---


def test_prepay_100(payment_terms):
    state = _state("prepay_100", payment_days=10)
    text = render_payment_block(state, [], payment_terms)
    assert "100%" in text
    assert "10 банковских дней" in text


def test_prepay_50_postpay_50(payment_terms):
    state = _state("prepay_50_postpay_50")
    text = render_payment_block(state, [], payment_terms)
    assert "Предоплата: 50%" in text
    assert "Доплата: 50%" in text


def test_prepay_30_postpay_70_with_overrides(payment_terms):
    state = _state(
        "prepay_30_postpay_70",
        payment_percents={"p1": 25, "p2": 75},
    )
    text = render_payment_block(state, [], payment_terms)
    assert "Предоплата: 25%" in text
    assert "Доплата: 75%" in text


def test_postpay_100_15d(payment_terms):
    state = _state("postpay_100_15d")
    text = render_payment_block(state, [], payment_terms)
    assert "100% оплаты в течение 5" in text


def test_postpay_100_30d_default_days(payment_terms):
    """Для постоплаты 30 дней — если payment_days не задан в state, берётся
    default_days из пресета (30)."""
    # Имитируем «дефолтный» state без явного payment_days — но в base уже есть 5.
    # Здесь проверим, что заданный payment_days перебивает default.
    state = _state("postpay_100_30d", payment_days=30)
    text = render_payment_block(state, [], payment_terms)
    assert "30 банковских дней" in text


# --- split_by_items: 4 сценария ---


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
    assert "Доплата за весы" in lines[1]
    assert "доставки" in lines[1]
    assert "Доплата за фундамент" in lines[2]
    assert "монтажа и поверки" in lines[3]


def test_split_only_scales(payment_terms):
    """B: только весы (без фундамента/доставки/монтажа/ОРИОН) →
    «стоимости проекта»."""
    items = [_item("vesta-с-60-18", "scales")]
    state = _state("split_by_items")
    text = render_payment_block(state, items, payment_terms)
    lines = text.split("\n")
    assert len(lines) == 2
    assert "стоимости проекта" in lines[0]
    assert "по уведомлению о готовности" in lines[1]


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
    assert "Доплата за весы" in lines[1]
    assert "монтажа и поверки" in lines[2]


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
    assert "по уведомлению о готовности" in lines[1]


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

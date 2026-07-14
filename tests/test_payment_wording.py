"""Тесты единого словаря формулировок оплаты (src/payment_wording.py)."""

import json
import logging

import pytest

from src.config import PAYMENT_TERMS_JSON
from src.payment_wording import (
    PREP,
    TRIGGER_WORDING,
    _iv_kind,
    default_days,
    default_preset_percents,
    default_split_percents,
    installation_object,
    kind_word,
)


def _raw() -> dict:
    return json.loads(PAYMENT_TERMS_JSON.read_text(encoding="utf-8"))


def _split_preset() -> dict:
    return next(p for p in _raw()["presets"] if p["id"] == "split_by_items")


# ---------------------------------------------------------------------------
# Дефолты читаются из JSON один-в-один (единственный источник)
# ---------------------------------------------------------------------------

def test_default_split_percents_matches_json():
    expected = {
        g["id"]: {k: int(v) for k, v in g["default_percents"].items()}
        for g in _split_preset()["groups"]
    }
    assert default_split_percents() == expected


def test_default_split_percents_has_four_buckets():
    got = default_split_percents()
    assert set(got) == {
        "scales", "foundation", "delivery", "installation_and_verification",
    }
    for bucket in got.values():
        assert set(bucket) == {"prepay", "postpay"}


def test_default_days_matches_json():
    assert default_days() == int(_split_preset()["default_days"])


def test_default_preset_percents_v1_v2():
    assert default_preset_percents("v1_prepay_postpay") == {"prepay": 50}
    assert default_preset_percents("v2_prepay_preship_postpay") == {"prepay": 30, "preship": 40}


def test_default_preset_percents_unknown_returns_empty():
    assert default_preset_percents("no_such_preset") == {}


# ---------------------------------------------------------------------------
# Слово-тип (W3)
# ---------------------------------------------------------------------------

def test_kind_word_paired():
    assert kind_word(50, 50, "prepay") == "предоплата"
    assert kind_word(50, 50, "postpay") == "доплата"


def test_kind_word_single_is_oplata():
    assert kind_word(100, 0, "prepay") == "оплата"
    assert kind_word(0, 100, "postpay") == "оплата"


# ---------------------------------------------------------------------------
# Константы и словарь триггеров
# ---------------------------------------------------------------------------

def test_prep_default():
    assert PREP == "от стоимости"


def test_trigger_wording_has_full_and_lite_for_each():
    for key, reg in TRIGGER_WORDING.items():
        assert "full" in reg and "lite" in reg, key
        assert reg["full"] and reg["lite"]


# ---------------------------------------------------------------------------
# B11 — композиция iv-объекта оплаты (installation_object) + предикат _iv_kind
# ---------------------------------------------------------------------------

# Позиции iv-бакета в двух формах: КП-плоская (item_key) и Договор SpecItem (id).
_INSTALL_CAT = {"item_key": "install_default", "name": "Монтаж автомобильных весов"}
_VERIF_CAT = {"item_key": "verification_default", "name": "Поверка"}
_ORION_INSTALL = {"item_key": "orion_install", "name": "Монтаж ПАК ОРИОН"}


def test_iv_kind_catalog_keys():
    assert _iv_kind(_INSTALL_CAT) == (True, False, False)
    assert _iv_kind({"id": "installation"}) == (True, False, False)
    assert _iv_kind(_VERIF_CAT) == (False, True, False)
    assert _iv_kind({"id": "verification"}) == (False, True, False)
    assert _iv_kind(_ORION_INSTALL) == (False, False, True)


def test_iv_kind_custom_tag_both_dict_shapes():
    """Правка 1: custom-монтаж опознаётся на ОБОИХ путях по сырому тегу.

    КП-путь: item_key=custom_N; Договор-путь при коллизии: id=custom_N.
    Промоушен id ненадёжен — ловим тегом custom_scope.
    """
    assert _iv_kind({"item_key": "custom_1", "custom_scope": "installation"}) == (True, False, False)
    assert _iv_kind({"id": "custom_1", "custom_scope": "installation"}) == (True, False, False)


def test_iv_kind_untagged_custom_unrecognized():
    assert _iv_kind({"item_key": "custom_2", "custom_scope": None}) == (False, False, False)


@pytest.mark.parametrize("shef,expected", [
    (False, "монтажных работ и поверки"),
    (True, "шеф-монтажных работ и поверки"),
])
def test_install_verification_full_byte_identical(shef, expected):
    assert installation_object("full", [_INSTALL_CAT, _VERIF_CAT], shef) == expected


@pytest.mark.parametrize("shef,expected", [
    (False, "Монтаж и поверка"),
    (True, "Шеф-монтаж и поверка"),
])
def test_install_verification_lite_byte_identical(shef, expected):
    assert installation_object("lite", [_INSTALL_CAT, _VERIF_CAT], shef) == expected


def test_compose_install_only():
    assert installation_object("full", [_INSTALL_CAT], False) == "монтажных работ"
    assert installation_object("lite", [_INSTALL_CAT], False) == "Монтаж"


def test_compose_orion_install_without_scales_install():
    assert installation_object("full", [_ORION_INSTALL], False) == "шеф-монтажа ПАК ОРИОН"
    assert installation_object("lite", [_ORION_INSTALL], False) == "Шеф-монтаж ПАК ОРИОН"


def test_compose_orion_install_absorbed_by_scales_install():
    """Поглощение: монтаж весов есть → шеф-монтаж ОРИОНа растворяется."""
    assert installation_object("full", [_INSTALL_CAT, _ORION_INSTALL], False) == "монтажных работ"


def test_compose_orion_install_plus_verification():
    assert (
        installation_object("full", [_ORION_INSTALL, _VERIF_CAT], False)
        == "шеф-монтажа ПАК ОРИОН и поверки"
    )


def test_compose_verification_only_lite_capitalized():
    """B15: состав «только поверка» — lite-объект с заглавной («— Поверка: …»),
    full — строчными (внутри предложения после «от стоимости»)."""
    assert installation_object("lite", [_VERIF_CAT], False) == "Поверка"
    assert installation_object("full", [_VERIF_CAT], False) == "поверки"


def test_compose_custom_install():
    iv = [{"item_key": "custom_1", "custom_scope": "installation"}, _VERIF_CAT]
    assert installation_object("lite", iv, False) == "Монтаж и поверка"


def test_guard_unrecognized_position_falls_to_generic(caplog):
    """Custom «Поверка» без тега (name-regex → iv-бакет, но не опознана)
    → generic + warning; композиция не включается на неполном составе."""
    iv = [
        _INSTALL_CAT,
        {"item_key": "custom_2", "name": "Поверка эталонами", "custom_scope": None},
    ]
    with caplog.at_level(logging.WARNING):
        result = installation_object("full", iv, False)
    assert result == "монтажных работ и поверки"  # generic, заведомо не хуже
    assert "неопознанная позиция iv-бакета" in caplog.text


def test_guard_empty_bucket_generic():
    assert installation_object("full", [], False) == "монтажных работ и поверки"
    assert installation_object("lite", [], True) == "Шеф-монтаж и поверка"

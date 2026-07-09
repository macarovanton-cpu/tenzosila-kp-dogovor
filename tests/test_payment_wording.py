"""Тесты единого словаря формулировок оплаты (src/payment_wording.py)."""

import json

from src.config import PAYMENT_TERMS_JSON
from src.payment_wording import (
    PREP,
    TRIGGER_WORDING,
    default_days,
    default_preset_percents,
    default_split_percents,
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

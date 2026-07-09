"""payment_wording.py — единый словарь формулировок блока оплаты.

Один источник для двух генераторов текста оплаты:
- КП (`generators/payment_renderer.py`) — регистр `lite` (без денег);
- Договор/Спецификация (`contracts/payment_line.py`) — регистр `full`.

Здесь же — дефолты процентов/сроков (единственный источник —
`data/payment_terms.json`) и правило слова-типа платежа (W3).

Модуль уровня src-корня (как `spec_builder`/`term_days`): без streamlit,
чтобы его импортировали и `contracts/`, и `generators/`.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from src.config import PAYMENT_TERMS_JSON

# ---------------------------------------------------------------------------
# Дефолты — единственный источник из data/payment_terms.json
# ---------------------------------------------------------------------------

_SPLIT_PRESET_ID = "split_by_items"


@lru_cache(maxsize=1)
def _load_payment_terms() -> dict:
    """Разобрать payment_terms.json (кэш). Без streamlit — plain json."""
    return json.loads(PAYMENT_TERMS_JSON.read_text(encoding="utf-8"))


def _preset(preset_id: str) -> dict:
    """Найти пресет по id (пустой dict, если нет)."""
    for p in _load_payment_terms().get("presets", []):
        if p.get("id") == preset_id:
            return p
    return {}


def default_split_percents() -> dict[str, dict[str, int]]:
    """Дефолтные проценты бакетов split_by_items: group_id → {prepay, postpay}."""
    return {
        g["id"]: {k: int(v) for k, v in (g.get("default_percents") or {}).items()}
        for g in _preset(_SPLIT_PRESET_ID).get("groups", [])
    }


def default_days() -> int:
    """Срок по умолчанию (банковских дней) пресета split_by_items."""
    return int(_preset(_SPLIT_PRESET_ID).get("default_days") or 5)


def default_preset_percents(preset_id: str) -> dict[str, int]:
    """default_percents не-split пресета (v1/v2/prepay_100) из JSON."""
    return {
        k: int(v)
        for k, v in (_preset(preset_id).get("default_percents") or {}).items()
    }


# ---------------------------------------------------------------------------
# Слово-тип платежа (W3, реш. 7 FIX_SPEC)
# ---------------------------------------------------------------------------

def kind_word(prepay_pct: int, postpay_pct: int, phase: Literal["prepay", "postpay"]) -> str:
    """Слово-тип по раскладу долей бакета.

    Обе фазы > 0 → «предоплата»/«доплата» (парный платёж);
    ровно одна > 0 → «оплата» (единичный платёж).
    """
    if prepay_pct > 0 and postpay_pct > 0:
        return "предоплата" if phase == "prepay" else "доплата"
    return "оплата"


# ---------------------------------------------------------------------------
# Предлог (W10) — единый дефолт; «за» остаётся ручной опцией редактора.
# ---------------------------------------------------------------------------

PREP = "от стоимости"


# ---------------------------------------------------------------------------
# Объекты оплаты — общие для обоих генераторов.
# ---------------------------------------------------------------------------

def installation_object(register: Literal["full", "lite"], shef: bool) -> str:
    """Объект оплаты монтажа (W6): при шеф-монтаже печатается «шеф-монтаж».

    Один источник для КП и Спец. Флаг shef оба пути берут из одного поля
    снапшота installation_scope: КП — state["is_shefmontazh"] (⟺
    scope == "shefmontazh", см. storage.snapshot_builder
    ._resolve_installation_scope и contracts.from_kp._reconstruct_state),
    Спец — installation_scope напрямую.
    """
    if register == "full":
        return "шеф-монтажных работ и поверки" if shef else "монтажных работ и поверки"
    return "Шеф-монтаж и поверка" if shef else "Монтаж и поверка"


# ---------------------------------------------------------------------------
# Тексты триггеров — единый словарь, два регистра.
# Ключи совпадают со значениями contracts.payment_line.PaymentTrigger.
# `full` — договор/спецификация; `lite` — КП (используется в Стадии 2).
# ---------------------------------------------------------------------------

TRIGGER_WORDING: dict[str, dict[str, str]] = {
    "SPEC_SIGNED":    {"full": "подписания настоящей Спецификации",
                       "lite": "с момента подписания Договора"},
    "FOUNDATION_ACT": {"full": "подписания Акта выполненных работ по строительству фундамента",
                       "lite": "после подписания Акта выполненных работ по строительству фундамента"},
    "SHIPMENT_READY": {"full": "получения уведомления о готовности Весов к отгрузке",
                       "lite": "после уведомления о готовности Весов к отгрузке"},
    "BRIGADE_READY":  {"full": "уведомления о готовности принять монтажную бригаду на месте монтажа",
                       "lite": "после уведомления о готовности к монтажу"},
    "WORK_ACT":       {"full": "подписания Акта выполненных работ по настоящей Спецификации",
                       "lite": "после подписания Акта выполненных работ"},
    "DELIVERED":      {"full": "поставки Весов Заказчику",
                       "lite": "после поставки Весов"},
}

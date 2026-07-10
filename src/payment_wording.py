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

def join_ru(parts: list[str]) -> str:
    """Перечисление по-русски: «a», «a и b», «a, b и c»."""
    if len(parts) <= 1:
        return parts[0] if parts else ""
    return ", ".join(parts[:-1]) + " и " + parts[-1]


def wording_flags(spec_items: list[dict]) -> dict[str, bool]:
    """Флаги формулировок по ключам позиций — единый детект для КП и Спец.

    Позиции несут ключи двух семейств: item_key опций КП (frame_*, ramp_set_*,
    orion_cable_poles) или канонические id Спец из contracts/spec_items.py
    (rama, pandus, orion_poles, orion) — матчим оба.
    has_orion — ОРИОН в сделке; has_poles — опоры/кабель-трассы ОРИОН (W9);
    has_ramps / has_frame — комплект пандусов / рама (бакет scales).
    """
    keys = {str(it.get("item_key") or it.get("id") or "") for it in spec_items}
    return {
        "has_orion": any(k == "orion" or k.startswith("orion_") for k in keys),
        "has_poles": bool(keys & {"orion_cable_poles", "orion_poles"}),
        "has_ramps": any(k == "pandus" or k.startswith("ramp_set_") for k in keys),
        "has_frame": any(k == "rama" or k.startswith("frame_") for k in keys),
    }


# Словоформы объекта «весы» по регистрам: full — род. падеж Спец,
# lite_gen — род. падеж КП («стоимости …»), lite_acc — вин. падеж КП («за …»).
_SCALES_WORDS: dict[str, dict[str, str]] = {
    "full":     {"scales": "Весов", "orion": "Весов (включая ПАК ОРИОН)",
                 "ramps": "комплекта пандусов", "frame": "рамы"},
    "lite_gen": {"scales": "весов", "orion": "весов (включая ПАК ОРИОН)",
                 "ramps": "комплекта пандусов", "frame": "рамы"},
    "lite_acc": {"scales": "весы", "orion": "весы (включая ПАК ОРИОН)",
                 "ramps": "комплект пандусов", "frame": "раму"},
}


def scales_object_parts(
    register: Literal["full", "lite_gen", "lite_acc"],
    has_orion: bool, has_ramps: bool, has_frame: bool,
) -> list[str]:
    """Части объекта «весы» для join_ru: рама/пандусы называются в объекте
    оплаты (реш. Антона, механизм W9)."""
    w = _SCALES_WORDS[register]
    parts = [w["orion"] if has_orion else w["scales"]]
    if has_ramps:
        parts.append(w["ramps"])
    if has_frame:
        parts.append(w["frame"])
    return parts


_POLES_SUFFIX = " и установку опор и кабель-трасс для ПАК ОРИОН"


def foundation_object(register: Literal["full", "lite"], has_poles: bool) -> str:
    """Объект доплаты за фундамент; W9 — опоры/кабель-трассы ОРИОН называются."""
    base = "фундамента Весов" if register == "full" else "фундамент"
    return base + _POLES_SUFFIX if has_poles else base


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
                       "lite": "подписание Договора"},
    # W7: prepay_100 — основание «счёт». Только full-регистр (Спец/Договор
    # поставки); в lite (КП) фраза про счёт не печатается (КП рендерит
    # prepay_100 из body_template JSON).
    "SPEC_SIGNED_INVOICE": {
        "full": "подписания настоящей Спецификации, "
                "на основании выставленного Поставщиком счёта",
        "lite": "с момента подписания Договора",
    },
    "FOUNDATION_ACT": {"full": "подписания Акта выполненных работ по строительству фундамента",
                       "lite": "Акт по строительству фундамента"},
    # W9: расширенный триггер акта фундамента при опорах/кабель-трассах ОРИОН.
    "FOUNDATION_ACT_POLES": {
        "full": "подписания Акта выполненных работ по строительству фундамента "
                "и установке опор и кабель-трасс",
        "lite": "Акт по строительству фундамента и установке опор и кабель-трасс",
    },
    "SHIPMENT_READY": {"full": "получения уведомления о готовности Весов к отгрузке",
                       "lite": "готовность Весов к отгрузке"},
    "BRIGADE_READY":  {"full": "уведомления о готовности принять монтажную бригаду на месте монтажа",
                       "lite": "готовность к монтажу"},
    "WORK_ACT":       {"full": "подписания Акта выполненных работ по настоящей Спецификации",
                       "lite": "Акт выполненных работ"},
    "DELIVERED":      {"full": "поставки Весов Заказчику",
                       "lite": "после поставки Весов"},
}

# W8: контекстные override'ы для Договора поставки (без Спецификации и монтажа).
# Ключи — значения PaymentTrigger; остальные триггеры берутся из full-регистра.
SUPPLY_TRIGGER_OVERRIDES: dict[str, str] = {
    "SPEC_SIGNED": "подписания настоящего Договора",
    "SPEC_SIGNED_INVOICE": "подписания настоящего Договора, "
                           "на основании выставленного Поставщиком счёта",
    "WORK_ACT":    "поставки Весов Покупателю",
    "DELIVERED":   "поставки Весов Покупателю",
}

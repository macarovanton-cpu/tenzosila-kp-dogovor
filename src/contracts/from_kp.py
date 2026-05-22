"""Маппинг снапшота КП из Supabase в плейсхолдеры спецификации договора."""
from __future__ import annotations

import logging
import re
from typing import Any

from src.term_days import TERM_DAYS_DEFAULTS, calculate_term_days_per_item

_logger = logging.getLogger(__name__)

_SIMPLE_OPTION_NAMES: dict[str, str] = {
    "delivery_default": "Доставка весов до объекта",
    "install_default": "Монтаж автомобильных весов",
    "verification_default": "Поверка автомобильных весов с доставкой эталонов",
}

_FOUNDATION_PATTERNS = [
    (re.compile(r"^foundation_s_f_(\d+)$"),
     "Фундамент железобетонный под весы автомобильные ВЕСТА-{line}, {N}м"),
    (re.compile(r"^foundation_lite_sl_fl_(\d+)$"),
     "Фундамент пандусный «ЛАЙТ» под весы автомобильные ВЕСТА-{line}, {N}м"),
    (re.compile(r"^foundation_std_sl_fl_(\d+)$"),
     "Фундамент пандусный «Стандарт» под весы автомобильные ВЕСТА-{line}, {N}м"),
]


def _resolve_option_name(key: str, line: str) -> str | None:
    """Вернуть каноническое имя для ключа опции или None если неизвестный."""
    if key in _SIMPLE_OPTION_NAMES:
        return _SIMPLE_OPTION_NAMES[key]
    for pattern, template in _FOUNDATION_PATTERNS:
        m = pattern.match(key)
        if m:
            return template.format(line=line, N=m.group(1))
    return None


def _reconstruct_state(kp_row: dict[str, Any]) -> dict[str, Any]:
    """Разворачивает kp_row["data"] JSONB → state-подобный dict для build_spec_items."""
    data = kp_row.get("data") or {}
    model = data.get("model") or {}
    payment = data.get("payment") or {}

    options = {
        key: {
            "enabled": True,
            "price": v.get("price", 0),
            "qty": v.get("qty", 1),
            "customer_side": v.get("customer_side", False),
        }
        for key, v in (data.get("options") or {}).items()
    }

    return {
        "model_id": kp_row.get("model_id", ""),
        "model_line": model.get("line", ""),
        "model_max": model.get("max"),
        "model_length": model.get("length"),
        "model_price": model.get("price"),
        "sensor_id": (data.get("equipment") or {}).get("sensor_id", ""),
        "indicator_id": (data.get("equipment") or {}).get("indicator_id", ""),
        "options": options,
        "spec_items_overrides": data.get("spec_overrides") or {},
        "total_term_days": None,
        "payment_preset_id": payment.get("preset_id", "split_by_items"),
        "payment_days": payment.get("days", 5),
        "payment_custom_text": payment.get("custom_text", ""),
        "payment_split_state": payment.get("split_state") or {},
        "payment_v1_prepay": payment.get("v1_prepay", 50),
        "payment_v2_prepay": payment.get("v2_prepay", 30),
        "payment_v2_preship": payment.get("v2_preship", 40),
        "payment_v3_days": payment.get("v3_days", 15),
        "payment_v3_trigger_id": payment.get("v3_trigger_id", "after_installation"),
    }


def _fmt(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") if amount else ""


def build_specification_from_kp_snapshot(
    kp_row: dict[str, Any],
    prices: dict[str, Any],
    models_json: dict[str, Any],
    payment_terms: dict[str, Any],
) -> dict[str, str]:
    """Принимает строку из Supabase, возвращает плоский dict {СПЕЦ_* → str}
    для filler.fill_template. ЗАКАЗЧИК_* поля не возвращаются.

    kp_row: строка из таблицы kps (id, kp_number, model_id, data, ...)
    prices: содержимое data/prices.json
    models_json: содержимое data/models.json
    payment_terms: содержимое data/payment_terms.json
    """
    from src.spec_builder import build_spec_items
    from src.contracts.utils import number_to_words
    from src.generators.payment_renderer import render_payment_block

    state = _reconstruct_state(kp_row)
    spec_items = build_spec_items(state, prices, models_json)

    scales = [i for i in spec_items if i.get("payment_group") == "scales"]
    foundations = [i for i in spec_items if i.get("payment_group") == "foundation"]
    install_verify = [
        i for i in spec_items
        if i.get("payment_group") == "installation_and_verification"
    ]
    delivery = [i for i in spec_items if i.get("payment_group") == "delivery"]

    scales_total = sum(i["total"] for i in scales)
    foundation_total = sum(i["total"] for i in foundations)
    install_total = sum(i["total"] for i in install_verify)
    delivery_total = sum(i["total"] for i in delivery)
    grand_total = scales_total + foundation_total + install_total + delivery_total

    data = kp_row.get("data") or {}
    model = data.get("model") or {}
    line = model.get("line", "")
    max_t = model.get("max", "")
    length = model.get("length", "")
    model_short = f"ВЕСТА-{line}-{max_t}-{length}"

    item_to_days, _ = calculate_term_days_per_item(spec_items)
    model_id = state.get("model_id", "")
    scales_term = str(item_to_days.get(model_id) or TERM_DAYS_DEFAULTS.get("scales", 20))

    foundation_term = ""
    for item in foundations:
        t = item_to_days.get(item["item_key"])
        if t is not None:
            foundation_term = str(t)
            break

    inst_sum = sum(item_to_days.get(i["item_key"], 0) or 0 for i in install_verify)
    install_term = str(inst_sum) if inst_sum else ""

    payment_text = render_payment_block(state, spec_items, payment_terms)
    lines = [ln.strip() for ln in payment_text.split("\n") if ln.strip()]
    slots = (lines + [""] * 6)[:6]

    p1_name = ""
    if scales:
        model_item = next(
            (i for i in scales if i["item_key"].startswith("vesta-")), scales[0]
        )
        p1_name = model_item["name"].split("\n")[0]

    p2_params = f"ВЕСТА-{line}, {length}м" if foundations else ""

    return {
        "СПЕЦ_НДС": "22",
        "СПЕЦ_МОДЕЛЬ_КРАТКОЕ": model_short,
        "СПЕЦ_МАКС_НАГРУЗКА": str(max_t),
        "СПЕЦ_П1_НАИМЕНОВАНИЕ": p1_name,
        "СПЕЦ_П1_СУММА": _fmt(scales_total),
        "СПЕЦ_П2_ПАРАМЕТРЫ": p2_params,
        "СПЕЦ_П2_СУММА": _fmt(foundation_total),
        "СПЕЦ_П3_НАИМЕНОВАНИЕ": "Монтаж и поверка" if install_verify else "",
        "СПЕЦ_П3_СУММА": _fmt(install_total),
        "СПЕЦ_П4_НАИМЕНОВАНИЕ": "Доставка" if delivery else "",
        "СПЕЦ_П4_СУММА": _fmt(delivery_total),
        "СПЕЦ_П5_НАИМЕНОВАНИЕ": "",
        "СПЕЦ_П5_СУММА": "",
        "СПЕЦ_ИТОГО": _fmt(grand_total),
        "СПЕЦ_ИТОГО_ПРОПИСЬ": number_to_words(grand_total),
        "СПЕЦ_ОПЛАТА_П1": slots[0],
        "СПЕЦ_ОПЛАТА_П2": slots[1],
        "СПЕЦ_ОПЛАТА_П3": slots[2],
        "СПЕЦ_ОПЛАТА_П4": slots[3],
        "СПЕЦ_ОПЛАТА_П5": slots[4],
        "СПЕЦ_ОПЛАТА_П6": slots[5],
        "СПЕЦ_СРОК_ПОСТАВКИ": scales_term,
        "СПЕЦ_СРОК_ФУНДАМЕНТ": foundation_term,
        "СПЕЦ_СРОК_МОНТАЖ": install_term,
    }


def build_spec_rows_from_snapshot(kp_row: dict[str, Any]) -> list[dict[str, Any]]:
    """Список строк спецификации из снапшота КП.

    Каждая строка: {name, qty, price, price_display, customer_side}.
    customer_side=True → price_display='ЗАКАЗЧИК', price=0 (не в итого).
    qty=0 → строка пропускается.
    Неизвестный ключ → WARNING в логе, добавляется с raw-ключом.
    """
    data = kp_row.get("data") or {}
    model = data.get("model") or {}
    line = model.get("line", "")
    max_t = model.get("max", "")
    length = model.get("length", "")
    model_price = int(model.get("price") or 0)

    rows: list[dict[str, Any]] = []

    model_name = (
        f"Весы автомобильные ВЕСТА-{line}-{max_t}-{length}-Ц, "
        f"max {max_t}т, размеры платформы {length}х3м"
    )
    rows.append({
        "name": model_name,
        "qty": 1,
        "price": model_price,
        "price_display": _fmt(model_price),
        "customer_side": False,
    })

    options = data.get("options") or {}
    for key, opt in options.items():
        qty = int(opt.get("qty", 1))
        if qty == 0:
            continue
        customer_side = bool(opt.get("customer_side", False))
        price = 0 if customer_side else int(opt.get("price", 0))
        price_display = "ЗАКАЗЧИК" if customer_side else _fmt(price)

        name = _resolve_option_name(key, line)
        if name is None:
            _logger.warning("build_spec_rows_from_snapshot: неизвестный ключ опции %r", key)
            name = key

        rows.append({
            "name": name,
            "qty": qty,
            "price": price,
            "price_display": price_display,
            "customer_side": customer_side,
        })

    return rows

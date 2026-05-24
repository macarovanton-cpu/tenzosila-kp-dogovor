"""Маппинг снапшота КП из Supabase в плейсхолдеры спецификации договора."""
from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from src.term_days import TERM_DAYS_DEFAULTS, calculate_term_days_per_item
from src.contracts.spec_items import SpecItem, _option_key_to_spec_id

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


def _row_sort_key(row: dict[str, Any]) -> int:
    """Ключ сортировки для стабильного порядка строк спецификации."""
    name = row.get("name", "")
    if name.startswith("Весы автомобильные"):
        return 0
    if "Фундамент" in name:
        return 1
    if "Монтаж" in name:
        return 2
    if "Поверка" in name:
        return 3
    if "Доставка" in name:
        return 4
    return 5


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

    Строки спецификации берутся из build_spec_rows_from_snapshot (канонические
    формулировки, отдельные монтаж и поверка). Платёжные строки и сроки —
    через старый пайплайн spec_items.
    """
    from src.spec_builder import build_spec_items
    from src.contracts.utils import number_to_words
    from src.generators.payment_renderer import render_payment_block

    rows = build_spec_rows_from_snapshot(kp_row)
    rows.sort(key=_row_sort_key)

    if len(rows) > 5:
        _logger.warning(
            "build_specification_from_kp_snapshot: %d строк > 5 слотов шаблона",
            len(rows),
        )

    result: dict[str, str] = {}
    for i in range(1, 6):
        if i <= len(rows):
            row = rows[i - 1]
            result[f"СПЕЦ_П{i}_НАИМЕНОВАНИЕ"] = row["name"]
            result[f"СПЕЦ_П{i}_СУММА"] = row["price_display"]
        else:
            result[f"СПЕЦ_П{i}_НАИМЕНОВАНИЕ"] = ""
            result[f"СПЕЦ_П{i}_СУММА"] = ""

    grand_total = sum(r["price"] for r in rows if not r["customer_side"])

    data = kp_row.get("data") or {}
    model = data.get("model") or {}
    line = model.get("line", "")
    max_t = model.get("max", "")
    length = model.get("length", "")
    model_short = f"ВЕСТА-{line}-{max_t}-{length}"

    state = _reconstruct_state(kp_row)
    spec_items = build_spec_items(state, prices, models_json)

    item_to_days, _ = calculate_term_days_per_item(spec_items)
    model_id = state.get("model_id", "")
    scales_term = str(item_to_days.get(model_id) or TERM_DAYS_DEFAULTS.get("scales", 20))

    foundations = [i for i in spec_items if i.get("payment_group") == "foundation"]
    foundation_term = ""
    for item in foundations:
        t = item_to_days.get(item["item_key"])
        if t is not None:
            foundation_term = str(t)
            break

    install_verify = [
        i for i in spec_items
        if i.get("payment_group") == "installation_and_verification"
    ]
    inst_sum = sum(item_to_days.get(i["item_key"], 0) or 0 for i in install_verify)
    install_term = str(inst_sum) if inst_sum else ""

    payment_text = render_payment_block(state, spec_items, payment_terms)
    lines = [ln.strip() for ln in payment_text.split("\n") if ln.strip()]
    slots = (lines + [""] * 6)[:6]

    result.update({
        "СПЕЦ_НДС": "22",
        "СПЕЦ_МОДЕЛЬ_КРАТКОЕ": model_short,
        "СПЕЦ_МАКС_НАГРУЗКА": str(max_t),
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
    })
    return result


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


def build_spec_v2_data(
    kp_row: dict[str, Any],
    prices: dict[str, Any],
    models_json: dict[str, Any],
    payment_terms: dict[str, Any],
    equipment_specs: dict[str, Any],
) -> tuple[dict, list[dict], dict]:
    """Собрать (data, items, deal) для fill_spec_v2 из снапшота КП.

    data — плейсхолдеры + _payment_lines, _terms_lines, _kit_items.
    items — SpecItem list для таблицы позиций.
    deal — контекст для clauses.
    """
    from datetime import date

    from src.contracts.kit_renderer import build_kit_items
    from src.contracts.terms_renderer import render_terms_section
    from src.contracts.tth_context import build_tth_data
    from src.contracts.utils import number_to_words
    from src.data_loader import get_line_defaults, get_model_by_id
    from src.generators.payment_renderer import render_payment_block
    from src.spec_builder import build_spec_items

    data_json = kp_row.get("data") or {}
    model_meta = data_json.get("model") or {}
    line = model_meta.get("line", "")
    max_t = model_meta.get("max", "")
    length = model_meta.get("length", "")
    model_short = f"ВЕСТА-{line}-{max_t}-{length}"

    # --- SpecItems ---
    items = build_specification_items(kp_row)

    # --- Deal ---
    deal: dict[str, Any] = {
        "items": items,
        "scope_overrides": data_json.get("spec_overrides") or {},
        "flags": data_json.get("flags") or {},
        "delivery_address": data_json.get("delivery_address", ""),
    }

    # --- Lookup model / sensor / indicator ---
    state = _reconstruct_state(kp_row)
    model_id = state.get("model_id", "")
    model_dict = get_model_by_id(models_json, model_id) or {}
    line_defaults = get_line_defaults(models_json, line)

    sensor_model_name = line_defaults.get("default_sensor", "Zemic DHM9B-30t")
    sensor_dict = _find_sensor(equipment_specs, sensor_model_name)
    indicator_name = line_defaults.get("default_indicator", "ТИТАН 3ЦС")
    indicator_dict = _find_indicator(equipment_specs, indicator_name)

    # --- Payment ---
    raw_spec_items = build_spec_items(state, prices, models_json)
    payment_text = render_payment_block(state, raw_spec_items, payment_terms)
    payment_lines = [ln.strip() for ln in payment_text.split("\n") if ln.strip()]

    # --- Terms ---
    terms_lines = render_terms_section(deal, raw_spec_items)

    # --- Kit ---
    cable_len = line_defaults.get("default_cable_length_m", 20)
    kit_items = build_kit_items(
        model_dict, line_defaults, sensor_dict, indicator_dict, cable_len,
    )

    # --- TTH ---
    tth = build_tth_data(model_dict, sensor_dict)

    # --- Data dict ---
    data: dict[str, Any] = {
        "СПЕЦ_НДС": "22",
        "СПЕЦ_МОДЕЛЬ_КРАТКОЕ": model_short,
        "СПЕЦ_МАКС_НАГРУЗКА": str(max_t),
        "ПРИЛОЖЕНИЕ_НОМЕР": "1",
        "ТЕКУЩИЙ_ГОД": str(date.today().year),
        "_payment_lines": payment_lines,
        "_terms_lines": terms_lines,
        "_kit_items": kit_items,
    }
    data.update(tth)

    return data, items, deal


def _find_sensor(equipment_specs: dict, sensor_label: str) -> dict:
    """Найти запись сенсора по метке из line_defaults (e.g. 'Zemic DHM9B-30t')."""
    parts = sensor_label.split()
    model_part = parts[1].split("-")[0] if len(parts) > 1 else sensor_label
    for s in equipment_specs.get("sensors", []):
        if s.get("model", "") == model_part:
            return s
    return {"temperature_min_c": -30, "temperature_max_c": 40, "type": "digital"}


def _find_indicator(equipment_specs: dict, indicator_name: str) -> dict:
    """Найти запись терминала по model name (e.g. 'ТИТАН 3ЦС')."""
    for t in equipment_specs.get("terminals", []):
        if t.get("model", "") == indicator_name:
            return t
    return {"model": indicator_name, "compatible_sensors": "digital"}


_ITEM_ORDER: dict[str, int] = {
    "weights": 0,
    "foundation": 1,
    "installation": 2,
    "verification": 3,
    "delivery": 4,
}


def build_specification_items(kp_row: dict[str, Any]) -> list[SpecItem]:
    """Собрать список SpecItem из строки КП Supabase.

    Цены хранятся с НДС (та же конвенция что и в prices.json и КП).
    """
    data = kp_row.get("data") or {}
    model = data.get("model") or {}
    line = model.get("line", "")
    max_t = model.get("max", "")
    length = model.get("length", "")
    model_price = float(model.get("price") or 0)
    options = data.get("options") or {}

    items: list[SpecItem] = []

    # Позиция весов — всегда первая
    model_name = (
        f"Весы автомобильные ВЕСТА-{line}-{max_t}-{length}-Ц, "
        f"max {max_t}т, размеры платформы {length}х3м"
    )
    items.append({  # type: ignore[misc]
        "id": "weights",
        "name": model_name,
        "unit": "компл",
        "quantity": 1.0,
        "price_per_unit": model_price,
        "total": model_price,
        "payment_group": None,
        "is_custom": False,
        "source": "preset",
        "metadata": {"line": line, "max": max_t, "length": length},
    })

    for key, opt in options.items():
        qty = float(opt.get("qty", 1) or 1)
        if qty == 0:
            continue

        customer_side = bool(opt.get("customer_side", False))
        price = 0.0 if customer_side else float(opt.get("price") or 0)

        spec_id = _option_key_to_spec_id(key)
        is_custom = spec_id is None
        if is_custom:
            _logger.warning("build_specification_items: неизвестный ключ %r", key)
            spec_id = f"custom_{uuid.uuid4().hex[:8]}"

        name = _resolve_option_name(key, line)
        if name is None:
            name = key

        metadata: dict[str, Any] = {}
        if customer_side:
            metadata["customer_side"] = True
        if spec_id == "installation":
            has_foundation = any(k.startswith("foundation_") for k in options)
            metadata["scope"] = "fundament" if has_foundation else "rama"
        elif spec_id == "foundation":
            if "_lite_" in key:
                metadata["scope"] = "pandus_lite"
            elif "_std_" in key:
                metadata["scope"] = "pandus_std"
            else:
                metadata["scope"] = "fundament_jb"

        price_per_unit = price / qty if qty > 0 else 0.0

        items.append({  # type: ignore[misc]
            "id": spec_id,
            "name": name,
            "unit": "компл",
            "quantity": qty,
            "price_per_unit": price_per_unit,
            "total": price,
            "payment_group": None,
            "is_custom": is_custom,
            "source": "custom" if is_custom else "preset",
            "metadata": metadata,
        })

    items.sort(key=lambda x: _ITEM_ORDER.get(x["id"], 10))
    return items

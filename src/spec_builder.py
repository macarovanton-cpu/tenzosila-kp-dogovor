"""Сборка spec_items — списка позиций для раздела спецификации КП."""
from __future__ import annotations

from typing import Any

from src.config import (
    OPTION_BLOCKS_ORDER,
    UNIT_BY_BLOCK,
)
from src.data_loader import (
    get_equipment_info,
    get_model_by_id,
    get_price_by_model_id,
)
from src.filters import get_visible_options
from src.term_days import resolve_term_role

# Дженерик-обозначения групп фундаментов в prices.json. Подменяются на
# конкретную линейку выбранной модели в имени позиции спецификации.
_FOUNDATION_S_F_PLACEHOLDER = "С/Ф/П"
_FOUNDATION_S_F_LINES = frozenset({"С", "Ф", "П"})
_FOUNDATION_SL_FL_PLACEHOLDER = "СЛ/ФЛ"
_FOUNDATION_SL_FL_LINES = frozenset({"СЛ", "ФЛ"})

# Дженерик-обозначения рам и пандусов.
_FRAME_PLACEHOLDER = "С(Ф)/ФЛ(СЛ)"
_FRAME_LINES = frozenset({"С", "Ф", "П", "СЛ", "ФЛ"})
_RAMP_F_S_PLACEHOLDER = "Ф/С"
_RAMP_F_S_LINES = frozenset({"С", "Ф", "П"})
_RAMP_FL_SL_PLACEHOLDER = "ФЛ/СЛ"
_RAMP_FL_SL_LINES = frozenset({"СЛ", "ФЛ"})


def _format_model_name(model: dict | None, model_id: str) -> str:
    if model and model.get("full_name"):
        return f"Весы автомобильные {model['full_name']}"
    return f"Весы автомобильные {model_id}"


def _format_dimension_value(value: Any) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "?"
    if num.is_integer():
        return str(int(num))
    return f"{num:.1f}".rstrip("0").rstrip(".")


def format_platform_size(
    length: Any, width: Any, *, separator: str = "х", suffix: str = "м"
) -> str:
    """Отформатировать размеры платформы для КП и DOCX."""
    return (
        f"{_format_dimension_value(length)}"
        f"{separator}"
        f"{_format_dimension_value(width)}"
        f"{suffix}"
    )


def _format_model_code(state: dict[str, Any]) -> str:
    """Короткий код модели для связанных позиций КП."""
    line = state.get("model_line", "")
    max_t = state.get("model_max", "")
    length = state.get("model_length", "")
    if line and max_t and length:
        return f"ВЕСТА-{line}-{max_t}-{length}"
    return "ВЕСТА"


def _format_model_full_spec_name(
    model: dict | None,
    model_id: str,
    state: dict,
    models_json: dict,
) -> str:
    """Многострочное имя для первой позиции спецификации.

    Структура (plain string с \\n; форматирование шрифта — в kp_generator):
        Весы автомобильные {full_name}
        Датчики: {sensor_label}, {sensors_count} шт.
        Терминал: {indicator_label}

    Ограждение, рама, пандусы — отдельные строки spec_items, в имя НЕ включаются.
    """
    parts = [_format_model_name(model, model_id)]
    if model:
        width = float(state.get("platform_width_m", 3.0) or 3.0)
        if width != 3.0:
            parts.append(
                "Размер платформы: "
                f"{format_platform_size(state.get('model_length', ''), width)}"
            )
        sensor_info = get_equipment_info(
            models_json, "sensor", state.get("sensor_id", "")
        )
        sensors_count = model.get("sensors_count", 0)
        parts.append(
            f"Датчики: {sensor_info['label']}, {sensors_count} шт."
        )
        indicator_info = get_equipment_info(
            models_json, "indicator", state.get("indicator_id", "")
        )
        parts.append(f"Терминал: {indicator_info['label']}")
    return "\n".join(parts)


def resolve_dynamic_option_label(
    item_key: str, label: str, model_line: str
) -> str:
    """Подставить букву линейки выбранной модели в обобщённый лейбл позиции.

    `foundation_s_f_*`            «… ВЕСТА-С/Ф/П, …»      → «… ВЕСТА-{line}, …»
    `foundation_lite/std_sl_fl_*` «… ВЕСТА-СЛ/ФЛ, …»      → «… ВЕСТА-{line}, …»
    `frame_*`                     «… ВЕСТА-С(Ф)/ФЛ(СЛ), …» → «… ВЕСТА-{line}, …»
    `ramp_set_f_s`                «… ВЕСТА-Ф/С …»          → «… ВЕСТА-{line} …»
    `ramp_set_fl_sl`              «… ВЕСТА-ФЛ/СЛ …»        → «… ВЕСТА-{line} …»

    Прочие ключи и лейблы возвращаются без изменений.
    """
    if not label:
        return label
    if item_key.startswith("foundation_"):
        if item_key.startswith("foundation_s_f_"):
            if model_line in _FOUNDATION_S_F_LINES:
                return label.replace(_FOUNDATION_S_F_PLACEHOLDER, model_line)
            return label
        if item_key.startswith(("foundation_lite_sl_fl_", "foundation_std_sl_fl_")):
            if model_line in _FOUNDATION_SL_FL_LINES:
                return label.replace(_FOUNDATION_SL_FL_PLACEHOLDER, model_line)
            return label
        return label
    if item_key.startswith("frame_"):
        if model_line in _FRAME_LINES:
            return label.replace(_FRAME_PLACEHOLDER, model_line)
        return label
    if item_key == "ramp_set_f_s":
        if model_line in _RAMP_F_S_LINES:
            return label.replace(_RAMP_F_S_PLACEHOLDER, model_line)
        return label
    if item_key == "ramp_set_fl_sl":
        if model_line in _RAMP_FL_SL_LINES:
            return label.replace(_RAMP_FL_SL_PLACEHOLDER, model_line)
        return label
    return label


def _foundation_execution_label(execution: str | None) -> str:
    """Фраза типа фундамента для наименования позиции КП."""
    if execution == "приямок":
        return "в приямок"
    if execution == "монолитная_плита":
        return "монолитная плита"
    return "пандусный"


def _foundation_option_name(item_key: str, state: dict[str, Any]) -> str | None:
    """Единое имя позиции варианта 1 «Фундамент под весы»."""
    if not item_key.startswith(("foundation_s_f_", "foundation_lite_", "foundation_std_")):
        return None
    length = state.get("model_length", "")
    model_code = _format_model_code(state)
    execution = _foundation_execution_label(state.get("foundation_execution"))
    return (
        f"Фундамент железобетонный {execution} "
        f"под весы {model_code}, {length}м"
    )


def _option_name(
    entry: dict, opt_state: dict, item_key: str, state: dict[str, Any]
) -> str:
    if item_key == "install_default" and state.get("is_shefmontazh"):
        name = "Шеф-монтаж и пусконаладка"
    elif item_key == "bytovka_weigh_room":
        dimensions = (
            str(opt_state.get("dimensions") or state.get("bytovka_dimensions") or "")
            .strip()
        )
        name = "Весовое помещение (бытовка)"
        if dimensions:
            name = f"{name} {dimensions}"
    else:
        foundation_name = _foundation_option_name(item_key, state)
        if foundation_name is not None:
            name = foundation_name
        else:
            name = resolve_dynamic_option_label(
                item_key, entry.get("label", ""), state.get("model_line", "")
            )
    if opt_state.get("customer_side"):
        name = f"{name} (силами Заказчика)"
    return name


def _iter_valid_custom_items(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Вернуть заполненные произвольные позиции КП."""
    result: list[dict[str, Any]] = []
    for index, item in enumerate(state.get("custom_items") or [], start=1):
        name = str(item.get("name") or "").strip()
        price = int(item.get("price") or 0)
        if not name or price <= 0:
            continue
        item_id = str(item.get("id") or f"custom_{index}")
        result.append({"id": item_id, "name": name, "price": price})
    return result


def _apply_override(
    computed_qty: int,
    computed_price: int,
    override: dict | None,
) -> tuple[int, int, bool]:
    """Применить override поверх вычисленных qty/price. Возвращает (qty, price, is_overridden)."""
    if not override:
        return computed_qty, computed_price, False
    ov_qty = override.get("qty")
    ov_price = override.get("price")
    qty = int(ov_qty) if ov_qty is not None else computed_qty
    price = int(ov_price) if ov_price is not None else computed_price
    is_ov = (ov_qty is not None) or (ov_price is not None)
    return qty, price, is_ov


def resolve_payment_group(item_key: str) -> str:
    """Какой группе оплаты (split_by_items) принадлежит позиция спецификации.

    Группы: scales (модель + ОРИОН + рамы/пандусы/ограждения/навес/люки/конструкция),
    foundation, delivery, installation_and_verification.
    """
    if item_key.startswith("foundation_"):
        return "foundation"
    if item_key.startswith("construction_works_"):
        return "foundation"
    if item_key.startswith(("concrete_base", "road_slabs_", "pag_slabs_")):
        return "foundation"
    if item_key == "delivery_default":
        return "delivery"
    if item_key in ("install_default", "verification_default", "orion_install"):
        return "installation_and_verification"
    # Опоры/кабель-трассы ОРИОН оплачиваются вместе с фундаментом (эталон A1)
    if item_key == "orion_cable_poles":
        return "foundation"
    return "scales"


def build_spec_items(
    state: dict[str, Any], prices: dict, models_json: dict
) -> list[dict]:
    """Собрать упорядоченный список позиций: модель + включённые опции.

    Если в state["spec_items_overrides"][item_key] есть qty/price — применяем.
    """
    items: list[dict] = []
    overrides: dict = state.get("spec_items_overrides", {}) or {}

    model_id = state.get("model_id", "")
    line = state.get("model_line", "")
    price_entry = get_price_by_model_id(prices, model_id)
    model = get_model_by_id(models_json, model_id)
    model_price = state.get("model_price")
    if price_entry is not None:
        if model_price is None:
            model_price = int(price_entry.get("retail", 0))
        qty, price, is_ov = _apply_override(
            1, int(model_price), overrides.get(model_id)
        )
        items.append({
            "num": 1,
            "item_key": model_id,
            "name": _format_model_full_spec_name(
                model, model_id, state, models_json
            ),
            "qty": qty,
            "unit": "шт",
            "price": price,
            "total": price * qty,
            "is_overridden": is_ov,
            "customer_side": False,
            "payment_group": resolve_payment_group(model_id),
            "term_role": resolve_term_role(model_id),
        })

    length = int(state.get("model_length") or 18)
    prices_options = prices.get("options", {})
    options_state = state.get("options", {})

    for block_id in OPTION_BLOCKS_ORDER:
        for key, entry in get_visible_options(prices_options, line, length, block_id):
            opt = options_state.get(key)
            if not opt or not opt.get("enabled"):
                continue
            computed_qty = int(opt.get("qty", 1))
            if opt.get("customer_side"):
                computed_price = 0
            else:
                computed_price = int(opt.get("price", 0))
            qty, price, is_ov = _apply_override(
                computed_qty, computed_price, overrides.get(key)
            )
            items.append({
                "num": len(items) + 1,
                "item_key": key,
                "name": _option_name(entry, opt, key, state),
                "qty": qty,
                "unit": UNIT_BY_BLOCK.get(block_id, "шт"),
                "price": price,
                "total": price * qty,
                "is_overridden": is_ov,
                "customer_side": bool(opt.get("customer_side", False)),
                "payment_group": resolve_payment_group(key),
                "term_role": resolve_term_role(key),
            })

    for custom in _iter_valid_custom_items(state):
        item_key = custom["id"]
        qty, price, is_ov = _apply_override(
            1, int(custom["price"]), overrides.get(item_key)
        )
        items.append({
            "num": len(items) + 1,
            "item_key": item_key,
            "name": custom["name"],
            "qty": qty,
            "unit": "шт",
            "price": price,
            "total": price * qty,
            "is_overridden": is_ov,
            "customer_side": False,
            "payment_group": "scales",
            "term_role": None,
        })

    return items


def build_construction_description(state: dict) -> str:
    """Готовый русский текст описания конструкции для поля ТХ в DOCX.

    Формат совпадает с UI-превью, но plain text (без Markdown-блока цитаты).
    """
    beam = state.get("construction_beam", "") or "—"
    beam_cnt = state.get("construction_beam_count", 0) or 0
    deck = state.get("construction_deck_mm", 0) or 0
    under = state.get("construction_underlining_mm", 0) or 0
    center_beam = state.get("construction_center_beam", "") or ""
    center_beam_count = state.get("construction_center_beam_count", 0) or 0
    is_rail = not center_beam

    if is_rail:
        return (
            f"Конструкция колейная: {beam} {beam_cnt} шт., "
            f"лист настила {deck} мм рифлёный, "
            f"нижний подшив {under} мм"
        )
    return (
        f"Конструкция сплошная: {beam} {beam_cnt} шт., "
        f"{center_beam} {center_beam_count} шт., "
        f"лист настила {deck} мм рифлёный, "
        f"нижний подшив {under} мм"
    )

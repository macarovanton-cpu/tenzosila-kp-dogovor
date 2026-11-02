"""kit_renderer.py — комплект поставки из модели и датчика."""
from __future__ import annotations

_PLATFORM_TYPE_MAP: dict[str, str] = {
    "Сплошная": "сплошного",
    "Колейная": "колейного",
    "Сплошная усиленная": "сплошного усиленного",
}

_SENSOR_TYPE_RU: dict[str, str] = {
    "digital": "цифровой",
    "analog": "аналоговый",
}


def _sensor_designation(line_defaults: dict, sensor: dict) -> str:
    """Полное обозначение датчика без производителя: 'DHM9B-30t'."""
    full = line_defaults.get("default_sensor", "")
    manufacturer = sensor.get("manufacturer", "")
    if manufacturer and full.startswith(manufacturer + " "):
        return full[len(manufacturer) + 1:]
    return full or sensor.get("model", "")


def _junction_box(sensor_type: str, sensors_count: int) -> str:
    """КБТ-N-Ц (digital) или КСТ-N (analog)."""
    if sensor_type == "digital":
        return f"КБТ-{sensors_count}-Ц"
    return f"КСТ-{sensors_count}"


def build_kit_items(
    model: dict,
    line_defaults: dict,
    sensor: dict,
    indicator: dict,
    cable_length_m: int = 20,
) -> list[dict[str, str]]:
    """Сформировать строки комплекта поставки.

    Возвращает [{name: str, qty: str}, ...] для таблицы Kit в spec_v2.
    """
    platform_raw = line_defaults.get("platform_type", "Сплошная")
    platform_adj = _PLATFORM_TYPE_MAP.get(platform_raw, "сплошного")
    sensor_type = sensor.get("type", "digital")
    sensor_type_ru = _SENSOR_TYPE_RU.get(sensor_type, "цифровой")
    sensors_count = model.get("sensors_count", 8)
    sensor_name = _sensor_designation(line_defaults, sensor)
    indicator_model = indicator.get("model", "")
    box = _junction_box(sensor_type, sensors_count)

    return [
        {"name": f"Модульная грузоприемная платформа {platform_adj} типа, шт.", "qty": "1"},
        {"name": f"Датчик весоизмерительный {sensor_type_ru} {sensor_name}, шт.", "qty": str(sensors_count)},
        {"name": f"Терминал весовой {sensor_type_ru} {indicator_model}, шт.", "qty": "1"},
        {"name": f"Коробка соединительная {box}, шт.", "qty": "1"},
        {"name": "Металлорукав в ПВХ-изоляции, компл.", "qty": "1"},
        {"name": "Кабель сигнальный, м", "qty": str(cable_length_m)},
        {"name": "Комплект документации: паспорт/РЭ на весы, паспорт/РЭ на терминал", "qty": "1"},
    ]


def resolve_equipment(
    models_json: dict, specs_json: dict, line: str, equipment: dict | None,
) -> tuple[dict, dict, dict, int]:
    """(line_defaults, sensor, indicator, cable_m) с учётом equipment снапшота КП.

    Пустые/неизвестные sensor_id, indicator_id, cable_m — умолчания линейки.
    line_defaults возвращается с подставленным default_sensor/default_indicator.
    """
    eq = equipment or {}
    ld = dict(models_json.get("line_defaults", {}).get(line, {}))
    alts = models_json.get("equipment_defaults", {})
    for key, block in (("default_sensor", "sensor"), ("default_indicator", "indicator")):
        want = eq.get(block + "_id")
        for alt in alts.get(block, {}).get("alternatives", []):
            if want and alt.get("id") == want:
                ld[key] = alt.get("label", ld.get(key, ""))

    # Подпись — «производитель модель» или одна модель (МВ-150-30t без производителя).
    # Самое длинное совпадение: «Keli ZSFY-D-30t» не должен попасть на «Keli ZSFY».
    sensor: dict = {}
    best = 0
    for s in specs_json.get("sensors", []):
        model = s.get("model", "")
        for cand in (f"{s.get('manufacturer', '')} {model}", model):
            if cand and ld.get("default_sensor", "").startswith(cand) and len(cand) > best:
                sensor, best = s, len(cand)
    indicator = next(
        (t for t in specs_json.get("terminals", [])
         if t.get("model", "") == ld.get("default_indicator", "")),
        {},
    )
    cable = eq.get("cable_m")
    if not isinstance(cable, (int, float)) or cable <= 0:
        cable = ld.get("default_cable_length_m", 20)
    return ld, sensor, indicator, cable

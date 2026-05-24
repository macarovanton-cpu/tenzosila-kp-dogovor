"""tth_context.py — ТТХ плейсхолдеры из модели и датчика."""
from __future__ import annotations


def _format_temp(val: int) -> str:
    return f"+{val}" if val > 0 else str(val)


def build_tth_data(model: dict, sensor: dict) -> dict[str, str]:
    """Вычислить значения ТТХ-плейсхолдеров для spec_v2.

    model  — запись из models.json
    sensor — запись из equipment_specs.json (sensors)
    """
    axle = model.get("axle_loads_t", {})
    axle_single = axle.get("single", "")

    dual = model.get("dual_range")
    if dual and "w1" in dual and "w2" in dual:
        e1 = dual["w1"]["e_kg"]
        e2 = dual["w2"]["e_kg"]
        discreteness = f"{e1}\n{e2}"
    else:
        discreteness = str(model.get("verification_division_kg", ""))

    length = model.get("length_m", "")
    width = model.get("width_m", "")
    dimensions = f"{length}×{width}"

    t_min = sensor.get("temperature_min_c", -30)
    t_max = sensor.get("temperature_max_c", 40)
    temperature = f"От {_format_temp(t_min)} до {_format_temp(t_max)}"

    return {
        "ТТХ_НАГРУЗКА_НА_ОСЬ": str(axle_single),
        "ТТХ_РАССТОЯНИЕ_ДО_ТЕРМИНАЛА": "не более 50 м",
        "ТТХ_ДИСКРЕТНОСТЬ_БЛОК": discreteness,
        "ТТХ_ГАБАРИТЫ": dimensions,
        "ТТХ_ТЕМПЕРАТУРА": temperature,
    }

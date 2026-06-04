"""tth_context.py — ТТХ плейсхолдеры из модели и датчика."""
from __future__ import annotations


def build_tth_data(model: dict, sensor: dict) -> dict[str, str]:
    """Вычислить значения ТТХ-плейсхолдеров для spec_v2.

    model  — запись из models.json
    sensor — запись из equipment_specs.json (sensors)
    """
    axle = model.get("axle_loads_t", {})
    axle_single = axle.get("single", "")

    dual = model.get("dual_range")
    if dual and "w1" in dual and "w2" in dual:
        disc_1 = str(dual["w1"]["e_kg"])
        disc_2 = str(dual["w2"]["e_kg"])
        border_1 = str(int(dual["w1"]["max_load_t"]))
        border_2 = str(int(dual["w2"]["max_load_t"]))
    else:
        disc_1 = str(model.get("verification_division_kg", ""))
        disc_2 = ""
        border_1 = str(model.get("max_load_t", ""))
        border_2 = ""

    length = model.get("length_m", "")
    width = model.get("width_m", "")
    dimensions = f"{length}×{width}"

    def _fmt(val: int) -> str:
        if val < 0:
            return f"–{abs(val)}"
        if val > 0:
            return f"+{val}"
        return "0"

    t_min = sensor.get("temperature_min_c", -30)
    t_max = sensor.get("temperature_max_c", 40)
    temperature = f"от {_fmt(t_min)} до {_fmt(t_max)} °С"

    return {
        "ТТХ_НАГРУЗКА_НА_ОСЬ": str(axle_single),
        "ТТХ_РАССТОЯНИЕ_ДО_ТЕРМИНАЛА": "не более 50 м",
        "ТТХ_ДИСКРЕТНОСТЬ_1": disc_1,
        "ТТХ_ДИСКРЕТНОСТЬ_2": disc_2,
        "ТТХ_ГРАНИЦА_1": border_1,
        "ТТХ_ГРАНИЦА_2": border_2,
        "ТТХ_ГАБАРИТЫ": dimensions,
        "ТТХ_ТЕМПЕРАТУРА": temperature,
    }

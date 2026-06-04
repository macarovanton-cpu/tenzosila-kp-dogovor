"""Тесты tth_context — ТТХ плейсхолдеры из модели и датчика."""
from src.contracts.tth_context import build_tth_data


SENSOR_DEFAULT = {"temperature_min_c": -30, "temperature_max_c": 40}

MODEL_DUAL = {
    "axle_loads_t": {"single": 14, "double": 13, "triple": 12, "quad": 11},
    "length_m": 18,
    "width_m": 3,
    "verification_division_kg": 20,
    "dual_range": {
        "w1": {"max_load_t": 30, "min_load_t": 0.2, "e_kg": 10, "n": 3000},
        "w2": {"max_load_t": 40, "min_load_t": 0.4, "e_kg": 20, "n": 2000},
    },
}

MODEL_SINGLE = {
    "axle_loads_t": {"single": 11},
    "length_m": 12,
    "width_m": 3,
    "verification_division_kg": 10,
    "max_load_t": 40,
}

MODEL_DUAL_C60 = {
    "axle_loads_t": {"single": 14},
    "length_m": 18,
    "width_m": 3,
    "dual_range": {
        "w1": {"max_load_t": 30, "min_load_t": 0.2, "e_kg": 10, "n": 3000},
        "w2": {"max_load_t": 60, "min_load_t": 0.4, "e_kg": 20, "n": 3000},
    },
}

MODEL_DUAL_C80 = {
    "axle_loads_t": {"single": 14},
    "length_m": 18,
    "width_m": 3,
    "dual_range": {
        "w1": {"max_load_t": 60, "min_load_t": 0.4, "e_kg": 20, "n": 3000},
        "w2": {"max_load_t": 80, "min_load_t": 1,   "e_kg": 50, "n": 1600},
    },
}


class TestDualRange:
    def test_discreteness_two_placeholders(self):
        result = build_tth_data(MODEL_DUAL, SENSOR_DEFAULT)
        assert result["ТТХ_ДИСКРЕТНОСТЬ_1"] == "10"
        assert result["ТТХ_ДИСКРЕТНОСТЬ_2"] == "20"

    def test_axle_load(self):
        result = build_tth_data(MODEL_DUAL, SENSOR_DEFAULT)
        assert result["ТТХ_НАГРУЗКА_НА_ОСЬ"] == "14"

    def test_dimensions(self):
        result = build_tth_data(MODEL_DUAL, SENSOR_DEFAULT)
        assert result["ТТХ_ГАБАРИТЫ"] == "18×3"


class TestSingleRange:
    def test_discreteness_single(self):
        result = build_tth_data(MODEL_SINGLE, SENSOR_DEFAULT)
        assert result["ТТХ_ДИСКРЕТНОСТЬ_1"] == "10"
        assert result["ТТХ_ДИСКРЕТНОСТЬ_2"] == ""

    def test_dimensions_12x3(self):
        result = build_tth_data(MODEL_SINGLE, SENSOR_DEFAULT)
        assert result["ТТХ_ГАБАРИТЫ"] == "12×3"


class TestTemperature:
    def test_default_minus30_plus40(self):
        result = build_tth_data(MODEL_DUAL, SENSOR_DEFAULT)
        assert result["ТТХ_ТЕМПЕРАТУРА"] == "от –30 до +40 °С"

    def test_arctic_minus50_plus50(self):
        sensor = {"temperature_min_c": -50, "temperature_max_c": 50}
        result = build_tth_data(MODEL_DUAL, sensor)
        assert result["ТТХ_ТЕМПЕРАТУРА"] == "от –50 до +50 °С"

    def test_zero_no_plus(self):
        sensor = {"temperature_min_c": 0, "temperature_max_c": 40}
        result = build_tth_data(MODEL_DUAL, sensor)
        assert result["ТТХ_ТЕМПЕРАТУРА"] == "от 0 до +40 °С"


class TestConstant:
    def test_terminal_distance(self):
        result = build_tth_data(MODEL_DUAL, SENSOR_DEFAULT)
        assert result["ТТХ_РАССТОЯНИЕ_ДО_ТЕРМИНАЛА"] == "не более 50 м"


class TestBoundaries:
    def test_dual_40(self):
        r = build_tth_data(MODEL_DUAL, SENSOR_DEFAULT)
        assert r["ТТХ_ГРАНИЦА_1"] == "30"
        assert r["ТТХ_ГРАНИЦА_2"] == "40"

    def test_dual_60(self):
        r = build_tth_data(MODEL_DUAL_C60, SENSOR_DEFAULT)
        assert r["ТТХ_ГРАНИЦА_1"] == "30"
        assert r["ТТХ_ГРАНИЦА_2"] == "60"

    def test_dual_80(self):
        r = build_tth_data(MODEL_DUAL_C80, SENSOR_DEFAULT)
        assert r["ТТХ_ГРАНИЦА_1"] == "60"
        assert r["ТТХ_ГРАНИЦА_2"] == "80"

    def test_single_range(self):
        r = build_tth_data(MODEL_SINGLE, SENSOR_DEFAULT)
        assert r["ТТХ_ГРАНИЦА_1"] == "40"
        assert r["ТТХ_ГРАНИЦА_2"] == ""

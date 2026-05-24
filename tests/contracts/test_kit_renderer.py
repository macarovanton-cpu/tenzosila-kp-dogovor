"""Тесты kit_renderer — комплект поставки из модели."""
from src.contracts.kit_renderer import build_kit_items


MODEL_8 = {"sensors_count": 8}
MODEL_10 = {"sensors_count": 10}

LINE_S = {
    "platform_type": "Сплошная",
    "default_sensor": "Zemic DHM9B-30t",
    "default_indicator": "ТИТАН 3ЦС",
    "default_cable_length_m": 20,
}

LINE_F = {
    "platform_type": "Колейная",
    "default_sensor": "Zemic DHM9B-30t",
    "default_indicator": "ТИТАН 3ЦС",
    "default_cable_length_m": 20,
}

SENSOR_DIGITAL = {"manufacturer": "Zemic", "model": "DHM9B", "type": "digital"}
SENSOR_ANALOG = {"manufacturer": "Zemic", "model": "HM9B", "type": "analog"}

INDICATOR = {"model": "ТИТАН 3ЦС", "compatible_sensors": "digital"}


class TestDigitalSensor:
    def test_junction_box_kbt(self):
        items = build_kit_items(MODEL_8, LINE_S, SENSOR_DIGITAL, INDICATOR)
        box_item = items[3]
        assert "КБТ-8-Ц" in box_item["name"]

    def test_sensor_count_8(self):
        items = build_kit_items(MODEL_8, LINE_S, SENSOR_DIGITAL, INDICATOR)
        sensor_item = items[1]
        assert sensor_item["qty"] == "8"

    def test_sensor_label_digital(self):
        items = build_kit_items(MODEL_8, LINE_S, SENSOR_DIGITAL, INDICATOR)
        assert "цифровой" in items[1]["name"]

    def test_sensor_designation(self):
        items = build_kit_items(MODEL_8, LINE_S, SENSOR_DIGITAL, INDICATOR)
        assert "DHM9B-30t" in items[1]["name"]


class TestAnalogSensor:
    def test_junction_box_kst(self):
        line = dict(LINE_S, default_sensor="Zemic HM9B-30t")
        items = build_kit_items(MODEL_8, line, SENSOR_ANALOG, INDICATOR)
        box_item = items[3]
        assert "КСТ-8" in box_item["name"]
        assert "Ц" not in box_item["name"]

    def test_sensor_label_analog(self):
        line = dict(LINE_S, default_sensor="Zemic HM9B-30t")
        items = build_kit_items(MODEL_8, line, SENSOR_ANALOG, INDICATOR)
        assert "аналоговый" in items[1]["name"]


class TestSensorsCount:
    def test_ten_sensors(self):
        items = build_kit_items(MODEL_10, LINE_S, SENSOR_DIGITAL, INDICATOR)
        assert items[1]["qty"] == "10"
        assert "КБТ-10-Ц" in items[3]["name"]


class TestPlatformType:
    def test_solid(self):
        items = build_kit_items(MODEL_8, LINE_S, SENSOR_DIGITAL, INDICATOR)
        assert "сплошного" in items[0]["name"]

    def test_track(self):
        items = build_kit_items(MODEL_8, LINE_F, SENSOR_DIGITAL, INDICATOR)
        assert "колейного" in items[0]["name"]


class TestItemCount:
    def test_seven_items(self):
        items = build_kit_items(MODEL_8, LINE_S, SENSOR_DIGITAL, INDICATOR)
        assert len(items) == 7

    def test_cable_length(self):
        items = build_kit_items(MODEL_8, LINE_S, SENSOR_DIGITAL, INDICATOR, cable_length_m=50)
        cable = items[5]
        assert cable["qty"] == "50"

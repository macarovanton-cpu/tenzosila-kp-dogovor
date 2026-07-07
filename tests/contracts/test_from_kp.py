"""Тесты build_specification_from_kp_snapshot."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest


def _load(fname: str) -> dict:
    return json.loads(Path(f"data/{fname}").read_text(encoding="utf-8"))


PRICES = _load("prices.json")
MODELS = _load("models.json")
PAYMENT_TERMS = _load("payment_terms.json")


def _make_kp_row(
    model_line: str = "С",
    model_max: int = 60,
    model_length: int = 18,
    model_width: float | None = None,
    model_price: int | None = 2835000,
    options: dict | None = None,
    payment_preset: str = "split_by_items",
    payment_split_state: dict | None = None,
    custom_items: list[dict] | None = None,
    installation_scope: str | None = None,
) -> dict:
    model_data = {
        "line": model_line,
        "max": model_max,
        "length": model_length,
        "price": model_price,
    }
    if model_width is not None:
        model_data["width"] = model_width
    return {
        "kp_number": "КП-2026-001",
        "model_id": f"vesta-{model_line.lower()}-{model_max}-{model_length}",
        "total_price": 0,
        "data": {
            "model": model_data,
            "equipment": {"sensor_id": "zemic_dhm9b_30t", "indicator_id": "titan_3cs", "cable_m": 20},
            "options": options or {},
            "custom_items": custom_items or [],
            "installation_scope": installation_scope,
            "spec_overrides": {},
            "payment": {
                "preset_id": payment_preset,
                "days": 5,
                "custom_text": "",
                "split_state": payment_split_state or {"scales": {"prepay": 50, "postpay": 50}},
                "v1_prepay": 50,
                "v2_prepay": 30,
                "v2_preship": 40,
                "v3_days": 15,
                "v3_trigger_id": "after_installation",
            },
            "metadata": {"kp_valid_days": 15, "warranty_months": 36},
            "construction": {
                "beam": "Двутавр 20Б1", "beam_count": 4,
                "center_beam": "", "center_beam_count": 0,
                "deck_mm": 6, "underlining_mm": 4,
            },
            "metrology": {"is_dual_range": False},
        },
    }


class TestBuildSpecFromKpSnapshot:
    def test_minimal_has_required_keys(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        kp_row = _make_kp_row()
        spec = build_specification_from_kp_snapshot(kp_row, PRICES, MODELS, PAYMENT_TERMS)

        required = {
            "СПЕЦ_НДС", "СПЕЦ_МОДЕЛЬ_КРАТКОЕ", "СПЕЦ_МАКС_НАГРУЗКА",
            "СПЕЦ_П1_НАИМЕНОВАНИЕ", "СПЕЦ_П1_СУММА",
            "СПЕЦ_П2_НАИМЕНОВАНИЕ", "СПЕЦ_П2_СУММА",
            "СПЕЦ_П3_НАИМЕНОВАНИЕ", "СПЕЦ_П3_СУММА",
            "СПЕЦ_П4_НАИМЕНОВАНИЕ", "СПЕЦ_П4_СУММА",
            "СПЕЦ_П5_НАИМЕНОВАНИЕ", "СПЕЦ_П5_СУММА",
            "СПЕЦ_ИТОГО", "СПЕЦ_ИТОГО_ПРОПИСЬ",
            "СПЕЦ_ОПЛАТА_П1", "СПЕЦ_ОПЛАТА_П2", "СПЕЦ_ОПЛАТА_П3",
            "СПЕЦ_ОПЛАТА_П4", "СПЕЦ_ОПЛАТА_П5", "СПЕЦ_ОПЛАТА_П6",
            "СПЕЦ_СРОК_ПОСТАВКИ", "СПЕЦ_СРОК_ФУНДАМЕНТ", "СПЕЦ_СРОК_МОНТАЖ",
        }
        assert required.issubset(spec.keys())

    def test_minimal_nds_is_22(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_НДС"] == "22"

    def test_model_краткое_формат(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(model_line="С", model_max=60, model_length=18),
            PRICES, MODELS, PAYMENT_TERMS,
        )
        assert spec["СПЕЦ_МОДЕЛЬ_КРАТКОЕ"] == "ВЕСТА-С-60-18"

    def test_no_foundation_fields_empty(self):
        """Без фундамента П2_НАИМЕНОВАНИЕ и П2_СУММА пустые."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_П2_НАИМЕНОВАНИЕ"] == ""
        assert spec["СПЕЦ_П2_СУММА"] == ""

    def test_with_foundation_option(self):
        """С фундаментом П2_НАИМЕНОВАНИЕ содержит полное имя фундамента."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        foundation_key = None
        for k in PRICES.get("options", {}):
            if k.startswith("foundation_s_f_") and "18" in k:
                foundation_key = k
                break
        if foundation_key is None:
            pytest.skip("foundation_s_f_18 not found in prices.json")

        options = {
            foundation_key: {"price": 350000, "qty": 1, "customer_side": False,
                             "retail": 350000, "dealer_is_synthetic": False}
        }
        kp_row = _make_kp_row(options=options)
        spec = build_specification_from_kp_snapshot(kp_row, PRICES, MODELS, PAYMENT_TERMS)
        assert "Фундамент" in spec["СПЕЦ_П2_НАИМЕНОВАНИЕ"]
        assert "ВЕСТА-С" in spec["СПЕЦ_П2_НАИМЕНОВАНИЕ"]
        assert spec["СПЕЦ_П2_СУММА"] != ""

    def test_итого_equals_sum_of_positions(self):
        """СПЕЦ_ИТОГО == сумма всех П*_СУММА."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        total_str = spec["СПЕЦ_ИТОГО"].replace(" ", "").replace("\xa0", "")
        total = int(total_str) if total_str else 0

        parts_sum = 0
        for i in range(1, 6):
            key = f"СПЕЦ_П{i}_СУММА"
            val = spec.get(key, "").replace(" ", "").replace("\xa0", "")
            if val:
                parts_sum += int(val)

        assert total == parts_sum, f"ИТОГО {total} != sum(П1..П5) {parts_sum}"

    def test_итого_пропись_not_empty(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_ИТОГО_ПРОПИСЬ"] != ""

    def test_оплата_п1_not_empty(self):
        """Хотя бы П1 условий оплаты заполнен."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_ОПЛАТА_П1"] != ""

    def test_срок_поставки_numeric(self):
        """СПЕЦ_СРОК_ПОСТАВКИ — строка с числом."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_СРОК_ПОСТАВКИ"].isdigit()

    def test_no_заказчик_fields(self):
        """ЗАКАЗЧИК_* поля НЕ должны быть в возвращаемом dict."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        zakazchik_keys = [k for k in spec if k.startswith("ЗАКАЗЧИК_")]
        assert zakazchik_keys == []

    def test_empty_length_does_not_crash(self):
        """Битый снапшот с length='' не роняет страницу (регресс)."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        kp_row = _make_kp_row()
        kp_row["data"]["model"]["length"] = ""
        spec = build_specification_from_kp_snapshot(kp_row, PRICES, MODELS, PAYMENT_TERMS)
        assert spec["СПЕЦ_НДС"] == "22"

    def test_empty_option_qty_price_does_not_crash(self):
        """Опция с qty='' и price='' (customer_side=False) не роняет страницу."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        kp_row = _make_kp_row(options={
            "delivery_default": {
                "qty": "", "price": "", "customer_side": False,
                "retail": 0, "dealer_is_synthetic": False,
            },
        })
        spec = build_specification_from_kp_snapshot(kp_row, PRICES, MODELS, PAYMENT_TERMS)
        assert spec["СПЕЦ_НДС"] == "22"

    def test_empty_model_price_does_not_crash(self):
        """Снапшот с model.price='' не роняет страницу (падает на retail модели)."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        kp_row = _make_kp_row(model_price="")
        spec = build_specification_from_kp_snapshot(kp_row, PRICES, MODELS, PAYMENT_TERMS)
        assert spec["СПЕЦ_НДС"] == "22"

    def test_row_without_data_yields_empty_spec(self):
        """Строка без ключа `data` (как из list_recent_kps) → тихо пустая спец.

        Документирует ловушку: дропдаун «Последние КП» отдаёт строку без снапшота
        (колонка `data` не входит в _KP_LIST_COLS). Функция не роняется, но
        спецификация пуста — суммы и ИТОГО пустые, генерить нечего. Дозагрузка
        полного снапшота (get_kp_by_number) на странице — обход этой ловушки.
        """
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        kp_row = {  # ровно то, что возвращает list_recent_kps: без `data`
            "kp_number": "КП-2026-001",
            "model_id": "vesta-с-60-18",
            "total_price": 2835000,
        }
        spec = build_specification_from_kp_snapshot(kp_row, PRICES, MODELS, PAYMENT_TERMS)
        assert spec["СПЕЦ_ИТОГО"] == ""
        assert spec["СПЕЦ_П1_СУММА"] == ""
        assert all(spec[f"СПЕЦ_П{i}_НАИМЕНОВАНИЕ"] == "" for i in range(2, 6))


class TestBuildSpecRowsFromSnapshot:
    """Тесты build_spec_rows_from_snapshot."""

    def _make_full_kp_row(self, line="С", max_t=60, length=18, price=2835000,
                           foundation_key="foundation_s_f_18",
                           foundation_price=350000,
                           verification_customer_side=False) -> dict:
        options = {
            foundation_key: {
                "qty": 1, "price": foundation_price,
                "retail": foundation_price, "customer_side": False,
            },
            "delivery_default": {
                "qty": 1, "price": 50000,
                "retail": 50000, "customer_side": False,
            },
            "install_default": {
                "qty": 1, "price": 80000,
                "retail": 80000, "customer_side": False,
            },
            "verification_default": {
                "qty": 1, "price": 30000,
                "retail": 30000, "customer_side": verification_customer_side,
            },
        }
        return _make_kp_row(
            model_line=line, model_max=max_t, model_length=length,
            model_price=price, options=options,
        )

    def test_base_case_five_rows(self):
        """Базовый кейс: модель + фундамент + доставка + монтаж + поверка → 5 строк."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        rows = build_spec_rows_from_snapshot(self._make_full_kp_row())
        assert len(rows) == 5

    def test_base_case_canonical_names(self):
        """Проверка канонических формулировок всех 5 строк."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        rows = build_spec_rows_from_snapshot(self._make_full_kp_row())
        names = [r["name"] for r in rows]
        assert names[0] == "Весы автомобильные ВЕСТА-С-60-18-Ц, max 60т, размеры платформы 18х3м"
        assert names[1] == "Фундамент железобетонный под весы автомобильные ВЕСТА-С, 18м"
        assert names[2] == "Доставка весов до объекта"
        assert names[3] == "Монтаж автомобильных весов"
        assert names[4] == "Поверка автомобильных весов с доставкой эталонов"

    def test_model_name_uses_nonstandard_width_from_snapshot(self):
        """model.width из snapshot попадает в договорную строку весов."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        rows = build_spec_rows_from_snapshot(
            _make_kp_row(model_width=3.5)
        )

        assert rows[0]["name"] == (
            "Весы автомобильные ВЕСТА-С-60-18-Ц, "
            "max 60т, размеры платформы 18х3.5м"
        )

    def test_model_name_defaults_to_3m_for_old_snapshot(self):
        """Старый snapshot без model.width остаётся с шириной 3м."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        rows = build_spec_rows_from_snapshot(_make_kp_row())

        assert "размеры платформы 18х3м" in rows[0]["name"]

    def test_customer_side_verification_price_is_zakazchik(self):
        """customer_side=True → price_display='ЗАКАЗЧИК', не учитывается в итого."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        rows = build_spec_rows_from_snapshot(
            self._make_full_kp_row(verification_customer_side=True)
        )
        assert len(rows) == 5
        verify_row = next(r for r in rows if "Поверка" in r["name"])
        assert verify_row["customer_side"] is True
        assert verify_row["price_display"] == "ЗАКАЗЧИК"
        # итого не включает поверку
        total = sum(r["price"] for r in rows if not r["customer_side"])
        assert total == 2835000 + 350000 + 50000 + 80000

    def test_qty_zero_row_skipped(self):
        """Опция с qty=0 не попадает в строки."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        kp_row = _make_kp_row(options={
            "delivery_default": {"qty": 0, "price": 50000, "retail": 50000, "customer_side": False},
        })
        rows = build_spec_rows_from_snapshot(kp_row)
        names = [r["name"] for r in rows]
        assert not any("Доставка" in n for n in names)

    def test_unknown_option_key_logged_and_included(self, caplog):
        """Неизвестный ключ → WARNING в логе, строка добавляется с raw-ключом."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        kp_row = _make_kp_row(options={
            "unknown_future_option_42": {"qty": 1, "price": 99000, "retail": 99000, "customer_side": False},
        })
        with caplog.at_level(logging.WARNING, logger="src.contracts.from_kp"):
            rows = build_spec_rows_from_snapshot(kp_row)
        assert any("unknown_future_option_42" in msg for msg in caplog.messages)
        assert any(r["name"] == "unknown_future_option_42" for r in rows)

    def test_bytovka_row_uses_dimensions_from_snapshot(self):
        """Договорные строки получают имя бытовки с габаритами."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        kp_row = _make_kp_row(options={
            "bytovka_weigh_room": {
                "qty": 1, "price": 650000, "retail": 650000,
                "customer_side": False, "dimensions": "6×2.4м",
            },
        })

        rows = build_spec_rows_from_snapshot(kp_row)

        assert any(
            r["name"] == "Весовое помещение (бытовка) 6×2.4м"
            and r["price"] == 650000
            for r in rows
        )

    def test_custom_items_rows_from_snapshot(self):
        """custom_items из snapshot попадают в договорные строки."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        kp_row = _make_kp_row(custom_items=[
            {"name": "Дополнительный шкаф", "price": 120000},
        ])

        rows = build_spec_rows_from_snapshot(kp_row)

        assert any(
            r["name"] == "Дополнительный шкаф" and r["price"] == 120000
            for r in rows
        )

    def test_foundation_formulations_all_three_types(self):
        """Проверка формулировок для всех 3 типов фундамента."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot

        # Тип 1: foundation_s_f_{N} для линейки С
        rows_sf = build_spec_rows_from_snapshot(
            self._make_full_kp_row(line="С", length=18, foundation_key="foundation_s_f_18")
        )
        f_names_sf = [r["name"] for r in rows_sf if "Фундамент" in r["name"]]
        assert f_names_sf == ["Фундамент железобетонный под весы автомобильные ВЕСТА-С, 18м"]

        # Тип 2: foundation_lite_sl_fl_{N} для линейки СЛ
        rows_lite = build_spec_rows_from_snapshot(
            self._make_full_kp_row(line="СЛ", length=18, foundation_key="foundation_lite_sl_fl_18")
        )
        f_names_lite = [r["name"] for r in rows_lite if "Фундамент" in r["name"]]
        assert f_names_lite == ["Фундамент пандусный «ЛАЙТ» под весы автомобильные ВЕСТА-СЛ, 18м"]

        # Тип 3: foundation_std_sl_fl_{N} для линейки ФЛ
        rows_std = build_spec_rows_from_snapshot(
            self._make_full_kp_row(line="ФЛ", length=24, foundation_key="foundation_std_sl_fl_24")
        )
        f_names_std = [r["name"] for r in rows_std if "Фундамент" in r["name"]]
        assert f_names_std == ["Фундамент пандусный «Стандарт» под весы автомобильные ВЕСТА-ФЛ, 24м"]

    def test_model_name_for_all_lines(self):
        """Формирование имени модели для всех линеек."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        for line in ("С", "СЛ", "Ф", "ФЛ", "П"):
            kp_row = _make_kp_row(model_line=line, model_max=40, model_length=12)
            rows = build_spec_rows_from_snapshot(kp_row)
            model_row = rows[0]
            expected = f"Весы автомобильные ВЕСТА-{line}-40-12-Ц, max 40т, размеры платформы 12х3м"
            assert model_row["name"] == expected, f"Line {line}: {model_row['name']!r}"

    def test_specification_items_use_nonstandard_width_from_snapshot(self):
        """SpecItem для spec_v2 тоже использует ширину из snapshot."""
        from src.contracts.from_kp import build_specification_items
        items = build_specification_items(_make_kp_row(model_width=4.0))

        assert items[0]["name"] == (
            "Весы автомобильные ВЕСТА-С-60-18-Ц, "
            "max 60т, размеры платформы 18х4м"
        )

    def test_specification_items_custom_items_payment_group(self):
        """custom_items становятся кастомными SpecItem с корректным payment_group."""
        from src.contracts.from_kp import build_specification_items

        items = build_specification_items(_make_kp_row(custom_items=[
            {"name": "Дополнительный шкаф", "price": 120000},
            {"name": "Доставка спецтехники", "price": 50000},
        ]))

        shkaf = next(i for i in items if i["name"] == "Дополнительный шкаф")
        assert shkaf["is_custom"] is True
        assert shkaf["source"] == "custom"
        assert shkaf["payment_group"] == "scales"
        assert shkaf["total"] == 120000

        delivery = next(i for i in items if i["name"] == "Доставка спецтехники")
        assert delivery["payment_group"] == "delivery"

    def test_specification_items_installation_scope_from_snapshot(self):
        """installation_scope из snapshot задаёт scope монтажа в SpecItem."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "install_default": {
                "qty": 1, "price": 180000, "retail": 180000,
                "customer_side": False,
            },
        }

        items = build_specification_items(
            _make_kp_row(options=opts, installation_scope="shefmontazh")
        )

        install = next(i for i in items if i["id"] == "installation")
        assert install["name"] == "Шеф-монтаж и пусконаладка"
        assert install["metadata"]["scope"] == "shefmontazh"


class TestResolveOptionName:
    """Тесты _resolve_option_name с prices-lookup."""

    def test_fence_norma_resolves_from_prices(self):
        """fence_norma_20 → label из prices.json, не raw-ключ."""
        from src.contracts.from_kp import _resolve_option_name
        name = _resolve_option_name("fence_norma_20", "С", prices=PRICES)
        assert name == "Ограждение НОРМА высота 200мм, 20м"

    def test_ramp_set_resolves_from_prices(self):
        """ramp_set_fl_sl → label из prices.json."""
        from src.contracts.from_kp import _resolve_option_name
        name = _resolve_option_name("ramp_set_fl_sl", "ФЛ", prices=PRICES)
        assert name == "Комплект пандусов под весы ВЕСТА-ФЛ/СЛ (L=2,9м)"

    def test_frame_resolves_from_prices(self):
        """frame_18 → label из prices.json, не raw-ключ."""
        from src.contracts.from_kp import _resolve_option_name
        name = _resolve_option_name("frame_18", "С", prices=PRICES)
        assert name == "Рама под весы ВЕСТА-С(Ф)/ФЛ(СЛ), 18м"

    def test_ramp_set_f_s_resolves_from_prices(self):
        """ramp_set_f_s → label из prices.json."""
        from src.contracts.from_kp import _resolve_option_name
        name = _resolve_option_name("ramp_set_f_s", "Ф", prices=PRICES)
        assert name == "Комплект пандусов под весы ВЕСТА-Ф/С (L=3,9м)"

    def test_foundation_pattern_not_overridden_by_prices(self):
        """foundation_s_f_18 с prices=PRICES всё равно использует паттерн с {line}."""
        from src.contracts.from_kp import _resolve_option_name
        name = _resolve_option_name("foundation_s_f_18", "С", prices=PRICES)
        assert name is not None
        assert "ВЕСТА-С" in name
        assert "Фундамент" in name

    def test_unknown_key_warns_and_returns_none(self, caplog):
        """Совсем неизвестный ключ → None + WARNING, даже если prices передан."""
        import logging
        from src.contracts.from_kp import _resolve_option_name
        with caplog.at_level(logging.WARNING, logger="src.contracts.from_kp"):
            name = _resolve_option_name("ghost_option_999", "С", prices=PRICES)
        assert name is None
        assert any("ghost_option_999" in msg for msg in caplog.messages)

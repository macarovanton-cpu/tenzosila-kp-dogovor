"""Тесты reconstruct_kp_state — чистая реконструкция state КП из снапшота.

Без сети/Supabase: снапшот собираем build_kp_snapshot из реалистичного
post-render state, оборачиваем в kp_row (колонки + data) и разворачиваем обратно.
"""
from __future__ import annotations

from datetime import date

from src.data_loader import load_prices
from src.storage.kp_restore import _is_purgeable, reconstruct_kp_state
from src.storage.snapshot_builder import build_kp_snapshot

MODEL_ID = "vesta-с-60-18"


def _post_render_state() -> dict:
    """State как ПОСЛЕ рендера конфигуратора (model_price — конкретное число)."""
    return {
        "kp_number": "КП-2026-777",
        "kp_date": date(2026, 5, 20),
        "kp_valid_days": 20,
        "warranty_months": 48,
        "client_name": "ООО Ромашка",
        "manager_id": "ivanov",
        "model_line": "С",
        "model_max": 60,
        "model_length": 18,
        "model_id": MODEL_ID,
        "model_price": 1_906_000,  # конкретное post-render, != retail
        "platform_width_m": 3.0,
        "sensor_id": "zemic_dhm9b_30t",
        "indicator_id": "titan_3cs",
        "cable_m": 25,
        "is_dual_range": True,
        "construction_beam": "Двутавр 25Б1",
        "construction_beam_count": 5,
        "construction_center_beam": "Швеллер 16",
        "construction_center_beam_count": 2,
        "construction_deck_mm": 8,
        "construction_underlining_mm": 5,
        "is_shefmontazh": True,
        "foundation_execution": "монолитная_плита",
        "bytovka_dimensions": "6×2.4м",
        "options": {
            "foundation_s_f_18": {
                "enabled": True, "price": 500_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 520_000, "dealer_is_synthetic": True,
                "block": "foundation_and_base",
            },
            "verification_default": {
                "enabled": True, "price": 0, "qty": 1,
                "customer_side": True, "is_on_request": False,
                "retail": 45_000, "dealer_is_synthetic": False,
                "block": "installation_and_verification",
            },
            "install_default": {
                "enabled": True, "price": 120_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 120_000, "dealer_is_synthetic": False,
                "block": "installation_and_verification",
            },
            "ramps_pair": {
                "enabled": True, "price": 85_000, "qty": 2,
                "customer_side": False, "is_on_request": False,
                "retail": 90_000, "dealer_is_synthetic": True,
                "block": "ramps",
            },
            "bytovka_weigh_room": {
                "enabled": True, "price": 650_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 650_000, "dealer_is_synthetic": False,
                "block": "misc", "dimensions": "6×2.4м",
            },
        },
        "custom_items": [
            {"id": "custom_1", "name": "Доп шкаф", "price": 120_000}
        ],
        "custom_item_next_id": 2,
        "spec_items_overrides": {MODEL_ID: {"price": 1_950_000}},
        "total_term_days": 42,
        "total_term_days_user_set": True,
        "payment_preset_id": "split_by_items",
        "payment_days": 7,
        "payment_custom_text": "",
        "payment_split_state": {"scales": {"prepay": 30, "postpay": 70}},
        "payment_v1_prepay": 50,
        "payment_v2_prepay": 30,
        "payment_v2_preship": 40,
        "payment_v3_days": 15,
        "payment_v3_trigger_id": "after_installation",
    }


def _kp_row(state: dict, kp_date: str = "2026-05-20") -> dict:
    """Обернуть snapshot в строку kps (колонки + data JSONB)."""
    return {
        "kp_number": state["kp_number"],
        "client_name": state["client_name"],
        "manager_id": state["manager_id"],
        "model_id": state["model_id"],
        "kp_date": kp_date,
        "data": build_kp_snapshot(state),
    }


def test_roundtrip_legacy_custom_item_scope_is_byte_identical():
    """Старый снапшот без scope → restore → пересейв байт-идентичен (не выдумывает scope)."""
    state = _post_render_state()  # custom item без поля scope (legacy)
    snap1 = build_kp_snapshot(state)
    assert snap1["custom_items"] == [{"name": "Доп шкаф", "price": 120_000}]

    out = reconstruct_kp_state(_kp_row(state), load_prices())
    assert out["custom_items"][0]["scope"] == "other"  # restore проставил дефолт

    snap2 = build_kp_snapshot(out)
    assert snap2["custom_items"] == snap1["custom_items"]  # пересейв не добавил scope


def test_round_trip_plain_keys():
    """build_kp_snapshot → reconstruct_kp_state: плоские ключи совпадают."""
    state = _post_render_state()
    out = reconstruct_kp_state(_kp_row(state), load_prices())

    # Колонки
    assert out["kp_number"] == "КП-2026-777"
    assert out["client_name"] == "ООО Ромашка"
    assert out["manager_id"] == "ivanov"
    assert out["model_id"] == MODEL_ID
    assert out["kp_date"] == date(2026, 5, 20)

    # metadata + срок
    assert out["kp_valid_days"] == 20
    assert out["warranty_months"] == 48
    assert out["total_term_days"] == 42
    assert out["total_term_days_user_set"] is True

    # model / каскад
    assert out["model_line"] == "С"
    assert out["model_max"] == 60
    assert out["model_length"] == 18
    assert out["platform_width_m"] == 3.0
    assert out["model_price"] == 1_906_000

    # equipment / metrology / construction
    assert out["sensor_id"] == "zemic_dhm9b_30t"
    assert out["indicator_id"] == "titan_3cs"
    assert out["cable_m"] == 25
    assert out["is_dual_range"] is True
    assert out["construction_beam"] == "Двутавр 25Б1"
    assert out["construction_center_beam_count"] == 2
    assert out["construction_deck_mm"] == 8

    # foundation / монтаж
    assert out["foundation_execution"] == "монолитная_плита"
    assert out["is_shefmontazh"] is True
    assert out["bytovka_dimensions"] == "6×2.4м"

    # spec overrides / custom / payment
    assert out["spec_items_overrides"] == {MODEL_ID: {"price": 1_950_000}}
    assert out["custom_items"] == [
        {"id": "custom_1", "name": "Доп шкаф", "price": 120_000, "scope": "other"}
    ]
    assert out["custom_item_next_id"] == 2
    assert out["payment_preset_id"] == "split_by_items"
    assert out["payment_days"] == 7
    assert out["payment_split_state"] == {"scales": {"prepay": 30, "postpay": 70}}
    assert out["payment_v3_trigger_id"] == "after_installation"


def test_round_trip_canonical_options():
    state = _post_render_state()
    out = reconstruct_kp_state(_kp_row(state), load_prices())
    opts = out["options"]

    assert set(opts) == {
        "foundation_s_f_18", "verification_default", "install_default",
        "ramps_pair", "bytovka_weigh_room",
    }
    fnd = opts["foundation_s_f_18"]
    assert fnd["enabled"] is True
    assert fnd["price"] == 500_000
    assert fnd["retail"] == 520_000
    assert fnd["dealer_is_synthetic"] is True
    assert opts["ramps_pair"]["qty"] == 2
    assert opts["verification_default"]["customer_side"] is True
    assert opts["bytovka_weigh_room"]["dimensions"] == "6×2.4м"


def test_round_trip_widget_keys():
    """Суффиксные widget-ключи — восстанавливают цену/qty/сторону/фундамент."""
    state = _post_render_state()
    out = reconstruct_kp_state(_kp_row(state), load_prices())
    s = f"__{MODEL_ID}"

    assert out[f"model_price_slider{s}"] == 1_906_000
    assert out[f"opt_foundation_s_f_18_enabled{s}"] is True
    assert out[f"opt_foundation_s_f_18_price{s}"] == 500_000
    assert out[f"opt_foundation_s_f_18_qty{s}"] == 1
    assert out[f"opt_foundation_s_f_18_foundation_execution{s}"] == "монолитная_плита"
    assert out[f"opt_ramps_pair_qty{s}"] == 2
    assert out[f"opt_verification_default_side{s}"] == "Заказчик"
    assert out[f"opt_install_default_shefmontazh{s}"] is True
    assert out[f"opt_bytovka_weigh_room_dimensions{s}"] == "6×2.4м"


def test_model_price_freeze_no_drift():
    """Замороженная цена восстанавливается точно, даже если retail изменился."""
    state = _post_render_state()
    state["model_price"] = 1_234_567  # заведомо != текущего retail
    out = reconstruct_kp_state(_kp_row(state), load_prices())

    assert out["model_price"] == 1_234_567
    assert out[f"model_price_slider__{MODEL_ID}"] == 1_234_567


def test_legacy_snapshot_without_term_and_price_does_not_crash():
    """Старый снапшот без total_term_days и с model.price=None → дефолты."""
    legacy_data = {
        "metadata": {"kp_valid_days": 15, "warranty_months": 36},
        "model": {"line": "С", "max": 60, "length": 18, "width": 3.0, "price": None},
        "equipment": {"sensor_id": "s1", "indicator_id": "i1", "cable_m": 20},
        "construction": {
            "beam": "20Б1", "beam_count": 4, "center_beam": "", "center_beam_count": 0,
            "deck_mm": 6, "underlining_mm": 4,
        },
        "metrology": {"is_dual_range": False},
        "options": {},
        "custom_items": [],
        "spec_overrides": {},
        "installation_scope": None,
        "foundation_execution": None,
        "payment": {"preset_id": "split_by_items", "days": 5},
    }
    kp_row = {
        "kp_number": "OLD-1", "client_name": "X", "manager_id": "ivanov",
        "model_id": MODEL_ID, "kp_date": "2026-01-01", "data": legacy_data,
    }
    prices = load_prices()
    out = reconstruct_kp_state(kp_row, prices)

    assert out["total_term_days"] is None
    assert out["total_term_days_user_set"] is False
    # model.price None → фактическая розница из prices.json
    expected_retail = int(prices["models"][MODEL_ID]["retail"])
    assert out["model_price"] == expected_retail
    assert out[f"model_price_slider__{MODEL_ID}"] == expected_retail
    assert out["options"] == {}
    assert out["custom_items"] == []


def test_purge_radius():
    """_is_purgeable: маски задевают только widget-ключи, не canonical-state."""
    purge = [
        f"opt_foundation_s_f_18_price__{MODEL_ID}",
        "opt_install_default_shefmontazh__vesta-ф-30-12",
        f"model_price_slider__{MODEL_ID}",
        "split_scales_prepay",
        "custom_1_name",
        "custom_2_price",
        "custom_10_delete",
    ]
    keep = [
        "options", "payment_split_state", "custom_items", "custom_item_next_id",
        "custom_item_add", "model_price", "model_line", "model_id", "kp_number",
        "total_term_days", "payment_preset_id", "foundation_execution",
    ]
    for k in purge:
        assert _is_purgeable(k), f"должен чиститься: {k}"
    for k in keep:
        assert not _is_purgeable(k), f"НЕ должен чиститься: {k}"


# --- AppTest smoke: реальный рендер после восстановления -------------------

def _smoke_state() -> dict:
    """Компактный post-render state на дефолтной модели С-60-18 (опции видимы)."""
    state = {k: v for k, v in _post_render_state().items()}
    # Опции, гарантированно видимые для С-60-18, с НЕдефолтными ценами.
    state["options"] = {
        "install_default": {
            "enabled": True, "price": 137_000, "qty": 1,
            "customer_side": False, "is_on_request": False,
            "retail": 150_000, "dealer_is_synthetic": False,
            "block": "installation_and_verification",
        },
    }
    state["is_shefmontazh"] = False
    state["custom_items"] = []
    state["spec_items_overrides"] = {}
    return state


def test_apptest_restore_end_to_end(monkeypatch):
    """Полный рендер после restore: без exception, цена опции восстановлена в виджете."""
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    # Список КП рисуется через load-секцию — глушим сеть (иначе зависание/креды).
    import src.ui.load_kp_section as load_sec
    monkeypatch.setattr(load_sec, "list_recent_kps", lambda *a, **k: [])
    monkeypatch.setattr(load_sec, "search_kps_by_contractor", lambda *a, **k: [])

    app_path = str(Path(__file__).resolve().parent.parent / "src" / "app.py")
    at = AppTest.from_file(app_path, default_timeout=60).run()
    assert not at.exception, at.exception

    # Стейджим restore ровно как кнопка _stage_restore.
    at.session_state["_kp_restore_row"] = _kp_row(_smoke_state())
    at.session_state["_kp_restore_pending"] = True
    at.run()
    assert not at.exception, at.exception

    # Плоские поля восстановлены.
    assert at.session_state["kp_number"] == "КП-2026-777"
    assert at.session_state["client_name"] == "ООО Ромашка"
    assert at.session_state["model_price"] == 1_906_000
    assert at.session_state["warranty_months"] == 48
    assert at.session_state["total_term_days"] == 42
    assert at.session_state["is_dual_range"] is True

    mid = at.session_state["model_id"]
    assert mid == MODEL_ID
    # ЯДРО: цена опции восстановлена в РЕАЛЬНОМ виджете (session_state победил value=).
    assert at.session_state[f"opt_install_default_price__{mid}"] == 137_000
    assert at.session_state[f"opt_install_default_enabled__{mid}"] is True
    # Канонический options пересобрался из виджетов с восстановленной ценой.
    assert at.session_state["options"]["install_default"]["price"] == 137_000
    # Предупреждение о перезаписи показано (номер совпадает с загруженным).
    assert at.session_state["_kp_loaded_number"] == "КП-2026-777"
    assert any("перезап" in w.value.lower() for w in at.warning)

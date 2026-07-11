"""Тесты вью обновления прайса: конверсия delta↔PriceItem + smoke потока."""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.admin import price_update_view, price_write_service
from src.admin.price_models import PriceItem
from src.admin.price_update_view import apply_editor_delta, items_to_dataframe

APP_PATH = str(Path(__file__).resolve().parents[2] / "src" / "app.py")


def _model() -> PriceItem:
    return PriceItem(
        item_type="model",
        key="vesta-фл-60-18",
        label="ВЕСТА-ФЛ 60т-18м",
        price_retail=1668432,
        price_dealer_ru=1534957,
        discount_pct=8,
        price_class="A_retail_and_dealer",
        on_request=False,
        allow_customer_value=False,
        range_min=None,
        range_max=None,
        applies_to_lines=[],
        applies_to_lengths=[],
        raw_payload={"source": "dealer", "retail": 1668432},
    )


def _option() -> PriceItem:
    return PriceItem(
        item_type="option",
        key="frame_18",
        label="Рама 18м",
        price_retail=300000,
        price_dealer_ru=None,
        discount_pct=None,
        price_class="C_manual_range",
        on_request=False,
        allow_customer_value=True,
        range_min=200000,
        range_max=400000,
        applies_to_lines=["Ф", "С"],
        applies_to_lengths=[18],
        raw_payload={"source": "retail", "notes": ["спец"]},
    )


def _empty_delta() -> dict:
    return {"edited_rows": {}, "added_rows": [], "deleted_rows": []}


# ──────────────────── конверсия (главный страховочный блок) ────────────────────

def test_round_trip_empty_delta_preserves_service_fields() -> None:
    items = [_model(), _option()]

    result = apply_editor_delta(items, _empty_delta())

    assert result == items  # frozen dataclass: полное равенство, служебные поля целы


def test_edit_price_keeps_other_fields() -> None:
    items = [_model(), _option()]
    delta = {"edited_rows": {1: {"Розница": 333000}}, "added_rows": [], "deleted_rows": []}

    result = apply_editor_delta(items, delta)

    assert result[1].price_retail == 333000
    # Служебные поля опции сохранены
    assert result[1].price_class == "C_manual_range"
    assert result[1].range_min == 200000
    assert result[1].range_max == 400000
    assert result[1].applies_to_lengths == [18]
    assert result[1].raw_payload == {"source": "retail", "notes": ["спец"]}


def test_editing_key_of_existing_row_is_ignored() -> None:
    """Смена ключа распознанной строки игнорируется → нет тихой потери служебных полей."""
    items = [_option()]
    delta = {"edited_rows": {0: {"Ключ": "hacked"}}, "added_rows": [], "deleted_rows": []}

    result = apply_editor_delta(items, delta)

    assert len(result) == 1
    assert result[0].key == "frame_18"  # исходный ключ
    assert result[0] == _option()  # обеднённая позиция НЕ создана


def test_added_row_builds_new_item() -> None:
    items = [_model()]
    delta = {
        "edited_rows": {},
        "added_rows": [
            {"Наименование": "Новая опция", "Тип": "Опция", "Розница": 50000, "Ключ": "new_opt"}
        ],
        "deleted_rows": [],
    }

    result = apply_editor_delta(items, delta)

    assert len(result) == 2
    new = result[1]
    assert new.key == "new_opt"
    assert new.item_type == "option"
    assert new.price_retail == 50000
    assert new.price_class == "UNKNOWN"
    assert new.raw_payload == {}


def test_deleted_row_removed() -> None:
    items = [_model(), _option()]
    delta = {"edited_rows": {}, "added_rows": [], "deleted_rows": [0]}

    result = apply_editor_delta(items, delta)

    assert [item.key for item in result] == ["frame_18"]


def test_items_to_dataframe_columns_and_key_last() -> None:
    df = items_to_dataframe([_model(), _option()])

    assert list(df.columns) == [
        "Наименование", "Тип", "Розница", "Дилер", "Признак", "Источник", "Ключ"
    ]
    assert df.iloc[0]["Ключ"] == "vesta-фл-60-18"
    assert df.iloc[1]["Источник"] == "retail"


# ──────────────────── smoke и поток через AppTest ────────────────────

def _admin_app() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    return at.switch_page("app_pages/3_Админка.py").run()


def test_update_view_renders_without_exception() -> None:
    at = _admin_app()

    assert not at.exception, f"Admin page raised: {at.exception}"
    headers = [str(h.value) for h in at.header]
    assert "Обновление прайса" in headers


def test_review_summary_has_no_false_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    """P2: сводка строится на итоге three-way merge → позиции вне снимка НЕ «удалены»."""
    monkeypatch.setattr(
        price_update_view.price_write_service, "write_prices", lambda *a, **k: None
    )

    at = AppTest.from_file(APP_PATH, default_timeout=30)
    # Снимок из одной позиции: текущий прайс содержит десятки других, которые three-way
    # merge перенесёт. Ложного «Удалено» быть не должно.
    at.session_state["price_update_stage"] = "table"
    at.session_state["price_update_working_items"] = [_option()]
    at.run()
    at.switch_page("app_pages/3_Админка.py").run()
    at.button(key="price_update_check").click().run()

    assert not at.exception, f"Review raised: {at.exception}"
    error_text = "\n".join(str(e.value) for e in at.error)
    assert "Удалено позиций" not in error_text


def test_flow_to_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    """Поток table → проверить → применить, без записи боевого prices.json."""
    calls: list[list[PriceItem]] = []

    def _fake_write(items: list[PriceItem], **_kwargs):
        calls.append(items)
        return price_write_service.WriteResult(
            prices_path=Path("prices.json"), backup_path=Path("prices.backup.json")
        )

    monkeypatch.setattr(price_update_view.price_write_service, "write_prices", _fake_write)

    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.session_state["price_update_stage"] = "table"
    at.session_state["price_update_working_items"] = [_model(), _option()]
    at.run()
    at.switch_page("app_pages/3_Админка.py").run()

    at.button(key="price_update_check").click().run()
    at.button(key="price_update_apply").click().run()

    assert not at.exception, f"Flow raised: {at.exception}"
    assert len(calls) == 1
    success = [str(s.value) for s in at.success]
    assert any("Прайс обновлён" in text for text in success)


def test_edit_current_enters_table_from_prices_json() -> None:
    """Smoke: «Редактировать текущий» → stage='table', working_items из normalize_prices(load_prices())."""
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.session_state["price_update_stage"] = "source"
    at.run()
    at.switch_page("app_pages/3_Админка.py").run()

    at.button(key="price_update_pick_current").click().run()

    assert not at.exception, f"Edit current raised: {at.exception}"
    assert "price_update_working_items" in at.session_state, "working_items должны быть заполнены"
    working_items = at.session_state["price_update_working_items"]
    assert len(working_items) >= 50, (
        f"Ожидалось 50+ позиций из prices.json, получено {len(working_items)}"
    )
    keys = {item.key for item in working_items}
    assert any("vesta-" in k for k in keys), "В таблице должны быть модели ВЕСТА"

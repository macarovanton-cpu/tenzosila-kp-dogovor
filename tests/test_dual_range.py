"""Тесты двухдиапазонной конфигурации весов (Фаза 1.5a).

Источник истины — Таблица 6 описания типа (приказ № 544 от 20.03.2025),
файл 03_knowledge_base/opisanie_tipa_VESTA_fixed.md.
"""
from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.data_loader import get_dual_range, load_models

APP_PATH = str(Path(__file__).resolve().parent.parent / "src" / "app.py")


def test_models_json_has_dual_range_for_scope():
    """Все 73 модели в scope MVP имеют непустой dual_range
    с обязательными подполями w1/w2 и ключами max/min/e/n."""
    models = load_models()["models"]
    assert len(models) == 73, f"Ожидалось 73 модели, найдено {len(models)}"
    for m in models:
        assert "dual_range" in m, f"{m['id']}: нет ключа dual_range"
        assert m["dual_range"] is not None, f"{m['id']}: dual_range = null"
        for key in ("w1", "w2"):
            assert key in m["dual_range"], f"{m['id']}: нет блока {key}"
            w = m["dual_range"][key]
            for f in ("max_load_t", "min_load_t", "e_kg", "n"):
                assert f in w, f"{m['id']}.{key}: нет поля {f}"


def test_dual_range_consistency_with_table_6():
    """Спот-чек 3 моделей из разных линеек/нагрузок vs Таблица 6 ОТ."""
    by_id = {m["id"]: m for m in load_models()["models"]}

    # С-80-18: W1=60/0.4/20/3000, W2=80/1/50/1600
    s80 = by_id["vesta-с-80-18"]["dual_range"]
    assert s80["w1"] == {"max_load_t": 60, "min_load_t": 0.4, "e_kg": 20, "n": 3000}
    assert s80["w2"] == {"max_load_t": 80, "min_load_t": 1, "e_kg": 50, "n": 1600}

    # ФЛ-40-22: W1=30/0.2/10/3000, W2=40/0.4/20/2000
    fl40 = by_id["vesta-фл-40-22"]["dual_range"]
    assert fl40["w1"] == {"max_load_t": 30, "min_load_t": 0.2, "e_kg": 10, "n": 3000}
    assert fl40["w2"] == {"max_load_t": 40, "min_load_t": 0.4, "e_kg": 20, "n": 2000}

    # С-120-24: W1=60/0.4/20/3000, W2=120/1/50/2400
    s120 = by_id["vesta-с-120-24"]["dual_range"]
    assert s120["w1"] == {"max_load_t": 60, "min_load_t": 0.4, "e_kg": 20, "n": 3000}
    assert s120["w2"] == {"max_load_t": 120, "min_load_t": 1, "e_kg": 50, "n": 2400}

    # П-100-18: W1=60/0.4/20/3000, W2=100/1/50/2000
    p100 = by_id["vesta-п-100-18"]["dual_range"]
    assert p100["w1"] == {"max_load_t": 60, "min_load_t": 0.4, "e_kg": 20, "n": 3000}
    assert p100["w2"] == {"max_load_t": 100, "min_load_t": 1, "e_kg": 50, "n": 2000}

    # СЛ-60-20: W1=30/0.2/10/3000, W2=60/0.4/20/3000
    sl60 = by_id["vesta-сл-60-20"]["dual_range"]
    assert sl60["w2"] == {"max_load_t": 60, "min_load_t": 0.4, "e_kg": 20, "n": 3000}


def test_get_dual_range_helper_returns_block_or_none():
    """Хелпер возвращает блок dual_range или None для отсутствующих id."""
    models = load_models()
    block = get_dual_range(models, "vesta-с-80-18")
    assert block is not None
    assert "w1" in block and "w2" in block
    assert get_dual_range(models, "несуществующий-id") is None


def test_is_dual_range_default_false():
    """initial_state выставляет is_dual_range = False."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    assert at.session_state["is_dual_range"] is False


def test_is_dual_range_resets_on_cascade_change():
    """Смена модели через каскад гасит чекбокс is_dual_range."""
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    at.session_state["is_dual_range"] = True
    # Меняем max через селектор (как в test_cascade_change_resets_overrides)
    try:
        at.selectbox(key="model_max").select(80).run()
    except Exception:
        from src.state import on_cascade_change
        at.session_state["model_max"] = 80
        on_cascade_change()
    assert at.session_state["is_dual_range"] is False

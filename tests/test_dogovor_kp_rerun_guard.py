"""A12: guard загрузки КП на странице Договор — стоп rerun-циклу редактора оплаты.

Дефект: блок загрузки КП перезасевал contract["payment_lines"] дефолтами на
КАЖДОМ rerun, пока КП выбран в дропдауне. Редактор оплаты накладывал дельту
пользователя, его сторож сходимости видел «дефолты != дефолты+дельта» →
st.rerun() навсегда (вечный спиннер при любой правке ячейки).

UI-цикл напрямую AppTest не берёт (правки st.data_editor не симулируются),
поэтому ловушка — на инвариант уровня state: при неизменном выбранном КП
повторный проход блока загрузки НЕ перезаписывает payment_lines; смена КП,
клик «Найти» и пересохранение (updated_at) — перезасевают.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.test_kp_restore import _kp_row, _smoke_state

APP_PATH = str(Path(__file__).resolve().parent.parent / "src" / "app.py")

_KP1 = "262626"
_KP2 = "КП-2026-888"


def _state(kp_number: str) -> dict:
    state = _smoke_state()
    state["kp_number"] = kp_number
    return state


def _summary(kp_number: str, updated_at: str) -> dict:
    """Строка как из list_recent_kps (без data)."""
    state = _state(kp_number)
    return {
        "kp_number": kp_number,
        "client_name": state["client_name"],
        "model_id": state["model_id"],
        "total_price": 1_000_000,
        "updated_at": updated_at,
    }


def _label(summary: dict) -> str:
    """Подпись дропдауна — ровно как строит страница."""
    price_str = f"{summary['total_price']:,}".replace(",", " ")
    return (
        f"{summary['kp_number']} — {summary['client_name']} — "
        f"{summary['model_id']} — {price_str} ₽"
    )


@pytest.fixture()
def at(monkeypatch) -> AppTest:
    """Договор-страница с замоканной сетью и двумя КП в дропдауне."""
    import streamlit as st

    import src.storage.supabase_client as sb
    import src.ui.load_kp_section as load_sec

    st.cache_data.clear()  # кэш _load_kp_full глобален на процесс

    summaries = [_summary(_KP1, "t1"), _summary(_KP2, "t1")]
    rows = {n: {**_kp_row(_state(n)), "updated_at": "t1"} for n in (_KP1, _KP2)}
    monkeypatch.setattr(sb, "list_recent_kps", lambda *a, **k: list(summaries))
    monkeypatch.setattr(sb, "get_kp_by_number", lambda num: rows.get(num))
    # Главная страница КП рисуется первой — глушим её сеть.
    monkeypatch.setattr(load_sec, "list_recent_kps", lambda *a, **k: [])
    monkeypatch.setattr(load_sec, "search_kps_by_contractor", lambda *a, **k: [])

    at = AppTest.from_file(APP_PATH, default_timeout=60).run()
    at.switch_page("app_pages/2_Договор.py").run()
    assert not at.exception, at.exception
    # Даём тестам мутировать моки (сценарий пересохранения КП).
    at._summaries = summaries
    at._rows = rows
    return at


def _select(at: AppTest, label: str) -> None:
    at.selectbox(key="kp_select").set_value(label).run()
    assert not at.exception, at.exception


def _lines(at: AppTest) -> list[dict]:
    return at.session_state["contract"]["payment_lines"]


def test_repeat_pass_does_not_reseed_payment_lines(at: AppTest):
    """ЯДРО A12: неизменный выбранный КП → повторный проход не трёт дельту."""
    _select(at, _label(_summary(_KP1, "t1")))
    defaults = _lines(at)
    assert defaults, "дефолтные строки оплаты не засеялись при загрузке КП"

    # Дельта редактора (эквивалент set_payment_lines после правки ячейки).
    edited = [dict(r) for r in defaults]
    edited[0]["Дней"] = 3
    at.session_state["contract"]["payment_lines"] = edited
    at.run()
    assert not at.exception, at.exception

    assert _lines(at)[0]["Дней"] == 3, (
        "блок загрузки КП перезасеял payment_lines на rerun при неизменном КП "
        "— второй писатель жив, rerun-цикл редактора оплаты вернётся"
    )


def test_switching_kp_reseeds(at: AppTest):
    """Guard не залипает: другой КП в дропдауне → полный перезасев."""
    _select(at, _label(_summary(_KP1, "t1")))
    edited = [dict(r) for r in _lines(at)]
    edited[0]["Дней"] = 3
    at.session_state["contract"]["payment_lines"] = edited

    _select(at, _label(_summary(_KP2, "t1")))
    assert at.session_state["contract"]["current_kp_number"] == _KP2
    assert _lines(at) and _lines(at)[0]["Дней"] != 3  # дефолты КП2, не дельта


def test_deselect_keeps_edits_and_reselect_same_kp_does_not_reseed(at: AppTest):
    """«— выбрать —» не трогает строки; возврат на тот же КП — без перезасева."""
    _select(at, _label(_summary(_KP1, "t1")))
    edited = [dict(r) for r in _lines(at)]
    edited[0]["Дней"] = 3
    at.session_state["contract"]["payment_lines"] = edited

    _select(at, "— выбрать —")
    assert _lines(at)[0]["Дней"] == 3  # правки не потеряны

    _select(at, _label(_summary(_KP1, "t1")))
    assert _lines(at)[0]["Дней"] == 3  # тот же КП → guard не перезасевает


def test_resaved_kp_reseeds(at: AppTest):
    """Пересохранённый КП (новый updated_at) обязан перезагрузиться."""
    _select(at, _label(_summary(_KP1, "t1")))
    edited = [dict(r) for r in _lines(at)]
    edited[0]["Дней"] = 3
    at.session_state["contract"]["payment_lines"] = edited

    # КП пересохранён под тем же номером: updated_at сменился и в сводке, и в строке.
    at._summaries[0] = _summary(_KP1, "t2")
    at._rows[_KP1]["updated_at"] = "t2"
    at.run()
    assert not at.exception, at.exception
    assert _lines(at)[0]["Дней"] != 3  # свежий снапшот перезасеял дефолты

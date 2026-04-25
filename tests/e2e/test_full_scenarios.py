"""4 e2e-сценария: Гипсобетон, Кирова (с/без поверки), Stress-max.

Каждый: применить конфиг через UI → скачать DOCX → content-asserts на
header/ТХ/спеку/оплату.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.helpers.apply import apply_scenario, generate_and_save
from tests.e2e.helpers.docx_assertions import (
    assert_full_text_contains,
    assert_header,
    assert_payment,
    assert_spec,
    assert_tx,
)
from tests.e2e.scenarios.gipsobeton import GIPSOBETON
from tests.e2e.scenarios.kirova import (
    KIROVA_WITH_VERIFICATION,
    KIROVA_WITHOUT_VERIFICATION,
)
from tests.e2e.scenarios.stress_max import STRESS_MAX

OUTPUT = Path(__file__).resolve().parent.parent / "output" / "scenarios"


def test_e2e_gipsobeton(kp_page):
    s = GIPSOBETON
    apply_scenario(kp_page, s)
    docx = generate_and_save(kp_page, s, OUTPUT)

    assert_header(
        docx,
        client_name=s.client_name,
        kp_number=s.kp_number,
        kp_date="25.04.2026",  # фиксируется TENZOSILA_FAKE_DATE
    )
    assert_tx(
        docx,
        max_load_t=s.model_max,
        platform_length_m=s.model_length,
        main_scale_contains=["20 кг", "50 кг"],  # dual_range
    )
    assert_spec(
        docx,
        require_model_full_name=s.model_full_name,
        expected_item_names=[
            s.model_full_name,
            "Фундамент под ВЕСТА-С/Ф/П, 18м",
            "ПАК ОРИОН Стандарт+",
            "Монтаж и пусконаладка",
            "Доставка весов до объекта",
            "Первичная поверка",
        ],
    )
    assert_payment(
        docx,
        contains=["Предоплата", "Доплата", "фундамент"],
        min_dash_lines=4,
    )


def test_e2e_kirova_with_verification(kp_page):
    s = KIROVA_WITH_VERIFICATION
    apply_scenario(kp_page, s)
    docx = generate_and_save(kp_page, s, OUTPUT)

    assert_header(docx, client_name=s.client_name, kp_number=s.kp_number)
    assert_tx(
        docx,
        max_load_t=s.model_max,
        platform_length_m=s.model_length,
        main_scale_contains=["кг"],
    )
    assert_spec(
        docx,
        require_model_full_name=s.model_full_name,
        expected_item_names=[
            s.model_full_name,
            "Монтаж и пусконаладка",
            "Доставка весов до объекта",
            "Первичная поверка",
        ],
    )
    assert_payment(
        docx,
        contains=["Предоплата", "Доплата"],
        min_dash_lines=2,
    )
    assert_full_text_contains(docx, "Первичная поверка")


def test_e2e_kirova_without_verification(kp_page):
    s = KIROVA_WITHOUT_VERIFICATION
    apply_scenario(kp_page, s)
    docx = generate_and_save(kp_page, s, OUTPUT)

    assert_header(docx, client_name=s.client_name, kp_number=s.kp_number)
    assert_spec(
        docx,
        require_model_full_name=s.model_full_name,
        expected_item_names=[
            s.model_full_name,
            "Монтаж и пусконаладка",
            "Доставка весов до объекта",
        ],
    )
    # Поверка ДОЛЖНА отсутствовать в спеке.
    from tests.e2e.helpers.docx_assertions import assert_full_text_contains
    from docx import Document
    doc = Document(str(docx))
    spec = doc.tables[3]
    spec_text = "\n".join(c.text for r in spec.rows for c in r.cells)
    assert "Первичная поверка" not in spec_text, (
        "Поверка не должна попасть в спеку: " + spec_text
    )


def test_e2e_stress_max(kp_page):
    s = STRESS_MAX
    apply_scenario(kp_page, s)
    docx = generate_and_save(kp_page, s, OUTPUT)

    assert_header(docx, client_name=s.client_name, kp_number=s.kp_number)
    assert_tx(
        docx,
        max_load_t=s.model_max,
        platform_length_m=s.model_length,
        main_scale_contains=["кг"],
    )
    # Порядок диктуется src/config.py:OPTION_BLOCKS_ORDER
    # (frames → fences → foundations → pak_orion → install → delivery → verification).
    # Опция canopy_turnkey_24 помечена on_request:true и в UI задизейблена,
    # поэтому в спеке отсутствует — см. сценарий stress_max.py.
    assert_spec(
        docx,
        require_model_full_name=s.model_full_name,
        expected_item_names=[
            s.model_full_name,
            "Рама под весы",
            "Ограждение НОРМА",
            "Фундамент под ВЕСТА-С/Ф/П, 24м",
            "ПАК ОРИОН Автоматика+",
            "Монтаж и пусконаладка",
            "Доставка весов до объекта",
            "Первичная поверка",
        ],
    )
    # custom-оплата — параграф содержит наш ввод
    assert_payment(
        docx,
        contains=["30%", "40%"],
        min_dash_lines=3,
    )

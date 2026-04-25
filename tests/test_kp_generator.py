"""Тесты kp_generator: контекст, имя файла, генерация DOCX."""
from __future__ import annotations

from datetime import date
from io import BytesIO

from docx import Document

from src.generators.kp_generator import (
    build_division_info,
    build_filename,
    build_main_scale_label,
    build_template_context,
    generate_kp,
)


def _state(**overrides) -> dict:
    base = {
        "kp_number": "47141",
        "kp_date": date(2026, 4, 22),
        "kp_valid_days": 15,
        "total_term_days": 35,
        "manager_id": "makarov_av",
        "client_name": "АО «Гипсобетон»",
        "model_line": "С",
        "model_max": 80,
        "model_length": 18,
        "model_id": "vesta-с-80-18",
        "model_price": 2_450_000,
        "warranty_months": 36,
        "is_dual_range": False,
        "construction_beam": "Двутавр 30Б1",
        "construction_beam_count": 8,
        "construction_center_beam": "Швеллер №12",
        "construction_center_beam_count": 2,
        "construction_deck_mm": 10,
        "construction_underlining_mm": 4,
        "options": {},
        "spec_items_overrides": {},
        "payment_preset_id": "prepay_50_postpay_50",
        "payment_split_state": {},
        "payment_percents": {"p1": 50, "p2": 50},
        "payment_days": 5,
        "payment_custom_text": "",
    }
    base.update(overrides)
    return base


# --- build_division_info ---


def test_build_division_info_single_range():
    model = {
        "full_name": "ВЕСТА-С-60-18",
        "length_m": 18, "width_m": 3,
        "max_load_t": 60, "verification_division_kg": 20, "n_intervals": 3000,
    }
    text = build_division_info(model, is_dual_range=False)
    assert "ВЕСТА-С-60-18" in text
    assert "Max=60т" in text
    assert "e=20 кг" in text
    assert "n=3000" in text


def test_build_division_info_dual_range():
    model = {
        "full_name": "ВЕСТА-С-80-18",
        "length_m": 18, "width_m": 3,
        "max_load_t": 80, "verification_division_kg": 50, "n_intervals": 1600,
        "dual_range": {
            "w1": {"max_load_t": 60, "min_load_t": 0.4, "e_kg": 20, "n": 3000},
            "w2": {"max_load_t": 80, "min_load_t": 0.4, "e_kg": 50, "n": 1600},
        },
    }
    text = build_division_info(model, is_dual_range=True)
    assert "Max₁=60т" in text
    assert "Max₂=80т" in text
    assert "e₁=20" in text
    assert "e₂=50" in text


# --- build_main_scale_label ---


def test_build_main_scale_label_single_range():
    model = {"verification_division_kg": 20}
    assert build_main_scale_label(model, is_dual_range=False) == "20"


def test_build_main_scale_label_dual_range():
    model = {
        "verification_division_kg": 50,
        "dual_range": {
            "w1": {"max_load_t": 60, "e_kg": 20},
            "w2": {"max_load_t": 80, "e_kg": 50},
        },
    }
    label = build_main_scale_label(model, is_dual_range=True)
    assert "20 до 60т" in label
    assert "50 от 60т до 80т" in label


# --- build_template_context ---


def test_build_template_context_keys(prices):
    state = _state()
    ctx = build_template_context(state, prices)
    expected_keys = {
        "client_name", "kp_number", "kp_date", "kp_valid_days",
        "warranty_text", "division_info", "max_load_t", "platform_size",
        "main_scale_label", "construction_description",
        "spec_items", "total_price", "total_term_days", "vat_percent",
        "payment_terms_block",
        "manager_full_name", "manager_phone", "manager_email",
    }
    assert expected_keys <= set(ctx.keys()), (
        f"Missing keys: {expected_keys - set(ctx.keys())}"
    )


def test_build_template_context_values(prices):
    state = _state()
    ctx = build_template_context(state, prices)
    assert ctx["client_name"] == "АО «Гипсобетон»"
    assert ctx["kp_number"] == "47141"
    assert ctx["kp_date"] == "22.04.2026"
    assert ctx["kp_valid_days"] == "15 дней"
    assert ctx["warranty_text"] == "36 месяцев"
    assert ctx["vat_percent"] == "22"
    assert ctx["manager_full_name"] == "Макаров Антон"
    assert isinstance(ctx["spec_items"], list)
    assert all("name" in i and "price" in i and "term_days" in i for i in ctx["spec_items"])


def test_pluralize_kp_valid_days_and_warranty(prices):
    state = _state(kp_valid_days=21, warranty_months=24)
    ctx = build_template_context(state, prices)
    assert ctx["kp_valid_days"] == "21 день"
    assert ctx["warranty_text"] == "24 месяца"


# --- build_filename ---


def test_build_filename_translit_russian():
    state = _state(client_name="ООО «Гипсобетон»")
    name = build_filename(state)
    assert name.startswith("КП_")
    assert name.endswith("_2026-04-22.docx")
    # Транслитерация: «Гипсобетон» → Gipsobeton
    assert "Gipsobeton" in name or "gipsobeton" in name.lower()


def test_build_filename_empty_client_uses_fallback():
    state = _state(client_name="")
    name = build_filename(state)
    assert name.startswith("КП_")


def test_build_filename_includes_model():
    state = _state()
    name = build_filename(state)
    assert "80-18" in name  # часть model_full_name


# --- generate_kp ---


def test_generate_kp_returns_zip_bytes(prices):
    """Сгенерированные байты — валидный zip (DOCX)."""
    state = _state()
    docx = generate_kp(state, prices)
    assert isinstance(docx, bytes)
    assert len(docx) > 1000
    assert docx.startswith(b"PK")  # zip signature


def test_generate_kp_no_remaining_jinja(prices):
    """В готовом DOCX нет неподставленных {{ или {% (включая колонтитул)."""
    state = _state()
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))

    parts: list[str] = []
    for p in doc.paragraphs:
        parts.append("".join(r.text or "" for r in p.runs))
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    parts.append("".join(r.text or "" for r in p.runs))
    for s in doc.sections:
        f = s.footer
        if f is None:
            continue
        for p in f.paragraphs:
            parts.append("".join(r.text or "" for r in p.runs))
        for t in f.tables:
            for row in t.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        parts.append("".join(r.text or "" for r in p.runs))

    text = " ".join(parts)
    assert "{{" not in text, "Остались плейсхолдеры {{...}}"
    assert "{%" not in text, "Остались jinja-теги {%...%}"


def test_generate_kp_dual_range_division_info_present(prices):
    """Для dual_range — division_info содержит Max₁/Max₂."""
    state = _state(model_id="vesta-с-80-18", is_dual_range=True)
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))
    text = " ".join(
        "".join(r.text or "" for r in p.runs)
        for p in doc.paragraphs
    )
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    text += " " + "".join(r.text or "" for r in p.runs)
    assert "Max₁" in text or "Max1" in text


def test_generate_kp_payment_block_contains_split_lines(prices):
    """split_by_items: убедимся, что строки про «по уведомлению» и
    «по факту готовности фундамента» есть в тексте."""
    state = _state(
        payment_preset_id="split_by_items",
        options={
            "foundation_s_f_18": {
                "enabled": True, "price": 1_900_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 1_900_000, "dealer_is_synthetic": False,
                "block": "foundations",
            },
        },
    )
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))
    text = " ".join(
        "".join(r.text or "" for r in p.runs) for p in doc.paragraphs
    )
    assert "по уведомлению" in text
    assert "фундамент" in text

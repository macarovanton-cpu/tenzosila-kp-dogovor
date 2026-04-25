"""Генерация DOCX КП через docxtpl."""
from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate, Listing
from slugify import slugify

from src.config import VAT_RATE
from src.data_loader import (
    get_manager_by_id,
    get_model_by_id,
    load_managers,
    load_models,
    load_payment_terms,
)
from src.generators.payment_renderer import render_payment_block
from src.spec_builder import (
    build_construction_description,
    build_spec_items,
    resolve_term_days,
)
from src.utils.format import fmt_int_spaces, pluralize

TEMPLATE_PATH: Path = Path(__file__).resolve().parent.parent.parent / "templates" / "kp_template.docx"


def build_division_info(model: dict, is_dual_range: bool) -> str:
    """Описание весов для шапки ТХ."""
    if not model:
        return "—"
    base = (
        f"Весы автомобильные {model.get('full_name', '—')}, "
        f"размер платформы {model.get('length_m', '?')}×{model.get('width_m', 3)}м, "
        f"класс точности III"
    )
    if is_dual_range and model.get("dual_range"):
        w1 = model["dual_range"]["w1"]
        w2 = model["dual_range"]["w2"]
        return (
            f"{base}, Max₁={w1['max_load_t']}т, Max₂={w2['max_load_t']}т, "
            f"e₁={w1['e_kg']} кг, e₂={w2['e_kg']} кг, "
            f"n₁={w1['n']}, n₂={w2['n']}"
        )
    return (
        f"{base}, Max={model.get('max_load_t', '?')}т, "
        f"e={model.get('verification_division_kg', '?')} кг, "
        f"n={model.get('n_intervals', '?')}"
    )


def build_main_scale_label(model: dict, is_dual_range: bool) -> str:
    """Метрология для строки «Цена поверочного деления»."""
    if not model:
        return "—"
    if is_dual_range and model.get("dual_range"):
        w1 = model["dual_range"]["w1"]
        w2 = model["dual_range"]["w2"]
        return (
            f"{w1['e_kg']} до {w1['max_load_t']}т / "
            f"{w2['e_kg']} от {w1['max_load_t']}т до {w2['max_load_t']}т"
        )
    return str(model.get("verification_division_kg", "—"))


def _payment_listing(payment_text: str) -> Listing:
    """Многострочный текст для подстановки: docxtpl.Listing преобразует
    '\\n' в `<w:br/>` (line break внутри параграфа).
    """
    return Listing(payment_text or "—")


def build_template_context(state: dict[str, Any], prices: dict) -> dict[str, Any]:
    """Чистая функция: state → dict для DocxTemplate.render()."""
    models_json = load_models()
    managers_json = load_managers()
    payment_terms_json = load_payment_terms()

    model = get_model_by_id(models_json, state.get("model_id", "")) or {}
    manager = get_manager_by_id(managers_json, state.get("manager_id", "")) or {}
    is_dual = bool(state.get("is_dual_range", False))

    spec_items = build_spec_items(state, prices, models_json)

    # Для шаблона передаём только те поля, что есть в spec-таблице (3 колонки)
    spec_items_fmt = [
        {
            "name": item["name"],
            "price": fmt_int_spaces(item["total"]),
            "term_days": str(item["term_days"]),
        }
        for item in spec_items
    ]

    total_price = sum(item["total"] for item in spec_items)
    total_term = resolve_term_days(spec_items, state)

    # Платформа
    platform_size = (
        f"{model.get('length_m', state.get('model_length', '?'))}×"
        f"{model.get('width_m', 3)}"
    )

    # Дата КП
    kp_date_val = state.get("kp_date") or date.today()
    if hasattr(kp_date_val, "strftime"):
        kp_date_str = kp_date_val.strftime("%d.%m.%Y")
    else:
        kp_date_str = str(kp_date_val)

    # Условия оплаты — Listing для переносов строк (\n → <w:br/>)
    payment_text = render_payment_block(state, spec_items, payment_terms_json)
    payment_rt = _payment_listing(payment_text)

    return {
        # Шапка
        "client_name": state.get("client_name", "—") or "—",
        "kp_number": state.get("kp_number", "—") or "—",
        "kp_date": kp_date_str,
        "kp_valid_days": pluralize(
            state.get("kp_valid_days", 15), ("день", "дня", "дней")
        ),
        # ТХ
        "warranty_text": pluralize(
            state.get("warranty_months", 36), ("месяц", "месяца", "месяцев")
        ),
        "division_info": build_division_info(model, is_dual),
        "max_load_t": str(model.get("max_load_t", state.get("model_max", "—"))),
        "platform_size": platform_size,
        "main_scale_label": build_main_scale_label(model, is_dual),
        "construction_description": build_construction_description(state),
        # Спецификация
        "spec_items": spec_items_fmt,
        # Итоги
        "total_price": fmt_int_spaces(total_price),
        "total_term_days": str(total_term),
        "vat_percent": str(int(VAT_RATE * 100)),
        # Оплата
        "payment_terms_block": payment_rt,
        # Колонтитул
        "manager_full_name": manager.get("full_name", "—") or "—",
        "manager_phone": manager.get("phone", "—") or "—",
        "manager_email": manager.get("email", "—") or "—",
    }


def generate_kp(state: dict[str, Any], prices: dict) -> bytes:
    """Сгенерировать DOCX КП из state. Возвращает bytes для st.download_button."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Шаблон не найден: {TEMPLATE_PATH}")

    doc = DocxTemplate(str(TEMPLATE_PATH))
    context = build_template_context(state, prices)
    doc.render(context)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def build_filename(state: dict[str, Any]) -> str:
    """КП_{client_translit}_{model_full_name}_{YYYY-MM-DD}.docx."""
    models_json = load_models()
    model = get_model_by_id(models_json, state.get("model_id", "")) or {}
    model_name = model.get("full_name", "ВЕСТА")

    client_translit = slugify(
        state.get("client_name", "") or "client",
        separator="_",
        lowercase=False,
    ) or "client"

    kp_date_val = state.get("kp_date") or date.today()
    if hasattr(kp_date_val, "strftime"):
        date_str = kp_date_val.strftime("%Y-%m-%d")
    else:
        date_str = str(kp_date_val)

    return f"КП_{client_translit}_{model_name}_{date_str}.docx"

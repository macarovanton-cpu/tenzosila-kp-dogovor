"""Генерация DOCX КП через docxtpl."""
from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate, Listing, RichText
from slugify import slugify

from src.config import VAT_RATE
from src.data_loader import (
    get_equipment_info,
    get_manager_by_id,
    get_model_by_id,
    load_managers,
    load_models,
    load_payment_terms,
)
from src.generators.payment_renderer import render_payment_block
from src.generators.spec_vmerge import apply_spec_vmerge, encode_term_days_marker
from src.spec_builder import (
    build_construction_description,
    build_spec_items,
)
from src.term_days import calculate_term_days_per_item, resolve_term_days
from src.utils.format import fmt_int_spaces, pluralize

TEMPLATE_PATH: Path = Path(__file__).resolve().parent.parent.parent / "templates" / "kp_template.docx"

# Размер шрифта вспомогательных строк имени модели в спецификации.
# В docxtpl.RichText.add(size=...) — half-points: 18 → 9pt.
_SPEC_NAME_SUBLINE_HALFPT = 18


def _spec_name_to_richtext(name: str) -> RichText:
    """Многострочное имя в спецификации → RichText.

    Первая строка — наследует размер ячейки (без явного size).
    Остальные строки — 9pt (size=18 в half-points).
    """
    lines = name.split("\n")
    rt = RichText()
    rt.add(lines[0])
    for line in lines[1:]:
        rt.add("\n", size=_SPEC_NAME_SUBLINE_HALFPT)
        rt.add(line, size=_SPEC_NAME_SUBLINE_HALFPT)
    return rt


def build_main_scale_label(model: dict, is_dual_range: bool) -> str:
    """Цена поверочного деления для ячейки ТХ.

    Однодиапазонная: '20 кг'
    Двухдиапазонная: '20 кг (до 60 т)\\n50 кг (от 60 до 80 т)'
    """
    if not model:
        return "—"
    if is_dual_range and model.get("dual_range"):
        w1 = model["dual_range"]["w1"]
        w2 = model["dual_range"]["w2"]
        return (
            f"{w1['e_kg']} кг (до {w1['max_load_t']} т)\n"
            f"{w2['e_kg']} кг (от {w1['max_load_t']} до {w2['max_load_t']} т)"
        )
    return f"{model.get('verification_division_kg', '—')} кг"


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
    total_term = resolve_term_days(spec_items, state)

    # Срок исполнения per-item — список той же длины, что spec_items.
    # Маркеры vMerge ("restart"/"continue") кодируем в текст ячейки;
    # apply_spec_vmerge() в generate_kp() заменит их на XML <w:vMerge>.
    per_item_terms = calculate_term_days_per_item(spec_items, total_term)

    # Для шаблона передаём только те поля, что есть в spec-таблице (3 колонки).
    # Многострочное имя (модель + датчики/терминал/ограждение) преобразуем в
    # RichText: первая строка обычным размером, остальные 9pt.
    spec_items_fmt = []
    for item, term_info in zip(spec_items, per_item_terms):
        name = item["name"]
        if isinstance(name, str) and "\n" in name:
            name_value = _spec_name_to_richtext(name)
        else:
            name_value = name
        spec_items_fmt.append({
            "name": name_value,
            "price": fmt_int_spaces(item["total"]),
            "term_days": encode_term_days_marker(
                term_info["value"] or "", term_info["merge"]
            ),
        })

    total_price = sum(item["total"] for item in spec_items)

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

    # main_scale_label — двухдиапазонная версия многострочная (\n → <w:br/>)
    main_scale = build_main_scale_label(model, is_dual)
    main_scale_value = Listing(main_scale) if "\n" in main_scale else main_scale

    # Датчик и терминал — лейбл и температурный диапазон
    sensor_info = get_equipment_info(
        models_json, "sensor", state.get("sensor_id", "")
    )
    indicator_info = get_equipment_info(
        models_json, "indicator", state.get("indicator_id", "")
    )

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
        "model_full_name": model.get("full_name", "ВЕСТА"),
        "max_load_t": str(model.get("max_load_t", state.get("model_max", "—"))),
        "platform_size": platform_size,
        "main_scale_label": main_scale_value,
        "construction_description": build_construction_description(state),
        "sensor_label": sensor_info["label"],
        "sensor_temp_range": sensor_info["temp_range"],
        "indicator_label": indicator_info["label"],
        "indicator_temp_range": indicator_info["temp_range"],
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

    # Постобработка: заменить маркеры ⟦MERGE:...⟧ в колонке сроков на
    # реальный текст + <w:vMerge> в tcPr. См. spec_vmerge.py.
    apply_spec_vmerge(doc.docx)

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

"""supply_filler.py — контекст договора поставки для docxtpl.

Основная точка входа: build_supply_context().
Переиспользует tth_context.build_tth_data, kit_renderer.build_kit_items,
payment_line.build_lines_from_snapshot/format_payment_line,
spec_v2_filler._load_model_and_deps — без дублирования логики.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from src.contracts.payment_line import (
    TRIGGER_TEXTS,
    PaymentTrigger,
    format_payment_line,
)
from src.contracts.requisites_transforms import (
    decline_fio,
    director_initials,
    position_genitive,
)
from src.contracts.supplier import SUPPLIER
from src.contracts.tth_context import build_tth_data
from src.contracts.utils import (
    MONTHS_RU,
    acts_participle,
    days_genitive,
    infer_director_gender,
    named_form,
    normalize_quotes,
    number_to_words,
)
from src.payment_wording import SUPPLY_TRIGGER_OVERRIDES
from src.term_days import TERM_DAYS_DEFAULTS, calculate_term_days_per_item, resolve_term_role


# ---------------------------------------------------------------------------
# Тексты триггеров под контекст договора поставки (W8): общий словарь
# + контекстные override'ы из payment_wording (без монтажа и Спецификации).
# ---------------------------------------------------------------------------

SUPPLY_TRIGGER_TEXTS: dict[PaymentTrigger, str] = {
    t: SUPPLY_TRIGGER_OVERRIDES.get(t.value, txt) for t, txt in TRIGGER_TEXTS.items()
}

# ---------------------------------------------------------------------------
# Статичные ТТХ из образца (supply-специфичные, не выводятся build_tth_data)
# ---------------------------------------------------------------------------

_TTH_SUPPLY_CONST: dict[str, str] = {
    "ТТХ_СВЯЗЬ":      "RS 232/485",
    "ТТХ_ПИТАНИЕ":    "220 ±15",
    "ТТХ_МОЩНОСТЬ":   "15",
    "ТТХ_ГОСТ_СТРОКА": (
        "Весы автомобильные ВЕСТА выпускаются ООО «Компания «Тензосила» "
        "по ГОСТ OIML R-76-1-2011, зарегистрированы в Госреестре СИ РФ под № 78871-20."
    ),
}


# ---------------------------------------------------------------------------
# _buyer_context: ЗАКАЗЧИК_* → ПОКУПАТЕЛЬ_* + ПОСТАВЩИК_*
# ---------------------------------------------------------------------------

_OSNOV_PREFIX_RE = re.compile(r"^на\s+основании\s+", re.IGNORECASE)


def _buyer_context(ctx: dict[str, str]) -> dict[str, str]:
    """Собрать ПОКУПАТЕЛЬ_* и ПОСТАВЩИК_* из плоского ctx (ЗАКАЗЧИК_*).

    Внутренние ЗАКАЗЧИК_* ключи НЕ переименовываются.
    ИП не имеет КПП: если ЗАКАЗЧИК_КПП отсутствует/пусто → пусто (не падать).
    Шаблон прячет строку КПП через {% if ПОКУПАТЕЛЬ_КПП %}.

    Преамбула в род. падеже (Путь A — авто-склонение). 6 ключей преамбулы/контактов
    ВСЕГДА присутствуют (пустая строка по умолчанию), иначе docxtpl {% if %} упадёт.
    Нет директора → ФИО_РП / ДОЛЖНОСТЬ_РП / ДЕЙСТВУЕТ / ОСНОВАНИЕ пустые, и клауза
    «в лице …» в шаблоне скрывается своим {% if %}.
    """
    g = ctx.get

    name = normalize_quotes(
        g("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ") or g("ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ", "")
    )
    fio = (g("ЗАКАЗЧИК_ДИРЕКТОР_ФИО", "") or "").strip()
    position = (g("ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ", "") or "").strip()
    gender = (g("ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ", "") or "").strip() or (
        infer_director_gender(fio) if fio else ""
    )

    # ФИО/должность в родительном падеже: берём готовое (ручная правка менеджера),
    # иначе склоняем; неизвестная должность → fallback на именительный (не падаем).
    fio_rp = (
        (g("ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП") or decline_fio(fio, gender or "male")[0])
        if fio else ""
    )
    position_rp = (
        (g("ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП") or position_genitive(position) or position)
        if position else ""
    )
    # Основание: парсер отдаёт без предлога; срезаем «на основании » для ручного ввода.
    osnovanie = _OSNOV_PREFIX_RE.sub("", (g("ЗАКАЗЧИК_ОСНОВАНИЕ", "") or "").strip())
    if fio and not osnovanie:
        osnovanie = "Устава"

    result: dict[str, str] = {
        # Покупатель — КРАТКОЕ наименование (симметрия с кратким поставщиком).
        "ПОКУПАТЕЛЬ_НАИМЕНОВАНИЕ":  name,
        "ПОКУПАТЕЛЬ_ИНН":            g("ЗАКАЗЧИК_ИНН", ""),
        "ПОКУПАТЕЛЬ_КПП":            g("ЗАКАЗЧИК_КПП", ""),
        "ПОКУПАТЕЛЬ_ОГРН":           g("ЗАКАЗЧИК_ОГРН", ""),
        "ПОКУПАТЕЛЬ_ЮР_АДРЕС":      g("ЗАКАЗЧИК_АДРЕС_ЮР", ""),
        "ПОКУПАТЕЛЬ_РС":             g("ЗАКАЗЧИК_РС", ""),
        "ПОКУПАТЕЛЬ_КС":             g("ЗАКАЗЧИК_КС", ""),
        "ПОКУПАТЕЛЬ_БИК":            g("ЗАКАЗЧИК_БИК", ""),
        "ПОКУПАТЕЛЬ_БАНК":           g("ЗАКАЗЧИК_БАНК", ""),
        "ПОКУПАТЕЛЬ_EMAIL":          g("ЗАКАЗЧИК_EMAIL", ""),
        "ПОКУПАТЕЛЬ_ТЕЛЕФОН":        g("ЗАКАЗЧИК_ТЕЛЕФОН", ""),
        # Подписант — формат «инициалы + фамилия» (симметрия с О.А. Сенаторов).
        "ПОКУПАТЕЛЬ_ДИРЕКТОР_ФИО":   (
            g("ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ") or director_initials(fio)
        ),
        "ПОКУПАТЕЛЬ_ДИРЕКТОР_ДОЛЖНОСТЬ": position,
        # Преамбула в родительном падеже + орг-форма.
        "ПОКУПАТЕЛЬ_ДИРЕКТОР_ФИО_РП":       fio_rp,
        "ПОКУПАТЕЛЬ_ДИРЕКТОР_ДОЛЖНОСТЬ_РП": position_rp,
        "ПОКУПАТЕЛЬ_ДЕЙСТВУЕТ":              acts_participle(gender) if fio else "",
        "ПОКУПАТЕЛЬ_ОСНОВАНИЕ":              osnovanie,
        "ПОКУПАТЕЛЬ_ИМЕНУЕМ":                named_form(name),
    }
    result.update(SUPPLIER)
    return result


# ---------------------------------------------------------------------------
# build_supply_tth: ТТХ для приложения №2
# ---------------------------------------------------------------------------

def build_supply_tth(model: dict, sensor: dict) -> dict[str, str]:
    """ТТХ для шаблона supply_appendix_2.docx.

    Перекладывает выход build_tth_data в supply-ключи и дополняет
    статичными константами (ТТХ_СВЯЗЬ, ТТХ_ПИТАНИЕ, ТТХ_МОЩНОСТЬ, ТТХ_ГОСТ_СТРОКА).
    """
    base = build_tth_data(model, sensor)

    d1 = base.get("ТТХ_ДИСКРЕТНОСТЬ_1", "")
    d2 = base.get("ТТХ_ДИСКРЕТНОСТЬ_2", "")
    дискретность = f"{d1} / {d2}" if d2 else d1

    result: dict[str, str] = {
        "ТТХ_MAX":                str(model.get("max_load_t", "")),
        "ТТХ_ОСЬ":               base.get("ТТХ_НАГРУЗКА_НА_ОСЬ", ""),
        "ТТХ_РАССТОЯНИЕ_ТЕРМИНАЛ": base.get("ТТХ_РАССТОЯНИЕ_ДО_ТЕРМИНАЛА", ""),
        "ТТХ_ДИСКРЕТНОСТЬ":       дискретность,
        "ТТХ_ГАБАРИТЫ":           base.get("ТТХ_ГАБАРИТЫ", ""),
        "ТТХ_ТЕМПЕРАТУРА":        base.get("ТТХ_ТЕМПЕРАТУРА", ""),
    }
    result.update(_TTH_SUPPLY_CONST)
    return result


# ---------------------------------------------------------------------------
# decide_contract_type
# ---------------------------------------------------------------------------

def decide_contract_type(
    install_scope: str,
    foundation_scope: str,
    has_orion: bool,
) -> str:
    """Определить тип документа по сигналам КП.

    Возвращает 'supply' или 'spec'.
    'supply' — чистая поставка: нет монтажа, нет фундамента Подрядчика, нет ОРИОН.
    Рама без монтажа — тоже поставка (FIX_SPEC БАГ-1b).
    """
    if (
        install_scope == "none"
        and foundation_scope in {"none", "existing_foundation", "rama"}
        and not has_orion
    ):
        return "supply"
    return "spec"


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _role_days_supply(spec_items: list[dict]) -> dict[str, int]:
    """role → days (первый item каждой роли из позиций спецификации)."""
    item_days, _ = calculate_term_days_per_item(spec_items)
    result: dict[str, int] = {}
    for item_key, days in item_days.items():
        if days is None:
            continue
        role = resolve_term_role(item_key)
        if role and role not in result:
            result[role] = days
    return result


def _fmt_days(d: int) -> str:
    """Форматировать количество рабочих дней: '20 (двадцати)'."""
    return f"{d} ({days_genitive(d)})"


def _fmt_date_ru(d: date) -> str:
    """Форматировать дату по-русски: '26 апреля 2026 года'."""
    return f"{d.day} {MONTHS_RU[d.month]} {d.year} года"


def _short_product_name(full_name: str) -> str:
    """Убрать 'Весы автомобильные ' из начала наименования.

    В appendix_2 шаблон уже содержит слово 'весов', поэтому ТОВАР_НАИМЕНОВАНИЕ
    должен начинаться с кода модели, а не дублировать 'Весы автомобильные'.
    """
    return re.sub(r"^Весы автомобильные\s+", "", full_name, flags=re.IGNORECASE)


def _fmt_money(x: int) -> str:
    """Сумма с разделителем тысяч пробелом: 2242000 → '2 242 000'."""
    return "{:,}".format(x).replace(",", " ")


def _supply_spec_rows(items: list[dict], product_name: str) -> tuple[int, list[dict]]:
    """Сумма поставки и строки спецификации (весы + доставка).

    Фильтр по payment_group: исключаются работы (installation_and_verification)
    и фундамент (foundation); остаются scales (+None/unknown) и delivery.
    Весы — одной агрегированной строкой, доставка — отдельной.
    Фильтр по payment_group, а не по id — обходит баг маппинга custom_N.
    """
    kept = [
        it for it in items
        if it.get("payment_group") not in {"installation_and_verification", "foundation"}
    ]
    delivery_total = sum(
        int(it.get("total") or 0) for it in kept
        if it.get("payment_group") == "delivery"
    )
    scales_total = sum(
        int(it.get("total") or 0) for it in kept
        if it.get("payment_group") != "delivery"
    )
    rows: list[dict] = []
    if scales_total:
        rows.append({"name": product_name, "sum": _fmt_money(scales_total)})
    if delivery_total:
        rows.append({"name": "Доставка", "sum": _fmt_money(delivery_total)})
    return scales_total + delivery_total, rows


# ---------------------------------------------------------------------------
# build_supply_context
# ---------------------------------------------------------------------------

def build_supply_context(
    ctx: dict[str, str],
    items: list[dict],
    deal: dict,
    payment_rows: list[dict],
    manual: dict[str, Any],
    contract_date: date,
    model_qty: int = 1,
) -> dict:
    """Полный контекст docxtpl для трёх шаблонов договора поставки.

    Служебные ключи (не для docxtpl):
      _payment_lines: list[str] — форматированные строки оплаты для
                      двупрохода с _replace_marker_with_paragraphs в compose_supply.
    """
    from src.contracts.spec_v2_filler import _load_model_and_deps

    result = _buyer_context(ctx)

    # --- Наименование товара (без 'Весы автомобильные' для корректной вставки) ---
    qty_scales = int(model_qty or 1)
    base_name = items[0]["name"] if items else ""
    short_name = _short_product_name(base_name)
    товар = (
        f"{short_name}, в количестве {qty_scales}шт." if short_name else ""
    )

    # --- Суммы и строки спецификации (фильтр по payment_group) ---
    # Строки спецификации — per-unit (за 1 весы). Цена договора (п.4.1) и
    # ИТОГО-за-N — от подытог_за_1 × model_qty.
    total_per_1, spec_rows = _supply_spec_rows(items, товар)
    total = total_per_1 * qty_scales
    сумма_цифрами = _fmt_money(total)
    сумма_прописью = number_to_words(total).capitalize() if total else ""

    # --- Сроки ---
    role_days = _role_days_supply(items)
    prod_days = role_days.get("scales", TERM_DAYS_DEFAULTS["scales"])
    deliv_days = role_days.get("delivery", TERM_DAYS_DEFAULTS["delivery"])

    # --- Срок действия договора ---
    valid_until_raw = manual.get("valid_until")
    if valid_until_raw and hasattr(valid_until_raw, "strftime"):
        срок_действия_до = valid_until_raw.strftime("%d.%m.%Y") + " г."
    else:
        срок_действия_до = str(valid_until_raw) if valid_until_raw else ""

    # --- ТТХ и комплект ---
    deps = _load_model_and_deps(deal)
    tth: dict[str, str] = dict.fromkeys(
        ["ТТХ_MAX", "ТТХ_ОСЬ", "ТТХ_РАССТОЯНИЕ_ТЕРМИНАЛ", "ТТХ_ДИСКРЕТНОСТЬ",
         "ТТХ_ГАБАРИТЫ", "ТТХ_ТЕМПЕРАТУРА", *_TTH_SUPPLY_CONST],
        "",
    )
    kit_rows: list[dict] = []
    if deps:
        model, line_defaults, sensor, indicator = deps
        tth = build_supply_tth(model, sensor)
        from src.contracts.kit_renderer import build_kit_items
        cable_m = line_defaults.get("default_cable_length_m", 20)
        kit_rows = build_kit_items(model, line_defaults, sensor, indicator, cable_m)

    # --- Оплата ---
    from src.ui.payment_lines_editor import _row_to_line
    payment_text_lines: list[str] = [
        format_payment_line(_row_to_line(row), f"4.2.{i + 1}", SUPPLY_TRIGGER_TEXTS)
        for i, row in enumerate(payment_rows)
    ]

    result.update({
        # Договорные поля
        "ДОГОВОР_НОМЕР":        manual.get("contract_number", ""),
        "ДОГОВОР_ДАТА":         _fmt_date_ru(contract_date),
        "ДОГОВОР_ГОРОД":        manual.get("contract_city", "г. Воронеж"),
        "ТОВАР_НАИМЕНОВАНИЕ":   товар,
        "СУММА_ЦИФРАМИ":        сумма_цифрами,
        "СУММА_ПРОПИСЬЮ":       сумма_прописью,
        "СРОК_ПРОИЗВОДСТВА_ДН": _fmt_days(prod_days),
        "СРОК_ДОСТАВКИ_ДН":    _fmt_days(deliv_days),
        "АДРЕС_ПОСТАВКИ":       manual.get("object_address", "").rstrip(" ."),
        "СРОК_ДЕЙСТВИЯ_ДО":     срок_действия_до,
        "ТЕКУЩИЙ_ГОД":          str(contract_date.year),
        # ТТХ
        **tth,
        # Спецификация прил.№1 (для docxtpl {%tr for row in spec_rows %}): весы + доставка
        "spec_rows": spec_rows,
        # Комплект (для docxtpl {%tr for item in kit_rows %} в appendix_2)
        "kit_rows": kit_rows,
        # Sentinel для двупрохода оплаты в compose_supply
        "PAYMENT_SECTION": "{{PAYMENT_SECTION}}",
        # Служебный ключ — строки оплаты для python-docx шага
        "_payment_lines": payment_text_lines,
        # Служебные ключи — вторая строка ИТОГО в appendix_1 (только при qty>1).
        # Строки спецификации per-unit → в ИТОГО «за 1 весы» = total_per_1.
        "_qty_scales": qty_scales,
        "_itogo_per_1": _fmt_money(total_per_1),
        "_itogo_n": сумма_цифрами,
    })

    return result

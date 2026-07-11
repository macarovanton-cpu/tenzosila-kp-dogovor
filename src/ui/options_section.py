"""13 блоков опций: пандусы, рама, ограждение, люки, фундамент и т.д."""
from __future__ import annotations

import re
from typing import Any

import streamlit as st

from src.config import (
    BLOCK_LABELS,
    OPTION_BLOCKS_ORDER,
    QTY_ENABLED_BLOCKS,
    VAT_RATE,
)
from src.contracts.custom_work_types import CUSTOM_WORK_TYPES, DEFAULT_WORK_TYPE
from src.filters import get_visible_options
from src.pricing import (
    SliderParams,
    color_code,
    get_slider_params,
    percent_to_retail,
)
from src.spec_builder import resolve_dynamic_option_label

FOUNDATION_EXECUTION_CHOICES: list[str] = [
    "пандусный",
    "приямок",
    "монолитная_плита",
]

_FOUNDATION_EXECUTION_DEFAULT = "пандусный"

# Эвристика ТОЛЬКО для UI-подсказки (не влияет на рендер/scope): имя похоже на монтаж,
# но менеджер оставил тип «Прочее» → клаузы монтажа не попадут в договор.
_LOOKS_LIKE_INSTALL_RE = re.compile(r"монтаж|пусконалад|ПНР|шеф.?монтаж", re.IGNORECASE)


def render_options_section(
    state: dict,
    prices: dict,
    models_json: dict,
    options_meta: dict,
) -> None:
    st.subheader(":material/add_circle: Опции и услуги")
    st.caption("Фундамент, монтаж, доставка, поверка и дополнительные услуги")
    line = state.get("model_line", "С")
    length = int(state.get("model_length", 18))
    prices_options = prices.get("options", {})
    enabled_map = state.get("options", {}) or {}

    for block_id in OPTION_BLOCKS_ORDER:
        visible = get_visible_options(prices_options, line, length, block_id)
        if not visible:
            # Не рендерим пустой expander — для чистоты UI
            continue
        enabled_count = sum(
            1 for key, _ in visible
            if enabled_map.get(key, {}).get("enabled")
        )
        label = BLOCK_LABELS[block_id]
        if enabled_count:
            label = f"{label} ({enabled_count} включено)"
        with st.expander(label, expanded=enabled_count > 0):
            for key, entry in visible:
                _render_option_row(
                    key, entry, block_id, state, options_meta
                )
    _render_custom_items(state)


def _render_option_row(
    key: str,
    entry: dict[str, Any],
    block_id: str,
    state: dict,
    options_meta: dict,
) -> None:
    params = get_slider_params(entry)
    model_id = state.get("model_id", "base")
    widget_suffix = f"__{model_id}"
    # Динамический лейбл: подменяем дженерик-обозначение линейки на букву
    # выбранной модели (С(Ф)/ФЛ(СЛ) → С, Ф/С → С и т.п.). Иначе менеджер
    # видит «Рама под весы ВЕСТА-С(Ф)/ФЛ(СЛ), 20м» вместо «…ВЕСТА-С, 20м».
    display_label = resolve_dynamic_option_label(
        key, entry.get("label", key), state.get("model_line", "С")
    )

    # Чекбокс включения
    checkbox_key = f"opt_{key}_enabled{widget_suffix}"
    if params.is_on_request:
        st.warning(
            f"**{display_label}** — под запрос у производства. "
            f"Свяжитесь для уточнения цены."
        )
        enabled = st.checkbox(
            display_label,
            value=False,
            disabled=True,
            key=checkbox_key,
        )
    else:
        enabled = st.checkbox(
            display_label,
            value=state.get("options", {}).get(key, {}).get("enabled", False),
            key=checkbox_key,
        )

    # Описание из options_meta
    _render_option_description(key, options_meta)

    if not enabled:
        # Сохранить «выключено», чтобы не держать старое значение после снятия галочки
        state.setdefault("options", {})[key] = {
            "enabled": False,
            "price": 0,
            "qty": 1,
            "customer_side": False,
            "is_on_request": params.is_on_request,
            "retail": params.retail,
            "dealer_is_synthetic": params.dealer_is_synthetic,
            "block": block_id,
        }
        if key == "bytovka_weigh_room":
            state["bytovka_dimensions"] = ""
            st.session_state.pop(f"opt_{key}_dimensions{widget_suffix}", None)
        if key == "install_default":
            state["is_shefmontazh"] = False
            st.session_state.pop(f"opt_{key}_shefmontazh{widget_suffix}", None)
        # При выключении опции сбросить её override в spec-таблице
        overrides = state.setdefault("spec_items_overrides", {})
        overrides.pop(key, None)
        return

    if _requires_foundation_execution_choice(key):
        _render_foundation_execution_choice(key, state, widget_suffix)

    dimensions = ""
    if key == "bytovka_weigh_room":
        dimensions = st.text_input(
            "Габариты",
            value=str(state.get("bytovka_dimensions", "")),
            placeholder="6×2.4м",
            key=f"opt_{key}_dimensions{widget_suffix}",
        ).strip()
        state["bytovka_dimensions"] = dimensions

    if key == "install_default":
        state["is_shefmontazh"] = bool(
            st.checkbox(
                "Шеф-монтаж",
                value=bool(state.get("is_shefmontazh", False)),
                key=f"opt_{key}_shefmontazh{widget_suffix}",
            )
        )

    # Поверка: особый случай — radio «Подрядчик / Заказчик»
    customer_side = False
    if key == "verification_default" and params.allow_customer_value:
        side = st.radio(
            "Силами",
            ["Подрядчик", "Заказчик"],
            horizontal=True,
            key=f"opt_{key}_side{widget_suffix}",
            help="При выборе «Заказчик» цена поверки в спецификации обнуляется",
        )
        customer_side = side == "Заказчик"

    price_value = params.default_v
    if customer_side:
        st.caption("Поверка силами Заказчика — цена 0 ₽.")
    else:
        price_value = _render_price_widget(key, params, widget_suffix)

    qty = 1
    if block_id in QTY_ENABLED_BLOCKS:
        qty = int(
            st.number_input(
                "Количество",
                min_value=1, max_value=20, step=1, value=1,
                key=f"opt_{key}_qty{widget_suffix}",
            )
        )

    state.setdefault("options", {})[key] = {
        "enabled": True,
        "price": int(price_value),
        "qty": qty,
        "customer_side": customer_side,
        "is_on_request": params.is_on_request,
        "retail": params.retail,
        "dealer_is_synthetic": params.dealer_is_synthetic,
        "block": block_id,
    }
    if key == "bytovka_weigh_room":
        state["options"][key]["dimensions"] = dimensions


def _render_custom_items(state: dict) -> None:
    """Динамический список произвольных товарных позиций КП."""
    state.setdefault("custom_items", [])
    state.setdefault("custom_item_next_id", 1)

    st.divider()
    st.caption("Произвольные позиции")
    if st.button("+ добавить позицию", key="custom_item_add"):
        next_id = int(state.get("custom_item_next_id", 1))
        state["custom_items"].append({
            "id": f"custom_{next_id}",
            "name": "",
            "price": 0,
            "scope": DEFAULT_WORK_TYPE,
        })
        state["custom_item_next_id"] = next_id + 1
        st.rerun()

    scope_keys = list(CUSTOM_WORK_TYPES.keys())
    scope_labels = [wt.label for wt in CUSTOM_WORK_TYPES.values()]
    for item in list(state.get("custom_items", [])):
        item_id = str(item.get("id") or "")
        if not item_id:
            continue
        cols = st.columns([4, 2, 2, 1])
        name = cols[0].text_input(
            "Название",
            value=str(item.get("name", "")),
            key=f"{item_id}_name",
        ).strip()
        current_scope = str(item.get("scope") or DEFAULT_WORK_TYPE)
        scope_index = scope_keys.index(current_scope) if current_scope in scope_keys else 0
        selected_label = cols[1].selectbox(
            "Тип работ",
            scope_labels,
            index=scope_index,
            key=f"{item_id}_scope",
            help="«Монтаж» добавит в договор обязательства сторон по монтажу",
        )
        scope = scope_keys[scope_labels.index(selected_label)]
        price = int(cols[2].number_input(
            "Цена, ₽",
            min_value=0,
            max_value=100_000_000,
            step=1_000,
            value=int(item.get("price", 0) or 0),
            key=f"{item_id}_price",
        ))
        if cols[3].button("×", key=f"{item_id}_delete", help="Удалить позицию"):
            state["custom_items"] = [
                existing for existing in state.get("custom_items", [])
                if existing.get("id") != item_id
            ]
            st.rerun()
        item["name"] = name
        item["price"] = price
        item["scope"] = scope

        # Подсказка: имя похоже на монтаж, но тип не выбран.
        if scope == DEFAULT_WORK_TYPE and _LOOKS_LIKE_INSTALL_RE.search(name):
            st.warning(
                "Похоже на монтаж — выберите тип «Монтаж», иначе обязательства "
                "сторон не попадут в договор."
            )
        # Подсказка: монтаж уже покрыт опцией (коллизия id в from_kp).
        if (
            scope == "installation"
            and state.get("options", {}).get("install_default", {}).get("enabled")
        ):
            st.info(
                "Монтаж уже покрыт опцией — ручная позиция пойдёт дополнительной строкой."
            )


def _requires_foundation_execution_choice(key: str) -> bool:
    """Нужен ли UI-выбор типа фундамента для варианта 1-3."""
    return (
        key.startswith(("foundation_lite_", "foundation_std_", "foundation_s_f_"))
        or key == "foundation_supervision"
        or key.startswith("construction_works_")
    )


def _render_foundation_execution_choice(
    key: str, state: dict, widget_suffix: str
) -> None:
    """Выбор типа фундамента для snapshot КП→Договор."""
    current = state.get("foundation_execution") or _FOUNDATION_EXECUTION_DEFAULT
    if current not in FOUNDATION_EXECUTION_CHOICES:
        current = _FOUNDATION_EXECUTION_DEFAULT

    selected = st.segmented_control(
        "Тип фундамента",
        FOUNDATION_EXECUTION_CHOICES,
        default=current,
        key=f"opt_{key}_foundation_execution{widget_suffix}",
        help="Попадает в snapshot КП для подбора строительного задания договора",
    )
    state["foundation_execution"] = selected or _FOUNDATION_EXECUTION_DEFAULT


def _clear_price_override(item_key: str) -> None:
    """Колбэк: движение слайдера цены молча чистит price-часть override."""
    overrides = st.session_state.setdefault("spec_items_overrides", {})
    ov = overrides.get(item_key, {}) or {}
    ov.pop("price", None)
    if ov:
        overrides[item_key] = ov
    else:
        overrides.pop(item_key, None)


def _render_price_widget(
    key: str, params: SliderParams, widget_suffix: str
) -> int:
    widget_key = f"opt_{key}_price{widget_suffix}"
    common = dict(
        min_value=params.min_v,
        max_value=params.max_v,
        value=params.default_v,
        step=params.step,
        key=widget_key,
        on_change=_clear_price_override,
        args=(key,),
        help="Диапазон дилерская ↔ розница +40 %. Значения округлены до тысяч",
    )
    value = st.number_input(f"Цена, ₽ (с НДС {VAT_RATE*100:.0f}%)", **common)

    _render_price_caption(int(value), params)
    return int(value)


def _render_price_caption(value: int, params: SliderParams) -> None:
    from src.utils.format import fmt_rub
    tag = color_code(value, params.retail, params.dealer)
    pct = percent_to_retail(value, params.retail)
    sign = "+" if pct >= 0 else ""
    dealer_part = ""
    if params.dealer is not None:
        dealer_label = "Дилер"
        if params.dealer_is_synthetic:
            dealer_label = "Дилер (оценка)"
        dealer_part = f"{dealer_label}: {fmt_rub(params.dealer)} · "
    st.caption(
        f"{tag} {dealer_part}"
        f"Розница: {fmt_rub(params.retail)} · "
        f"Выбрано: {fmt_rub(value)} ({sign}{pct:.1f}% к рознице)"
    )


def _render_option_description(key: str, options_meta: dict) -> None:
    """Показать описание из data/options.json (если есть)."""
    descr = _lookup_options_meta_description(key, options_meta)
    if descr:
        st.caption(descr)


def _lookup_options_meta_description(key: str, options_meta: dict) -> str:
    """Ищет поле description/notes в options.json по ключу опции из prices.json."""
    # ПАК ОРИОН — список
    for pkg in options_meta.get("pak_orion_packages", []) or []:
        if pkg.get("id") == key:
            parts = []
            if pkg.get("description"):
                parts.append(str(pkg["description"]))
            if pkg.get("components"):
                comp = ", ".join(str(c) for c in pkg["components"])
                parts.append(f"Состав: {comp}")
            return " · ".join(parts)
    # Фундаменты — словарь или список
    fnd = options_meta.get("foundation_options") or {}
    if isinstance(fnd, dict) and key in fnd:
        entry = fnd[key]
        if isinstance(entry, dict):
            return str(entry.get("description") or entry.get("notes") or "")
    elif isinstance(fnd, list):
        for entry in fnd:
            if entry.get("id") == key:
                return str(entry.get("description") or entry.get("notes") or "")
    return ""

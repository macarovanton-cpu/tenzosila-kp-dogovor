"""13 блоков опций: пандусы, рама, ограждение, люки, фундамент и т.д."""
from __future__ import annotations

from typing import Any

import streamlit as st

from src.config import (
    BLOCK_LABELS,
    OPTION_BLOCKS_ORDER,
    QTY_ENABLED_BLOCKS,
)
from src.filters import get_visible_options
from src.pricing import (
    SliderParams,
    color_code,
    get_slider_params,
    percent_to_retail,
)


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

    # Чекбокс включения
    checkbox_key = f"opt_{key}_enabled{widget_suffix}"
    if params.is_on_request:
        st.warning(
            f"**{entry.get('label', key)}** — под запрос у производства. "
            f"Свяжитесь для уточнения цены."
        )
        enabled = st.checkbox(
            entry.get("label", key),
            value=False,
            disabled=True,
            key=checkbox_key,
        )
    else:
        enabled = st.checkbox(
            entry.get("label", key),
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
        # При выключении опции сбросить её override в spec-таблице
        overrides = state.setdefault("spec_items_overrides", {})
        overrides.pop(key, None)
        return

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
    if params.kind == "number_input":
        value = st.number_input("Цена, ₽ (с НДС 22%)", **common)
    else:
        value = st.slider("Цена, ₽ (с НДС 22%)", **common)

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

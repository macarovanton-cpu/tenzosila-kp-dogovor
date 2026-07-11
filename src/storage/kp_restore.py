"""Реконструкция состояния конфигуратора КП из снапшота Supabase.

`reconstruct_kp_state` — чистая функция (без streamlit): снапшот-строка `kp_row`
→ плоский dict `{session_state_key: value}`, включая суффиксные widget-ключи
`opt_*__{model_id}`. Legacy-graceful: нет поля → дефолт, `model.price` None → retail.

`apply_kp_snapshot_to_state` — тонкая обёртка над `st.session_state`
(очистка устаревших widget-ключей + применение).

НЕ переиспользует `from_kp._reconstruct_state` — та под договор и лоссова для
конфигуратора (см. docs/audit_kp_snapshot_reconstruction_2026-07-06.md).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

import streamlit as st

from src.data_loader import get_price_by_model_id
from src.filters import model_id_from_cascade

_FOUNDATION_EXECUTION_CHOICES = ("пандусный", "приямок", "монолитная_плита")
_DEFAULT_FOUNDATION_EXECUTION = "пандусный"


def _needs_foundation_choice(key: str) -> bool:
    """Опции, для которых в UI рендерится segmented_control «тип фундамента»
    (зеркалит options_section._requires_foundation_execution_choice)."""
    return (
        key.startswith(("foundation_lite_", "foundation_std_", "foundation_s_f_"))
        or key == "foundation_supervision"
        or key.startswith("construction_works_")
    )


def _parse_kp_date(raw: Any) -> date | None:
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None
    return None


def _coerce_int(value: Any) -> Any:
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def reconstruct_kp_state(kp_row: dict[str, Any], prices: dict) -> dict[str, Any]:
    """Снапшот КП → dict для присвоения в st.session_state (см. модульный docstring)."""
    data = kp_row.get("data") or {}
    model = data.get("model") or {}
    metadata = data.get("metadata") or {}
    payment = data.get("payment") or {}
    equipment = data.get("equipment") or {}
    construction = data.get("construction") or {}
    metrology = data.get("metrology") or {}
    snap_options = data.get("options") or {}

    line = model.get("line", "")
    max_t = _coerce_int(model.get("max"))
    length = _coerce_int(model.get("length"))
    if line and max_t and length:
        model_id = model_id_from_cascade(line, max_t, length)
    else:
        model_id = kp_row.get("model_id", "")
    suffix = f"__{model_id}"

    # model_price: факт. число заморожено в снапшоте; legacy None/0 → retail.
    raw_price = model.get("price")
    if raw_price:
        model_price = int(raw_price)
    else:
        price_entry = get_price_by_model_id(prices, model_id) or {}
        model_price = int(price_entry.get("retail", 0)) or None

    installation_scope = data.get("installation_scope")
    foundation_execution = data.get("foundation_execution")
    is_shefmontazh = installation_scope == "shefmontazh"

    out: dict[str, Any] = {}

    # --- Колонки строки kps (не часть data JSONB) ---
    out["kp_number"] = kp_row.get("kp_number", "")
    out["client_name"] = kp_row.get("client_name", "")
    out["manager_id"] = kp_row.get("manager_id", "")
    out["model_id"] = model_id
    kp_date = _parse_kp_date(kp_row.get("kp_date"))
    if kp_date is not None:
        out["kp_date"] = kp_date

    # --- metadata ---
    if metadata.get("kp_valid_days") is not None:
        out["kp_valid_days"] = metadata["kp_valid_days"]
    if metadata.get("warranty_months") is not None:
        out["warranty_months"] = metadata["warranty_months"]
    # Срок исполнения. Legacy (поля нет) → user_set False, срок пересчитает header.
    out["total_term_days_user_set"] = bool(metadata.get("total_term_days_user_set"))
    out["total_term_days"] = metadata.get("total_term_days")

    # --- model / каскад ---
    out["model_line"] = line
    out["model_max"] = max_t
    out["model_length"] = length
    out["platform_width_m"] = float(model.get("width", 3.0) or 3.0)
    out["model_price"] = model_price
    if model_price is not None:
        out[f"model_price_slider{suffix}"] = model_price
    # Количество весов. Legacy-снапшот без qty → 1.
    model_qty = int(model.get("qty") or 1)
    out["model_qty"] = model_qty
    out[f"model_qty{suffix}"] = model_qty

    # --- equipment ---
    out["sensor_id"] = equipment.get("sensor_id", "")
    out["indicator_id"] = equipment.get("indicator_id", "")
    if equipment.get("cable_m") is not None:
        out["cable_m"] = equipment["cable_m"]

    # --- construction ---
    for snap_key, state_key in (
        ("beam", "construction_beam"),
        ("beam_count", "construction_beam_count"),
        ("center_beam", "construction_center_beam"),
        ("center_beam_count", "construction_center_beam_count"),
        ("deck_mm", "construction_deck_mm"),
        ("underlining_mm", "construction_underlining_mm"),
    ):
        if construction.get(snap_key) is not None:
            out[state_key] = construction[snap_key]

    # --- metrology ---
    out["is_dual_range"] = bool(metrology.get("is_dual_range"))

    # --- foundation / монтаж ---
    out["foundation_execution"] = foundation_execution
    out["is_shefmontazh"] = is_shefmontazh

    # --- options: canonical dict + суффиксные widget-ключи ---
    options: dict[str, Any] = {}
    bytovka_dimensions = ""
    for key, v in snap_options.items():
        price = int(v.get("price") or 0)
        qty = v.get("qty") if v.get("qty") not in (None, "") else 1
        customer_side = bool(v.get("customer_side", False))
        dimensions = v.get("dimensions", "") or ""
        options[key] = {
            "enabled": True,
            "price": price,
            "qty": qty,
            "customer_side": customer_side,
            "is_on_request": False,
            "retail": v.get("retail", price),
            "dealer_is_synthetic": bool(v.get("dealer_is_synthetic", False)),
        }
        if dimensions:
            options[key]["dimensions"] = dimensions

        # Widget-ключи: цена/qty/сторона сидятся из констант (не из canonical),
        # поэтому их ОБЯЗАТЕЛЬНО выставлять напрямую.
        out[f"opt_{key}_enabled{suffix}"] = True
        out[f"opt_{key}_price{suffix}"] = price
        out[f"opt_{key}_qty{suffix}"] = int(qty)
        if key == "verification_default":
            out[f"opt_{key}_side{suffix}"] = "Заказчик" if customer_side else "Подрядчик"
        if key == "bytovka_weigh_room":
            bytovka_dimensions = dimensions
            out[f"opt_{key}_dimensions{suffix}"] = dimensions
        if key == "install_default":
            out[f"opt_{key}_shefmontazh{suffix}"] = is_shefmontazh
        if _needs_foundation_choice(key):
            fe = (
                foundation_execution
                if foundation_execution in _FOUNDATION_EXECUTION_CHOICES
                else _DEFAULT_FOUNDATION_EXECUTION
            )
            out[f"opt_{key}_foundation_execution{suffix}"] = fe

    out["options"] = options
    out["bytovka_dimensions"] = bytovka_dimensions

    # --- spec overrides ---
    out["spec_items_overrides"] = data.get("spec_overrides") or {}

    # --- custom items: снапшот хранит name/price/scope? → переприсваиваем id ---
    from src.contracts.custom_work_types import DEFAULT_WORK_TYPE

    custom: list[dict[str, Any]] = []
    for i, item in enumerate(data.get("custom_items") or [], start=1):
        custom.append({
            "id": f"custom_{i}",
            "name": item.get("name", ""),
            "price": int(item.get("price") or 0),
            # Legacy без поля → «Прочее» (тот же рендер, что и сегодня).
            "scope": item.get("scope", DEFAULT_WORK_TYPE),
        })
    out["custom_items"] = custom
    out["custom_item_next_id"] = len(custom) + 1

    # --- payment (дефолты как в initial_state()/from_kp._reconstruct_state) ---
    out["payment_preset_id"] = payment.get("preset_id", "split_by_items")
    out["payment_days"] = payment.get("days", 5)
    out["payment_custom_text"] = payment.get("custom_text", "")
    out["payment_split_state"] = payment.get("split_state") or {}
    out["payment_v1_prepay"] = payment.get("v1_prepay", 50)
    out["payment_v2_prepay"] = payment.get("v2_prepay", 30)
    out["payment_v2_preship"] = payment.get("v2_preship", 40)
    out["payment_v3_days"] = payment.get("v3_days", 15)
    out["payment_v3_trigger_id"] = payment.get("v3_trigger_id", "after_installation")

    return out


# --- Applier над st.session_state ------------------------------------------

_PURGE_PREFIXES = ("opt_", "model_price_slider__", "split_")
_CUSTOM_WIDGET_RE = re.compile(r"^custom_\d+_(name|price|delete)$")


def _is_purgeable(key: str) -> bool:
    """True для устаревших widget-ключей опций/слайдера/split/custom-строк.

    Радиус: `opt_*`, `model_price_slider__*`, `split_*` (мирроры payment_split_state)
    и `custom_\\d+_(name|price|delete)`. НЕ задевает canonical-ключи `options`,
    `payment_split_state`, `custom_items`, `custom_item_next_id` (не под масками).
    """
    return key.startswith(_PURGE_PREFIXES) or bool(_CUSTOM_WIDGET_RE.match(key))


def _purge_widget_keys() -> None:
    for k in list(st.session_state.keys()):
        if _is_purgeable(k):
            del st.session_state[k]


def apply_kp_snapshot_to_state(kp_row: dict[str, Any], prices: dict) -> None:
    """Очистить устаревшие widget-ключи и применить снапшот КП к st.session_state.

    Запоминает загруженный номер (`_kp_loaded_number`) для предупреждения о
    перезаписи. Вызывать ДО инстанцирования виджетов конфигуратора этим run.
    """
    _purge_widget_keys()
    for key, value in reconstruct_kp_state(kp_row, prices).items():
        st.session_state[key] = value
    st.session_state["_kp_loaded_number"] = kp_row.get("kp_number", "")

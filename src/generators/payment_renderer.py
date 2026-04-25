"""Рендеринг блока «Условия поставки» для DOCX.

Возвращает многострочный plain text — потом докручивается в RichText
в kp_generator.build_template_context.
"""
from __future__ import annotations

from typing import Any


def get_active_payment_groups(spec_items: list[dict]) -> dict:
    """Какие группы оплаты есть в спецификации + есть ли ОРИОН (по ключу orion_*)."""
    groups = {
        g: False
        for g in ("scales", "foundation", "delivery", "installation_and_verification")
    }
    has_orion = False
    for item in spec_items:
        g = item.get("payment_group")
        if g in groups:
            groups[g] = True
        if str(item.get("item_key", "")).startswith("orion_"):
            has_orion = True
    return {"groups": groups, "has_orion": has_orion}


def _split_pct(state: dict, group_id: str, key: str, groups_by_id: dict) -> int:
    """Достать процент из state["payment_split_state"], fallback — default_percents."""
    splits = state.get("payment_split_state") or {}
    group_default = groups_by_id.get(group_id, {}).get("default_percents", {})
    return int(splits.get(group_id, {}).get(key, group_default.get(key, 0)))


def render_split_by_items(
    state: dict[str, Any], spec_items: list[dict], preset: dict
) -> str:
    """Динамическая сборка для пресета split_by_items.

    Состав строк зависит от того, какие группы активны в spec_items.
    """
    active = get_active_payment_groups(spec_items)
    g = active["groups"]
    has_orion = active["has_orion"]

    groups_by_id = {grp["id"]: grp for grp in preset.get("groups", [])}
    pct = lambda gid, k: _split_pct(state, gid, k, groups_by_id)  # noqa: E731

    only_scales = not (g["foundation"] or g["delivery"] or g["installation_and_verification"])
    lines: list[str] = []

    # --- Строка 1: Предоплата ---
    if only_scales and not has_orion:
        lines.append(f"— Предоплата: {pct('scales', 'prepay')}% стоимости проекта.")
    else:
        scales_label = "стоимости весов (включая ПАК ОРИОН)" if has_orion else "стоимости весов"
        prepay_parts = [f"{pct('scales', 'prepay')}% {scales_label}"]
        if g["foundation"]:
            prepay_parts.append(f"{pct('foundation', 'prepay')}% стоимости фундамента")
        lines.append(f"— Предоплата: {' + '.join(prepay_parts)}.")

    # --- Строка 2: Доплата за весы ---
    if only_scales:
        lines.append(
            f"— Доплата: {pct('scales', 'postpay')}% по уведомлению о готовности к отгрузке."
        )
    else:
        postpay_parts = [
            f"{pct('scales', 'postpay')}% по уведомлению о готовности к отгрузке"
        ]
        if g["delivery"]:
            postpay_parts.append(f"{pct('delivery', 'postpay')}% стоимости доставки")
        lines.append(f"— Доплата за весы: {' + '.join(postpay_parts)}.")

    # --- Строка 3: Доплата за фундамент ---
    if g["foundation"]:
        lines.append(
            f"— Доплата за фундамент: {pct('foundation', 'postpay')}% "
            f"по факту готовности фундамента."
        )

    # --- Строка 4: Монтаж и поверка ---
    if g["installation_and_verification"]:
        lines.append(
            f"— Оплата монтажа и поверки: "
            f"{pct('installation_and_verification', 'postpay')}% "
            f"по факту выполнения монтажа и поверки."
        )

    return "\n".join(lines)


def render_simple_preset(state: dict[str, Any], preset: dict) -> str:
    """Рендеринг простых пресетов (prepay_100, 50/50, 30/70, postpay_*)."""
    percents = state.get("payment_percents") or {}
    days = state.get("payment_days") or preset.get("default_days", 5)

    template_vars: dict[str, Any] = {"days": days}
    defaults = preset.get("default_percents", {})
    for key in preset.get("editable_percent_keys", []):
        template_vars[key] = percents.get(key, defaults.get(key, 0))

    body_template = preset.get("body_template", "")
    return body_template.format(**template_vars)


def render_payment_block(
    state: dict[str, Any], spec_items: list[dict], payment_terms_json: dict
) -> str:
    """Главная функция: возвращает готовый plain-text блок «Условия поставки»."""
    preset_id = state.get("payment_preset_id", "split_by_items")
    presets_by_id = {p["id"]: p for p in payment_terms_json.get("presets", [])}
    preset = presets_by_id.get(preset_id)
    if not preset:
        return "—"

    if preset.get("is_freeform"):
        return (state.get("payment_custom_text", "") or "").strip() or "—"

    if preset.get("is_split"):
        return render_split_by_items(state, spec_items, preset)

    return render_simple_preset(state, preset)

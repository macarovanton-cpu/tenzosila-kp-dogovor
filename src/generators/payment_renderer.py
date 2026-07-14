"""Рендеринг блока «Условия поставки» для DOCX.

Возвращает многострочный plain text. В split_by_items и многострочных
простых пресетах каждая строка начинается с «— » (визуальный маркер
списка). Стиль абзаца Word рисует list-marker только для первой строки
параграфа, поэтому маркеры расставляем вручную.
"""
from __future__ import annotations

from typing import Any

from src.payment_wording import (
    TRIGGER_WORDING,
    days_brief,
    default_days,
    default_preset_percents,
    foundation_object,
    installation_object,
    join_ru,
    kind_word,
    scales_object_parts,
    wording_flags,
)

# Сноска под блоком (эталон PAYMENT_SPEC): единица срока вынесена из строк.
FOOTNOTE = "Сроки указаны в банковских днях."


def get_active_payment_groups(spec_items: list[dict]) -> dict:
    """Какие группы оплаты есть в спецификации + есть ли ОРИОН (по ключу orion_*)."""
    groups = dict.fromkeys(("scales", "foundation", "delivery", "installation_and_verification"), False)
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
    """Динамическая сборка для пресета split_by_items (lite-регистр, эталон
    PAYMENT_SPEC).

    Формула строки: «— <Название> <%> <база> <предлог+событие> (<N дней>).»
    Порядок строк — хронология сделки: подписание → Акт фундамента →
    готовность к отгрузке → монтаж/поверка. База — в каждой строке, род.
    падеж («стоимости …»). Строка/фаза с процентом 0 не печатается (W3, реш. 7).
    """
    active = get_active_payment_groups(spec_items)
    g = active["groups"]
    flags = wording_flags(spec_items)
    has_orion = flags["has_orion"]

    groups_by_id = {grp["id"]: grp for grp in preset.get("groups", [])}
    pct = lambda gid, k: _split_pct(state, gid, k, groups_by_id)  # noqa: E731
    days = days_brief(int(state.get("payment_days") or default_days()))

    def event(trigger_key: str) -> str:
        """Событие lite-регистра с предлогом («при подписании…», «по Акту…»)."""
        return TRIGGER_WORDING[trigger_key]["lite"]

    s_prepay, s_post = pct("scales", "prepay"), pct("scales", "postpay")
    f_prepay = pct("foundation", "prepay") if g["foundation"] else 0
    scales_gen = join_ru(scales_object_parts(
        "lite_gen", has_orion, flags["has_ramps"], flags["has_frame"]
    ))
    lines: list[str] = []

    # --- Строка 1: предоплата (весы [+ ОРИОН/рама/пандусы] [+ фундамент]) ---
    # Слияние равных % (F1): весы и фундамент с одинаковым % — процент один раз,
    # объекты через «и»; разные % — раздельно через « + ».
    prepay_parts: list[str] = []
    if s_prepay > 0 and f_prepay > 0 and s_prepay == f_prepay:
        gen_parts = scales_object_parts(
            "lite_gen", has_orion, flags["has_ramps"], flags["has_frame"]
        )
        gen_parts.append("фундамента")
        prepay_parts.append(f"{s_prepay}% стоимости {join_ru(gen_parts)}")
    else:
        if s_prepay > 0:
            prepay_parts.append(f"{s_prepay}% стоимости {scales_gen}")
        if f_prepay > 0:
            prepay_parts.append(f"{f_prepay}% стоимости фундамента")
    if prepay_parts:
        if s_prepay > 0:
            word = kind_word(s_prepay, s_post, "prepay")
        else:
            word = kind_word(f_prepay, pct("foundation", "postpay"), "prepay")
        lines.append(
            f"— {word.capitalize()} {' + '.join(prepay_parts)} "
            f"{event('SPEC_SIGNED')} ({days})."
        )

    # --- Строка 2: доплата за фундамент (хронология: Акт фундамента раньше
    # отгрузки; W9: опоры ОРИОН — объект и триггер) ---
    if g["foundation"]:
        f_post = pct("foundation", "postpay")
        if f_post > 0:
            word = kind_word(f_prepay, f_post, "postpay").capitalize()
            f_obj = foundation_object("lite", flags["has_poles"])
            f_event = event("FOUNDATION_ACT_POLES" if flags["has_poles"] else "FOUNDATION_ACT")
            lines.append(f"— {word} {f_post}% стоимости {f_obj} {f_event} ({days}).")

    # --- Строка 3: доплата за весы [и доставку] (W1-lite: % весов, доставка тем же) ---
    if s_post > 0:
        word = kind_word(s_prepay, s_post, "postpay").capitalize()
        obj_parts = scales_object_parts(
            "lite_gen", has_orion, flags["has_ramps"], flags["has_frame"]
        )
        if g["delivery"]:
            obj_parts.append("доставки")
        lines.append(
            f"— {word} {s_post}% стоимости {join_ru(obj_parts)} "
            f"{event('SHIPMENT_READY')} ({days})."
        )

    # --- Строка 4: монтаж и поверка (обе фазы одной строкой; W6/B11 — состав бакета) ---
    if g["installation_and_verification"]:
        iv_items = [
            it for it in spec_items
            if it.get("payment_group") == "installation_and_verification"
        ]
        iv_label = installation_object("lite", iv_items, bool(state.get("is_shefmontazh")))
        iv_prepay = pct("installation_and_verification", "prepay")
        iv_post = pct("installation_and_verification", "postpay")
        phases: list[str] = []
        if iv_prepay > 0:
            phases.append(
                f"{kind_word(iv_prepay, iv_post, 'prepay')} {iv_prepay}% {event('BRIGADE_READY')}"
            )
        if iv_post > 0:
            phases.append(
                f"{kind_word(iv_prepay, iv_post, 'postpay')} {iv_post}% {event('WORK_ACT')}"
            )
        if phases:
            lines.append(f"— {iv_label}: {', '.join(phases)} ({days}).")

    return "\n".join(lines)


def render_v1(state: dict[str, Any], preset: dict) -> str:
    """Variant 1 — Аванс + Постоплата. Postpay = 100 − prepay."""
    v1_def = default_preset_percents("v1_prepay_postpay")
    prepay = int(state.get("payment_v1_prepay", v1_def.get("prepay", 50)))
    postpay = 100 - prepay
    days = int(state.get("payment_days", preset.get("default_days", 5)))
    return preset.get("body_template", "").format(
        prepay=prepay, postpay=postpay, days_phrase=days_brief(days)
    )


def render_v2(state: dict[str, Any], preset: dict) -> str:
    """Variant 2 — Аванс + Перед отгрузкой + Постоплата. Postpay = 100 − prepay − preship."""
    v2_def = default_preset_percents("v2_prepay_preship_postpay")
    prepay = int(state.get("payment_v2_prepay", v2_def.get("prepay", 30)))
    preship = int(state.get("payment_v2_preship", v2_def.get("preship", 40)))
    postpay = 100 - prepay - preship
    days = int(state.get("payment_days", preset.get("default_days", 5)))
    return preset.get("body_template", "").format(
        prepay=prepay, preship=preship, postpay=postpay,
        days_phrase=days_brief(days)
    )


def render_v3(state: dict[str, Any], preset: dict) -> str:
    """Variant 3 — 100% постоплата с настраиваемой точкой отсчёта."""
    days = int(state.get("payment_v3_days", preset.get("default_days", 15)))
    triggers = preset.get("trigger_options", [])
    trigger_id = state.get(
        "payment_v3_trigger_id", preset.get("default_trigger_id", "")
    )
    trigger_text = next(
        (t["text"] for t in triggers if t["id"] == trigger_id),
        "",
    )
    return preset.get("body_template", "").format(
        days_phrase=days_brief(days), trigger_text=trigger_text
    )


def render_prepay_100(state: dict[str, Any], preset: dict) -> str:
    """100% предоплата — единственное поле: срок."""
    days = int(state.get("payment_days", preset.get("default_days", 5)))
    return preset.get("body_template", "").format(
        p1=100, days_phrase=days_brief(days)
    )


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

    variant = preset.get("variant")
    if preset.get("is_split"):
        text = render_split_by_items(state, spec_items, preset)
    elif variant == "v1":
        text = render_v1(state, preset)
    elif variant == "v2":
        text = render_v2(state, preset)
    elif variant == "v3":
        text = render_v3(state, preset)
    elif preset_id == "prepay_100":
        text = render_prepay_100(state, preset)
    else:
        text = preset.get("body_template", "—")

    if text and text != "—":
        text += f"\n\n{FOOTNOTE}"
    return text

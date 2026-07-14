"""payment_line.py — строка платёжного раздела спецификации."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from src.contracts.utils import due_days_phrase, number_to_words, rubles_word
from src.payment_wording import (
    TRIGGER_WORDING,
    default_days,
    default_preset_percents,
    default_split_percents,
    foundation_object,
    installation_object,
    join_ru,
    kind_word,
    scales_object_parts,
    wording_flags,
)


class PaymentCoverageError(ValueError):
    """Строки оплаты не покрывают сумму, которую движок обязан выставить.

    Инвариант-страж A9 (по образцу A5): фантомный процент (delivery.prepay)
    молча занижает график — недобор ловим на выходе build_lines_from_snapshot.
    """


class PaymentTrigger(str, Enum):
    SPEC_SIGNED         = "SPEC_SIGNED"
    SPEC_SIGNED_INVOICE = "SPEC_SIGNED_INVOICE"    # W7: prepay_100, основание «счёт»
    FOUNDATION_ACT      = "FOUNDATION_ACT"
    FOUNDATION_ACT_POLES = "FOUNDATION_ACT_POLES"  # W9: + установка опор и кабель-трасс
    SHIPMENT_READY      = "SHIPMENT_READY"
    BRIGADE_READY       = "BRIGADE_READY"
    WORK_ACT            = "WORK_ACT"
    DELIVERED           = "DELIVERED"


# full-регистр общего словаря (единственный источник формулировок триггеров).
# Имя и форма сохранены — их импортируют supply_filler и payment_lines_editor.
TRIGGER_TEXTS: dict[PaymentTrigger, str] = {
    t: TRIGGER_WORDING[t.value]["full"] for t in PaymentTrigger
}


@dataclass
class PaymentLine:
    kind:         Literal["предоплата", "доплата", "оплата"]
    share_pct:    float | None
    share_prep:   Literal["от стоимости", "за", "от"] | None
    share_object: str
    amount:       int
    trigger:      PaymentTrigger
    due:          int
    due_unit:     Literal["банковских", "рабочих", "календарных"] = field(default="банковских")
    # База, от которой считается amount = round(share_pct/100 × base_amount).
    # Не-split — ИТОГО спецификации; split — комбинированный итог бакетов строки.
    base_amount:  int | None = field(default=None)


def format_payment_line(
    line: PaymentLine,
    index: int,
    trigger_texts: dict | None = None,
) -> str:
    """Форматировать строку оплаты.

    trigger_texts — опциональный словарь текстов триггеров (например,
    SUPPLY_TRIGGER_TEXTS из supply_filler.py). Дефолт — TRIGGER_TEXTS.
    Spec-флоу вызывает без этого аргумента → поведение не меняется.
    """
    amount_fmt  = "{:,}".format(line.amount).replace(",", chr(32))
    words       = number_to_words(line.amount).strip()  # W4: пропись строчными
    due_phrase  = due_days_phrase(line.due, line.due_unit)
    trigger_txt = (trigger_texts or TRIGGER_TEXTS)[line.trigger]
    kind_cap    = line.kind.capitalize()

    if line.share_pct is not None:
        pct = int(line.share_pct) if line.share_pct == int(line.share_pct) else line.share_pct
        share = f"{pct}% {line.share_prep} {line.share_object}"
        return (
            f"{index}. {kind_cap} {share} в размере "
            f"{amount_fmt} ({words}) {rubles_word(line.amount)}, в т.ч. НДС 22%, "
            f"в течение {due_phrase} "
            f"с момента {trigger_txt}."
        )
    else:
        return (
            f"{index}. {kind_cap} в размере "
            f"{amount_fmt} ({words}) {rubles_word(line.amount)}, в т.ч. НДС 22%, "
            f"в течение {due_phrase} "
            f"с момента {trigger_txt}."
        )


# ---------------------------------------------------------------------------
# Bridge: snapshot.payment + spec_items → list[PaymentLine]
# ---------------------------------------------------------------------------

# Маппинг v3 trigger_id → PaymentTrigger
_V3_TRIGGER_MAP: dict[str, PaymentTrigger] = {
    "after_delivery":     PaymentTrigger.DELIVERED,
    "after_installation": PaymentTrigger.WORK_ACT,
    "after_act":          PaymentTrigger.WORK_ACT,
}


def _spec_total(spec_items: list[dict]) -> int:
    """Σ стоимости всех позиций спецификации (зеркало редактора payment_lines_editor)."""
    return sum(int(it.get("total") or 0) for it in spec_items)


def _non_split_phases(
    payment: dict,
) -> tuple[list[tuple[str, int, PaymentTrigger]], int]:
    """Фазы (kind, pct, trigger) и срок для не-split пресетов.

    Возвращает ([], 0) для custom и неизвестных пресетов.
    Дефолты процентов/дней совпадают с defaults в state.py.
    """
    preset_id = payment.get("preset_id", "")
    days = int(payment.get("days") or default_days())

    if preset_id == "v1_prepay_postpay":
        v1_def = default_preset_percents("v1_prepay_postpay")
        prepay = int(payment.get("v1_prepay") or v1_def.get("prepay", 50))
        postpay = 100 - prepay
        return [
            ("предоплата", prepay,   PaymentTrigger.SPEC_SIGNED),
            ("доплата",    postpay,  PaymentTrigger.WORK_ACT),
        ], days

    if preset_id == "v2_prepay_preship_postpay":
        v2_def  = default_preset_percents("v2_prepay_preship_postpay")
        prepay  = int(payment.get("v2_prepay")  or v2_def.get("prepay", 30))
        v2_preship = payment.get("v2_preship")
        preship = v2_def.get("preship", 40) if v2_preship is None else int(v2_preship)
        postpay = 100 - prepay - preship
        return [
            ("предоплата", prepay,   PaymentTrigger.SPEC_SIGNED),
            ("доплата",    preship,  PaymentTrigger.SHIPMENT_READY),
            ("доплата",    postpay,  PaymentTrigger.WORK_ACT),
        ], days

    if preset_id == "v3_postpay_only":
        v3_days    = int(payment.get("v3_days") or 15)
        trigger_id = payment.get("v3_trigger_id") or "after_installation"
        trigger    = _V3_TRIGGER_MAP.get(trigger_id, PaymentTrigger.WORK_ACT)
        return [
            ("оплата", 100, trigger),
        ], v3_days

    if preset_id == "prepay_100":
        # W7: простая поставка — основание «счёт» в триггере.
        return [
            ("предоплата", 100, PaymentTrigger.SPEC_SIGNED_INVOICE),
        ], days

    # custom и неизвестные пресеты — свободный текст, строки не генерируем
    return [], 0


def _build_non_split_lines(
    payment: dict, spec_items: list[dict], model_qty: int = 1
) -> list[PaymentLine]:
    """PaymentLine-строки для не-split пресетов (base = общая сумма спецификации).

    Последняя строка добирает остаток, чтобы Σamount == ИТОГО точно.
    Фазы с pct == 0 и строки с amount == 0 пропускаются.
    base = подытог_за_1 × model_qty (spec_items per-unit).
    """
    phases, due = _non_split_phases(payment)
    phases = [(k, p, t) for k, p, t in phases if p > 0]
    if not phases:
        return []

    total = _spec_total(spec_items) * int(model_qty or 1)
    lines: list[PaymentLine] = []
    assigned = 0

    for i, (kind, pct, trigger) in enumerate(phases):
        is_last = (i == len(phases) - 1)
        if is_last:
            amt = total - assigned
        else:
            amt = round(total * pct / 100)
        if amt == 0:
            assigned += amt
            continue
        lines.append(PaymentLine(
            kind=kind,
            share_pct=float(pct),
            share_prep="от",
            share_object="общей цены договора",
            amount=amt,
            trigger=trigger,
            due=due,
            base_amount=total,
        ))
        assigned += amt

    return lines

def orion_poles_without_foundation(spec_items: list[dict]) -> bool:
    """True, если бакет foundation в спецификации состоит ТОЛЬКО из опор ОРИОН.

    Опоры (orion_cable_poles, spec id "orion_poles") оплачиваются в одном бакете
    с фундаментом (resolve_payment_group, эталон A1). Если в бакете нет ничего,
    кроме опор — значит физического фундамента в сделке нет, а автотекст оплаты
    и Акта всё равно сошлётся на «фундамент».
    """
    foundation_items = [it for it in spec_items if it.get("payment_group") == "foundation"]
    has_poles = any(it.get("id") == "orion_poles" for it in foundation_items)
    return has_poles and all(it.get("id") == "orion_poles" for it in foundation_items)


def _active_buckets(spec_items: list[dict]) -> dict[str, bool]:
    """Какие группы оплаты есть в спецификации (payment_group → bool).

    Локальная копия логики generators.payment_renderer.get_active_payment_groups —
    contracts не зависит от рендер-слоя. Флаги формулировок (ОРИОН, опоры,
    рама/пандусы) — payment_wording.wording_flags.
    """
    groups = dict.fromkeys(
        ("scales", "foundation", "delivery", "installation_and_verification"), False
    )
    for item in spec_items:
        g = item.get("payment_group")
        if g in groups:
            groups[g] = True
    return groups


def _split_pct(split_state: dict, group_id: str, key: str) -> int:
    """Процент из split_state[group][key], fallback — дефолты из payment_terms.json.

    На практике UI (payment_section._render_split) заполняет split_state теми же
    значениями до снапшота — fallback лишь страхует битые снапшоты.
    """
    grp = split_state.get(group_id) or {}
    if key in grp:
        return int(grp[key])
    return int(default_split_percents().get(group_id, {}).get(key, 0))


def _bucket_total(spec_items: list[dict], bucket: str) -> int:
    """Σ стоимости позиций бакета. customer_side имеют total=0 → не влияют."""
    total = 0
    for it in spec_items:
        if it.get("payment_group") != bucket:
            continue
        if "total" in it:
            total += int(it["total"])
        else:
            total += int(it.get("price", 0)) * int(it.get("qty", 0))
    return total


def _amount(total: int, pct: int) -> int:
    """Черновая сумма, round до рубля."""
    return round(total * pct / 100)


def _assert_payment_covers(lines: list[PaymentLine], expected: int) -> None:
    """Страж A9: Σ amount строк оплаты сверяется с `expected` этой ветки —
    split передаёт Σ 4 бакетов (scales+foundation+delivery+iv), non-split —
    _spec_total×qty. Фантомный процент (delivery.prepay) ловится здесь.

    Границы (по факту, не «любой путь, 100% ИТОГО»):
    - split: `expected` — сумма ТОЛЬКО забакеченных позиций. Позиция с
      payment_group=None невидима стражу с обеих сторон (ни в lines, ни в
      expected) — недобор такой позиции страж не увидит (см. B9 F2).
    - проверка АГРЕГАТНАЯ, не по-бакетно: переплата одного бакета маскирует
      недобор другого при том же суммарном допуске (см. B9 F1).
    - вызывается на build-time, внутри build_lines_from_snapshot
      (default_payment_rows — автопосев/кнопка «Заполнить по умолчанию»).
      Финальная генерация (fill_spec_v2, build_supply_context) эту функцию не
      зовёт — она форматирует уже сохранённые payment_lines (см. B9 F3/F4).

    Суммируем реальные amount строк, НЕ реконструируем %×база — иначе споткнулись
    бы о ту же мину составной строки, из-за которой отложена W1.

    Допуск: каждая amount = round(...) округляется независимо (≤0,5 ₽), суммарный
    дрейф < числа строк. max(len, 1) ₽ — та же граница, что в редакторе
    (payment_lines_editor._validate_rows). Пустой график (custom) — расчёта нет.
    """
    if not lines:
        return
    covered = sum(ln.amount for ln in lines)
    tol = max(len(lines), 1)
    if abs(expected - covered) > tol:
        raise PaymentCoverageError(
            f"Строки оплаты покрывают {covered} из {expected} "
            f"(недобор {expected - covered}); проверь фантомные проценты "
            f"(delivery.prepay)."
        )


def build_lines_from_snapshot(
    payment: dict,
    spec_items: list[dict],
    model_qty: int = 1,
    installation_scope: str | None = None,
) -> list[PaymentLine]:
    """Черновые строки платёжного раздела из снапшота оплаты.

    split_by_items — строки по бакетам; прочие пресеты — строки от общей суммы;
    custom → []. Строка пропускается, если управляющий процент == 0 или сумма == 0.

    installation_scope — из снапшота КП (W6): "shefmontazh" → объект монтажа
    «шеф-монтажных работ и поверки».

    spec_items остаются per-unit; суммы бакетов домножаются на model_qty
    (график покрывает подытог_за_1 × qty).
    """
    payment = payment or {}
    qty = int(model_qty or 1)
    if payment.get("preset_id") != "split_by_items":
        lines = _build_non_split_lines(payment, spec_items, qty)
        # non-split бьёт весь _spec_total (остаток добирается последней фазой);
        # позиции без бакета там тоже выставлены → сверяем с полным ИТОГО.
        _assert_payment_covers(lines, _spec_total(spec_items) * qty)
        return lines

    split_state = payment.get("split_state") or {}
    days = int(payment.get("days") or default_days())

    g = _active_buckets(spec_items)
    flags = wording_flags(spec_items)

    scales_total     = _bucket_total(spec_items, "scales") * qty
    foundation_total = _bucket_total(spec_items, "foundation") * qty
    delivery_total   = _bucket_total(spec_items, "delivery") * qty
    iv_total         = _bucket_total(spec_items, "installation_and_verification") * qty

    pct = lambda gid, k: _split_pct(split_state, gid, k)  # noqa: E731
    lines: list[PaymentLine] = []

    # Проценты бакета весов нужны для обеих строк (L1 предоплата, L3 доплата)
    # и для слова-типа (W3): единичный платёж → «оплата», парный → пред/доплата.
    s_prepay = pct("scales", "prepay")
    s_post   = pct("scales", "postpay")

    # Объект «весы»: ОРИОН + рама/пандусы называются (реш. Антона, механизм W9).
    scales_parts = scales_object_parts(
        "full", flags["has_orion"], flags["has_ramps"], flags["has_frame"]
    )

    # L1 — SPEC_SIGNED (весы [+ ОРИОН/рама/пандусы] [+ фундамент])
    amt = _amount(scales_total, s_prepay)
    obj_parts = list(scales_parts)
    share_pct_l1: float | None = float(s_prepay)
    base_l1 = scales_total
    if g["foundation"]:
        obj_parts.append("фундамента Весов")
        f_prepay = pct("foundation", "prepay")
        amt += _amount(foundation_total, f_prepay)
        base_l1 += foundation_total
        # Осознанная защёлка L1 (не в W-списке): разные % предоплаты весов и
        # фундамента → печатаем плоскую сумму без %. На дефолте (50/50) не срабатывает.
        if f_prepay != s_prepay:
            share_pct_l1 = None
    if amt != 0:
        lines.append(PaymentLine(
            kind_word(s_prepay, s_post, "prepay"), share_pct_l1,
            "от стоимости" if share_pct_l1 is not None else None,
            join_ru(obj_parts), amt, PaymentTrigger.SPEC_SIGNED, days,
            base_amount=base_l1,
        ))

    # L2 — акт фундамента (W9: опоры ОРИОН — объект и расширенный триггер)
    if g["foundation"]:
        f_prepay = pct("foundation", "prepay")
        f_post = pct("foundation", "postpay")
        amt = _amount(foundation_total, f_post)
        if f_post != 0 and amt != 0:
            lines.append(PaymentLine(
                kind_word(f_prepay, f_post, "postpay"), float(f_post),
                "от стоимости", foundation_object("full", flags["has_poles"]), amt,
                PaymentTrigger.FOUNDATION_ACT_POLES if flags["has_poles"]
                else PaymentTrigger.FOUNDATION_ACT,
                days,
                base_amount=foundation_total,
            ))

    # L3 — SHIPMENT_READY (весы [+ доставка])
    amt = _amount(scales_total, s_post)
    obj_parts = list(scales_parts)
    share_pct_l3: float | None = float(s_post)
    base_l3 = scales_total
    if g["delivery"]:
        obj_parts.append("доставки")
        d_post = pct("delivery", "postpay")
        amt += _amount(delivery_total, d_post)
        base_l3 += delivery_total
        # Защёлка (как у L1): разные % весов и доставки → плоская сумма без %.
        # Пересчёт графика (payment_lines_editor._recompute_amounts, autoverify)
        # реконструирует сумму из одного %×база и не умеет разложить составную
        # (s_post%·весы + d_post%·доставка). flat сохраняет её как есть.
        # W1 (печать scales.postpay% + объект) отложена в Стадию 2 — вместе с
        # правкой пересчёта, иначе график молча недобирает 50%·доставки.
        if d_post != s_post:
            share_pct_l3 = None
    if amt != 0:
        lines.append(PaymentLine(
            kind_word(s_prepay, s_post, "postpay"), share_pct_l3,
            "от стоимости" if share_pct_l3 is not None else None,
            join_ru(obj_parts), amt, PaymentTrigger.SHIPMENT_READY, days,
            base_amount=base_l3,
        ))

    # L4/L5 — монтаж и поверка (W6/B11: объект по составу iv-бакета)
    if g["installation_and_verification"]:
        iv_items = [
            it for it in spec_items
            if it.get("payment_group") == "installation_and_verification"
        ]
        iv_obj = installation_object("full", iv_items, installation_scope == "shefmontazh")
        iv_prepay = pct("installation_and_verification", "prepay")
        iv_post   = pct("installation_and_verification", "postpay")
        if iv_prepay > 0:
            amt = _amount(iv_total, iv_prepay)
            if amt != 0:
                lines.append(PaymentLine(
                    kind_word(iv_prepay, iv_post, "prepay"), float(iv_prepay),
                    "от стоимости", iv_obj, amt,
                    PaymentTrigger.BRIGADE_READY, days,
                    base_amount=iv_total,
                ))
        amt = _amount(iv_total, iv_post)
        if iv_post != 0 and amt != 0:
            lines.append(PaymentLine(
                kind_word(iv_prepay, iv_post, "postpay"), float(iv_post),
                "от стоимости", iv_obj, amt,
                PaymentTrigger.WORK_ACT, days,
                base_amount=iv_total,
            ))

    # Страж покрытия: строки должны выставить всю сумму 4 бакетов. Фантом
    # delivery.prepay недобирает бакет доставки → падаем. Позиция без бакета
    # (payment_group=None) исключена из обеих частей — её ловит UI (st.error).
    _assert_payment_covers(
        lines, scales_total + foundation_total + delivery_total + iv_total
    )
    return lines

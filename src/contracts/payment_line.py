"""payment_line.py — строка платёжного раздела спецификации."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from src.contracts.utils import days_genitive, number_to_words


class PaymentTrigger(str, Enum):
    SPEC_SIGNED    = "SPEC_SIGNED"
    FOUNDATION_ACT = "FOUNDATION_ACT"
    SHIPMENT_READY = "SHIPMENT_READY"
    BRIGADE_READY  = "BRIGADE_READY"
    WORK_ACT       = "WORK_ACT"
    DELIVERED      = "DELIVERED"


TRIGGER_TEXTS: dict[PaymentTrigger, str] = {
    PaymentTrigger.SPEC_SIGNED:    "подписания настоящей Спецификации",
    PaymentTrigger.FOUNDATION_ACT: "подписания Акта выполненных работ по строительству фундамента",
    PaymentTrigger.SHIPMENT_READY: "получения уведомления о готовности Весов к отгрузке",
    PaymentTrigger.BRIGADE_READY:  "уведомления о готовности принять монтажную бригаду на месте монтажа",
    PaymentTrigger.WORK_ACT:       "подписания Акта выполненных работ по настоящей Спецификации",
    PaymentTrigger.DELIVERED:      "поставки Весов Заказчику",
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


def format_payment_line(line: PaymentLine, index: int) -> str:
    amount_fmt  = "{:,}".format(line.amount).replace(",", chr(32))
    words       = number_to_words(line.amount).strip()
    due_words   = days_genitive(line.due)
    trigger_txt = TRIGGER_TEXTS[line.trigger]
    kind_cap    = line.kind.capitalize()

    if line.share_pct is not None:
        pct = int(line.share_pct) if line.share_pct == int(line.share_pct) else line.share_pct
        share = f"{pct}% {line.share_prep} {line.share_object}"
        return (
            f"{index}. {kind_cap} {share} в размере "
            f"{amount_fmt} ({words}) рублей, в т.ч. НДС 22%, "
            f"в течение {line.due} ({due_words}) {line.due_unit} дней "
            f"с момента {trigger_txt}."
        )
    else:
        return (
            f"{index}. {kind_cap} в размере "
            f"{amount_fmt} ({words}) рублей, в т.ч. НДС 22%, "
            f"в течение {line.due} ({due_words}) {line.due_unit} дней "
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
    days = int(payment.get("days") or 5)

    if preset_id == "v1_prepay_postpay":
        prepay = int(payment.get("v1_prepay") or 50)
        postpay = 100 - prepay
        return [
            ("предоплата", prepay,   PaymentTrigger.SPEC_SIGNED),
            ("доплата",    postpay,  PaymentTrigger.WORK_ACT),
        ], days

    if preset_id == "v2_prepay_preship_postpay":
        prepay  = int(payment.get("v2_prepay")  or 30)
        preship = int(payment.get("v2_preship") or 40)
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
        return [
            ("предоплата", 100, PaymentTrigger.SPEC_SIGNED),
        ], days

    # custom и неизвестные пресеты — свободный текст, строки не генерируем
    return [], 0


def _build_non_split_lines(
    payment: dict, spec_items: list[dict]
) -> list[PaymentLine]:
    """PaymentLine-строки для не-split пресетов (base = общая сумма спецификации).

    Последняя строка добирает остаток, чтобы Σamount == ИТОГО точно.
    Фазы с pct == 0 и строки с amount == 0 пропускаются.
    """
    phases, due = _non_split_phases(payment)
    phases = [(k, p, t) for k, p, t in phases if p > 0]
    if not phases:
        return []

    total = _spec_total(spec_items)
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

# Fallback дефолтов, когда split_state не заполнен. На практике UI
# (payment_section._render_split) заполняет split_state этими же значениями
# до снапшота — это лишь страховка для битых снапшотов.
_DEFAULT_SPLIT_PERCENTS: dict[str, dict[str, int]] = {
    "scales":                        {"prepay": 50, "postpay": 50},
    "foundation":                    {"prepay": 50, "postpay": 50},
    "delivery":                      {"prepay": 0,  "postpay": 100},
    "installation_and_verification": {"prepay": 0,  "postpay": 100},
}


def _active_buckets(spec_items: list[dict]) -> dict:
    """Какие группы оплаты есть в спецификации + есть ли ОРИОН (item_key orion_*).

    Локальная копия логики generators.payment_renderer.get_active_payment_groups —
    contracts не зависит от рендер-слоя.
    """
    groups = dict.fromkeys(
        ("scales", "foundation", "delivery", "installation_and_verification"), False
    )
    has_orion = False
    for item in spec_items:
        g = item.get("payment_group")
        if g in groups:
            groups[g] = True
        if str(item.get("item_key") or item.get("id", "")).startswith("orion_"):
            has_orion = True
    return {"groups": groups, "has_orion": has_orion}


def _split_pct(split_state: dict, group_id: str, key: str) -> int:
    """Процент из split_state[group][key], fallback — _DEFAULT_SPLIT_PERCENTS."""
    grp = split_state.get(group_id) or {}
    if key in grp:
        return int(grp[key])
    return int(_DEFAULT_SPLIT_PERCENTS.get(group_id, {}).get(key, 0))


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


def build_lines_from_snapshot(
    payment: dict, spec_items: list[dict]
) -> list[PaymentLine]:
    """Черновые строки платёжного раздела из снапшота оплаты.

    split_by_items — строки по бакетам; прочие пресеты — строки от общей суммы;
    custom → []. Строка пропускается, если управляющий процент == 0 или сумма == 0.
    """
    payment = payment or {}
    if payment.get("preset_id") != "split_by_items":
        return _build_non_split_lines(payment, spec_items)

    split_state = payment.get("split_state") or {}
    days = int(payment.get("days") or 5)

    active = _active_buckets(spec_items)
    g = active["groups"]
    has_orion = active["has_orion"]

    scales_total     = _bucket_total(spec_items, "scales")
    foundation_total = _bucket_total(spec_items, "foundation")
    delivery_total   = _bucket_total(spec_items, "delivery")
    iv_total         = _bucket_total(spec_items, "installation_and_verification")

    pct = lambda gid, k: _split_pct(split_state, gid, k)  # noqa: E731
    lines: list[PaymentLine] = []

    # L1 — предоплата SPEC_SIGNED (весы [+ ОРИОН] [+ фундамент])
    s_prepay = pct("scales", "prepay")
    amt = _amount(scales_total, s_prepay)
    obj = "Весов (включая ПАК ОРИОН)" if has_orion else "Весов"
    share_pct_l1: float | None = float(s_prepay)
    base_l1 = scales_total
    if g["foundation"]:
        obj += " и фундамента Весов"
        f_prepay = pct("foundation", "prepay")
        amt += _amount(foundation_total, f_prepay)
        base_l1 += foundation_total
        if f_prepay != s_prepay:
            share_pct_l1 = None
    if s_prepay != 0 and amt != 0:
        lines.append(PaymentLine(
            "предоплата", share_pct_l1,
            "от стоимости" if share_pct_l1 is not None else None,
            obj, amt, PaymentTrigger.SPEC_SIGNED, days,
            base_amount=base_l1,
        ))

    # L2 — доплата FOUNDATION_ACT
    if g["foundation"]:
        f_post = pct("foundation", "postpay")
        amt = _amount(foundation_total, f_post)
        if f_post != 0 and amt != 0:
            lines.append(PaymentLine(
                "доплата", float(f_post), "от стоимости", "фундамента Весов", amt,
                PaymentTrigger.FOUNDATION_ACT, days,
                base_amount=foundation_total,
            ))

    # L3 — доплата SHIPMENT_READY (весы [+ доставка])
    s_post = pct("scales", "postpay")
    amt = _amount(scales_total, s_post)
    obj = "Весов"
    share_pct_l3: float | None = float(s_post)
    base_l3 = scales_total
    if g["delivery"]:
        obj += " и доставки"
        d_post = pct("delivery", "postpay")
        amt += _amount(delivery_total, d_post)
        base_l3 += delivery_total
        if d_post != s_post:
            share_pct_l3 = None
    if s_post != 0 and amt != 0:
        lines.append(PaymentLine(
            "доплата", share_pct_l3,
            "от стоимости" if share_pct_l3 is not None else None,
            obj, amt, PaymentTrigger.SHIPMENT_READY, days,
            base_amount=base_l3,
        ))

    # L4/L5 — монтаж и поверка
    if g["installation_and_verification"]:
        iv_prepay = pct("installation_and_verification", "prepay")
        if iv_prepay > 0:
            amt = _amount(iv_total, iv_prepay)
            if amt != 0:
                lines.append(PaymentLine(
                    "предоплата", float(iv_prepay), "от стоимости",
                    "монтажных работ и поверки", amt,
                    PaymentTrigger.BRIGADE_READY, days,
                    base_amount=iv_total,
                ))
        iv_post = pct("installation_and_verification", "postpay")
        amt = _amount(iv_total, iv_post)
        if iv_post != 0 and amt != 0:
            lines.append(PaymentLine(
                "доплата", float(iv_post), "от стоимости",
                "монтажных работ и поверки", amt,
                PaymentTrigger.WORK_ACT, days,
                base_amount=iv_total,
            ))

    return lines

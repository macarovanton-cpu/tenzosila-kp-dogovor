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
    kind:         Literal["предоплата", "доплата"]
    share_pct:    float | None
    share_prep:   Literal["от стоимости", "за"] | None
    share_object: str
    amount:       int
    trigger:      PaymentTrigger
    due:          int
    due_unit:     Literal["банковских", "рабочих", "календарных"] = field(default="банковских")


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
# Только для пресета split_by_items; прочие пресеты → []
# (менеджер заполнит редактор вручную на шаге 4).
# ---------------------------------------------------------------------------

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
        if str(item.get("item_key", "")).startswith("orion_"):
            has_orion = True
    return {"groups": groups, "has_orion": has_orion}


def _split_pct(split_state: dict, group_id: str, key: str) -> int:
    """Процент из split_state[group][key], fallback — _DEFAULT_SPLIT_PERCENTS."""
    grp = split_state.get(group_id) or {}
    if key in grp:
        return int(grp[key])
    return int(_DEFAULT_SPLIT_PERCENTS.get(group_id, {}).get(key, 0))


def _bucket_total(spec_items: list[dict], bucket: str) -> int:
    """Σ(price×qty) по позициям бакета. customer_side имеют price=0 → не влияют."""
    return sum(
        int(it.get("price", 0)) * int(it.get("qty", 0))
        for it in spec_items
        if it.get("payment_group") == bucket
    )


def _amount(total: int, pct: int) -> int:
    """Черновая сумма, round до рубля."""
    return round(total * pct / 100)


def build_lines_from_snapshot(
    payment: dict, spec_items: list[dict]
) -> list[PaymentLine]:
    """Черновые строки платёжного раздела для пресета split_by_items.

    Прочие пресеты (v1/v2/v3/prepay_100/custom) → []. Строка пропускается, если её
    управляющий процент == 0 или итоговая сумма == 0.
    """
    payment = payment or {}
    if payment.get("preset_id") != "split_by_items":
        return []

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
    if g["foundation"]:
        obj += " и фундамента Весов"
        f_prepay = pct("foundation", "prepay")
        amt += _amount(foundation_total, f_prepay)
        if f_prepay != s_prepay:
            share_pct_l1 = None
    if s_prepay != 0 and amt != 0:
        lines.append(PaymentLine(
            "предоплата", share_pct_l1,
            "от стоимости" if share_pct_l1 is not None else None,
            obj, amt, PaymentTrigger.SPEC_SIGNED, days,
        ))

    # L2 — доплата FOUNDATION_ACT
    if g["foundation"]:
        f_post = pct("foundation", "postpay")
        amt = _amount(foundation_total, f_post)
        if f_post != 0 and amt != 0:
            lines.append(PaymentLine(
                "доплата", float(f_post), "от стоимости", "фундамента Весов", amt,
                PaymentTrigger.FOUNDATION_ACT, days,
            ))

    # L3 — доплата SHIPMENT_READY (весы [+ доставка])
    s_post = pct("scales", "postpay")
    amt = _amount(scales_total, s_post)
    obj = "Весов"
    share_pct_l3: float | None = float(s_post)
    if g["delivery"]:
        obj += " и доставки"
        d_post = pct("delivery", "postpay")
        amt += _amount(delivery_total, d_post)
        if d_post != s_post:
            share_pct_l3 = None
    if s_post != 0 and amt != 0:
        lines.append(PaymentLine(
            "доплата", share_pct_l3,
            "от стоимости" if share_pct_l3 is not None else None,
            obj, amt, PaymentTrigger.SHIPMENT_READY, days,
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
                ))
        iv_post = pct("installation_and_verification", "postpay")
        amt = _amount(iv_total, iv_post)
        if iv_post != 0 and amt != 0:
            lines.append(PaymentLine(
                "доплата", float(iv_post), "от стоимости",
                "монтажных работ и поверки", amt,
                PaymentTrigger.WORK_ACT, days,
            ))

    return lines

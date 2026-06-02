"""payment_line.py — строка платёжного раздела спецификации."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from src.contracts.utils import number_to_words


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

_DUE_WORDS: dict[int, str] = {
    3:  "трёх",
    5:  "пяти",
    10: "десяти",
    14: "четырнадцати",
    20: "двадцати",
    30: "тридцати",
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
    if line.due not in _DUE_WORDS:
        raise ValueError(f"due={line.due} не поддерживается; допустимые: {sorted(_DUE_WORDS)}")

    amount_fmt  = "{:,}".format(line.amount).replace(",", chr(32))
    words       = number_to_words(line.amount).strip()
    due_words   = _DUE_WORDS[line.due]
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

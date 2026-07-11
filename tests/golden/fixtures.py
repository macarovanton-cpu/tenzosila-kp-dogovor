"""Загрузка и валидация JSON-фикстур golden-master харнесса (P0-02).

Формат идентичен tests/autoverify/fixtures.py (не общий модуль — golden и
autoverify фиксируют разные вещи и могут разойтись, см. MIGRATION_PLAN.md §2).
Фикстура = входная карточка сделки: KP-state (как в st.session_state КП),
реквизиты заказчика и параметры договора. КП-снапшот отдельно не хранится —
его строит build_kp_snapshot() внутри generate_all().
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_REQUIRED_TOP = ("meta", "kp_state", "requisites", "contract")
_REQUIRED_META = ("id", "flow")
_REQUIRED_CONTRACT = (
    "contract_date", "contract_number", "spec_number", "object_address",
)
_FLOWS = ("spec", "supply")


@dataclass(frozen=True)
class Fixture:
    """Разобранная фикстура сделки."""
    id: str
    flow: str                         # ожидаемый тип документа: spec | supply
    comment: str                      # описание кейса (справочно)
    kp_state: dict[str, Any]          # плоский KP-state (kp_date уже date)
    requisites: dict[str, str]
    contract_date: date
    contract_number: str
    spec_number: str
    object_address: str
    scope_overrides: dict[str, Any]
    flags: dict[str, Any]
    # None → сидинг строк оплаты из снапшота КП (реплика «Заполнить по умолчанию»)
    payment_rows: list[dict[str, Any]] | None
    valid_until: date | None          # только для supply-флоу


def list_fixture_ids() -> list[str]:
    """Отсортированные id всех фикстур в fixtures/."""
    return sorted(p.stem for p in FIXTURES_DIR.glob("*.json"))


def load_fixture(fixture_id: str) -> Fixture:
    """Прочитать fixtures/<id>.json, проверить обязательные ключи."""
    path = FIXTURES_DIR / f"{fixture_id}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))

    missing = [k for k in _REQUIRED_TOP if k not in raw]
    if missing:
        raise ValueError(f"{path.name}: нет секций {missing}")

    meta = raw["meta"]
    for key in _REQUIRED_META:
        if not meta.get(key):
            raise ValueError(f"{path.name}: meta.{key} обязателен")
    if meta["flow"] not in _FLOWS:
        raise ValueError(f"{path.name}: meta.flow={meta['flow']!r}, ожидалось {_FLOWS}")
    if meta["id"] != fixture_id:
        raise ValueError(f"{path.name}: meta.id={meta['id']!r} != имени файла")

    contract = raw["contract"]
    for key in _REQUIRED_CONTRACT:
        if not contract.get(key):
            raise ValueError(f"{path.name}: contract.{key} обязателен")

    kp_state = dict(raw["kp_state"])
    # Дата КП обязана быть пиновой — иначе date.today() ломает детерминизм.
    if not kp_state.get("kp_date"):
        raise ValueError(f"{path.name}: kp_state.kp_date обязателен (детерминизм)")
    kp_state["kp_date"] = date.fromisoformat(kp_state["kp_date"])

    valid_until_raw = contract.get("valid_until")

    return Fixture(
        id=meta["id"],
        flow=meta["flow"],
        comment=meta.get("comment", ""),
        kp_state=kp_state,
        requisites=dict(raw["requisites"]),
        contract_date=date.fromisoformat(contract["contract_date"]),
        contract_number=contract["contract_number"],
        spec_number=contract["spec_number"],
        object_address=contract["object_address"],
        scope_overrides=dict(contract.get("scope_overrides") or {}),
        flags=dict(contract.get("flags") or {}),
        payment_rows=contract.get("payment_rows"),
        valid_until=date.fromisoformat(valid_until_raw) if valid_until_raw else None,
    )

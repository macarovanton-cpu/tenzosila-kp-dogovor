"""Headless-раннер генерации КП + договора + спецификации на фикстуре.

⚠️ ЗЕРКАЛО глюкода src/pages/2_Договор.py:959-1010 (кнопка «Сгенерировать
договор и спецификацию») — менять ПАРНО с страницей. Постоянный фикс —
вынос общего кода в src/contracts/generate_service.py (backlog в STATUS.md).

Осознанные отличия от страницы:
- data["ТЕКУЩИЙ_ГОД"] пинуется годом contract_date (страница полагается на
  setdefault(now().year) в fill_spec_v2) — иначе дампы недетерминированы
  при годовом rollover'е.
- fallback fill_spec_with_items при падении fill_spec_v2 НЕ реплицируется:
  исключение должно уронить тест, а не деградировать выход.

CLI: python -m tests.autoverify.runner <fixture_id> [-o <dir>]
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.contracts.clauses_context import build_clauses_context
from src.contracts.clauses_renderer import RenderedClause, build_contract_clauses
from src.contracts.compose import compose_spec_with_attachments, compose_supply
from src.contracts.filler import fill_template
from src.contracts.from_kp import (
    build_specification_from_kp_snapshot,
    build_specification_items,
)
from src.contracts.payment_line import build_lines_from_snapshot, format_payment_line
from src.contracts.spec_v2_filler import fill_spec_v2
from src.contracts.supply_filler import build_supply_context, decide_contract_type
from src.contracts.utils import format_date_parts
from src.data_loader import load_models, load_payment_terms, load_prices
from src.generators.kp_generator import generate_kp
from src.storage.snapshot_builder import build_kp_snapshot
from src.ui.payment_lines_editor import (
    _line_to_row,
    _normalize_rows,
    _recompute_amounts,
    _row_to_line,
)
from tests.autoverify.fixtures import Fixture, load_fixture

CONTRACT_TEMPLATE = Path("templates/contracts/contract.docx")
SPEC_V2_TEMPLATE = Path("templates/contracts/spec_v2.docx")

# Дефолты флагов — зеркало init_contract_state() (src/contracts/state.py)
_FLAG_DEFAULTS: dict[str, Any] = {
    "winter_concrete": False,
    "winter_surcharge": False,
    "winter_surcharge_amount": 200000,
}


@dataclass(frozen=True)
class GeneratedSet:
    """Результат прогона: пути DOCX + промежуточные структуры для проверок."""
    fixture_id: str
    flow: str                                   # фактический тип: spec | supply
    docx_paths: dict[str, Path]                 # kp / contract / spec | kp / supply
    data: dict[str, Any]                        # плоский dict плейсхолдеров
    items: list[dict[str, Any]]                 # SpecItem list (per-unit)
    deal: dict[str, Any]
    payment_rows: list[dict[str, Any]]          # строки редактора оплаты
    spec_total: int                             # подытог_за_1 × model_qty
    model_qty: int
    clauses: dict[str, list[RenderedClause]]    # section_id → клаузы


def _build_payment_rows(
    fixture: Fixture, snapshot: dict, items: list[dict], model_qty: int,
) -> tuple[list[dict], int]:
    """Строки оплаты: явные из фикстуры или сидинг из снапшота.

    Зеркало render_payment_lines_editor: «Заполнить по умолчанию» +
    нормализация/пересчёт сумм, как делает редактор на каждом rerun.
    """
    spec_total = sum(int(it.get("total") or 0) for it in items) * model_qty
    if fixture.payment_rows is not None:
        raw_rows = fixture.payment_rows
    else:
        lines = build_lines_from_snapshot(
            snapshot.get("payment") or {}, items, model_qty
        )
        raw_rows = [_line_to_row(line) for line in lines]
    rows = _recompute_amounts(_normalize_rows(raw_rows), spec_total)
    return rows, spec_total


def generate_all(fixture: Fixture, out_dir: Path) -> GeneratedSet:
    """Полный headless-прогон фикстуры: КП + договор + спецификация → DOCX."""
    out_dir.mkdir(parents=True, exist_ok=True)
    prices = load_prices()
    models_json = load_models()
    payment_terms = load_payment_terms()

    # --- КП (шов чистый: state → bytes) ---
    kp_path = out_dir / f"{fixture.id}_kp.docx"
    kp_path.write_bytes(generate_kp(fixture.kp_state, prices))

    # --- kp_row из снапшота (зеркало пути «Из базы (по номеру)») ---
    snapshot = build_kp_snapshot(fixture.kp_state)
    kp_row = {
        "kp_number": fixture.kp_state.get("kp_number", ""),
        "client_name": fixture.kp_state.get("client_name", ""),
        "model_id": fixture.kp_state.get("model_id", ""),
        "data": snapshot,
    }
    spec_flat = build_specification_from_kp_snapshot(
        kp_row, prices, models_json, payment_terms
    )
    items = build_specification_items(kp_row, prices)

    # --- data: ЗЕРКАЛО collect_for_template() + глюкода страницы ---
    data: dict[str, Any] = {**fixture.requisites}
    data.update({k: v for k, v in spec_flat.items() if k != "items"})
    data.update(format_date_parts(str(fixture.contract_date)))
    data["ДОГОВОР_НОМЕР"] = fixture.contract_number
    data["СПЕЦ_АДРЕС_ОБЪЕКТА"] = fixture.object_address
    data["СПЕЦ_НОМЕР"] = fixture.spec_number
    pol = data.get("ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ", "male")
    data["ДИРЕКТОР_ПРИЧАСТИЕ"] = "действующей" if pol == "female" else "действующего"
    nds = data.get("СПЕЦ_НДС", "")
    if not nds or "20" in nds:
        data["СПЕЦ_НДС"] = nds.replace("20", "22") if nds else "22"
    data["ТЕКУЩИЙ_ГОД"] = str(fixture.contract_date.year)  # пин детерминизма

    # --- deal + model_qty (зеркало _gen_deal / get_model_qty) ---
    model_qty = int((snapshot.get("model") or {}).get("qty") or 1)
    deal: dict[str, Any] = {
        "items": items,
        "scope_overrides": fixture.scope_overrides,
        "flags": {**_FLAG_DEFAULTS, **fixture.flags},
        "delivery_address": fixture.object_address,
    }
    prows, spec_total = _build_payment_rows(fixture, snapshot, items, model_qty)

    # --- Тип документа (зеркало авто-выбора страницы) ---
    ctx_now = build_clauses_context(deal)
    actual_flow = decide_contract_type(
        ctx_now.get("installation_scope", "none"),
        ctx_now.get("foundation_scope", "none"),
        bool(ctx_now.get("has_orion", False)),
    )
    if actual_flow != fixture.flow:
        raise AssertionError(
            f"{fixture.id}: decide_contract_type={actual_flow!r}, "
            f"фикстура ожидает {fixture.flow!r}"
        )

    docx_paths: dict[str, Path] = {"kp": kp_path}
    manual = {
        "contract_number": fixture.contract_number,
        "object_address": fixture.object_address,
        "spec_number": fixture.spec_number,
        "valid_until": fixture.valid_until,
    }

    if actual_flow == "supply":
        # --- Supply-флоу: три docxtpl-шаблона → один DOCX ---
        supply_path = out_dir / f"{fixture.id}_dogovor_postavki.docx"
        supply_ctx = build_supply_context(
            data, items, deal, prows, manual, fixture.contract_date,
            model_qty=model_qty,
        )
        compose_supply(supply_ctx, supply_path)
        docx_paths["supply"] = supply_path
    else:
        # --- Spec-флоу: Договор + Спецификация ---
        contract_path = out_dir / f"{fixture.id}_dogovor.docx"
        spec_path = out_dir / f"{fixture.id}_spec.docx"
        fill_template(str(CONTRACT_TEMPLATE), data, str(contract_path))
        if prows:
            data["_payment_lines"] = [
                format_payment_line(_row_to_line(row), f"2.{i + 1}")
                for i, row in enumerate(prows)
            ]
        fill_spec_v2(
            str(SPEC_V2_TEMPLATE), data, items, deal, str(spec_path),
            model_qty=model_qty,
        )
        # Фикстуры без фундаментных приложений: attachments={} — no-op склейка
        compose_spec_with_attachments(spec_path, {}, data)
        docx_paths["contract"] = contract_path
        docx_paths["spec"] = spec_path

    return GeneratedSet(
        fixture_id=fixture.id,
        flow=actual_flow,
        docx_paths=docx_paths,
        data=data,
        items=items,
        deal=deal,
        payment_rows=prows,
        spec_total=spec_total,
        model_qty=model_qty,
        clauses=build_contract_clauses(deal),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Headless-прогон фикстуры autoverify")
    parser.add_argument("fixture_id")
    parser.add_argument(
        "-o", "--out", type=Path, default=Path("tests/output/autoverify"),
    )
    args = parser.parse_args(argv)
    result = generate_all(load_fixture(args.fixture_id), args.out)
    for kind, path in result.docx_paths.items():
        print(f"{kind}: {path}")


if __name__ == "__main__":
    main()

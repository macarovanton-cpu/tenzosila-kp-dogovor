"""Разведочный скрипт: полная матрица условий оплаты движка (без фиксов).

Прогоняет tests/autoverify/runner.generate_all() (продакшн-путь генерации
КП/Договора/Спецификации) на 5 пресетах оплаты (фиксированный состав сделки)
+ 5 доп. композициях для split_by_items, и печатает дословный текст условий
оплаты в docs/PAYMENT_MATRIX.md — для ручной вычитки, не для авто-сверки.

CLI: python -m tools.payment_matrix
"""
from __future__ import annotations

import tempfile
from dataclasses import replace
from datetime import date
from pathlib import Path

from src.contracts.spec_v2_filler import _payment_lines_from_data
from src.data_loader import load_payment_terms
from tests.autoverify.fixtures import Fixture, load_fixture
from tests.autoverify.runner import generate_all
from tests.autoverify.test_group_w_payment_wording import _full_lines, _kp_lines

OUT_MD = Path("docs/PAYMENT_MATRIX.md")

_BASE_COMPOSITION = "весы + фундамент + монтаж + поверка + доставка"

_OPTION = lambda price: {  # noqa: E731
    "enabled": True, "price": price, "qty": 1,
    "customer_side": False, "retail": price, "dealer_is_synthetic": False,
}

# (id-суффикс, состав, flow, options, доп. пресеты дней)
_EXTRA_COMPOSITIONS = [
    ("bare_scales", "весы (без опций)", "supply", {}),
    ("install_only", "весы + монтаж (без фундамента)", "spec",
     {"install_default": _OPTION(180000)}),
    ("rama_ramps", "весы + рама + пандусы (без монтажа)", "supply",
     {"frame_18": _OPTION(130000), "ramp_set_fl_sl": _OPTION(280000)}),
    # Форма 9 PAYMENT_SPEC: монтаж весов есть → шеф-монтаж ОРИОНа растворяется
    # в «монтажных работах» (поглощение B11).
    ("orion_poles", "весы + ПАК ОРИОН + опоры + монтаж + поверка", "spec",
     {"orion_standard": _OPTION(464900), "orion_cable_poles": _OPTION(155000),
      "install_default": _OPTION(180000), "verification_default": _OPTION(60000)}),
    # Форма 11 PAYMENT_SPEC: бандл ОРИОН расщепляется на ПАК + orion_install;
    # монтажа весов нет → поглощение B11 не срабатывает, ОРИОН назван прямо.
    ("orion_shef_only", "весы + шеф-монтаж ПАК ОРИОН (без монтажа весов)", "spec",
     {"orion_standard": _OPTION(464900)}),
]


def _build_scenarios() -> list[tuple[str, str, int, Fixture]]:
    """(заголовок, состав, days, Fixture) для всех 10 сценариев."""
    base = load_fixture("fundament_montazh_poverka")
    preset_names = {p["id"]: p["name"] for p in load_payment_terms()["presets"]}
    scenarios: list[tuple[str, str, int, Fixture]] = []

    for preset_id in (
        "split_by_items", "prepay_100", "v1_prepay_postpay",
        "v2_prepay_preship_postpay", "v3_postpay_only",
    ):
        # payment_v3_days — отдельное поле для v3 (см. render_v3), тоже пинуем на 5
        kp_state = {**base.kp_state, "payment_preset_id": preset_id, "payment_v3_days": 5}
        label = f"{preset_id} ({preset_names[preset_id]})"
        scenarios.append((label, _BASE_COMPOSITION, 5,
                           replace(base, id=f"base__{preset_id}", kp_state=kp_state)))

    for suffix, composition, flow, options in _EXTRA_COMPOSITIONS:
        kp_state = {**base.kp_state, "payment_preset_id": "split_by_items", "options": options}
        extra = {"valid_until": date(2026, 7, 15)} if flow == "supply" else {}
        fixture = replace(base, id=f"extra__{suffix}", flow=flow, kp_state=kp_state, **extra)
        scenarios.append((f"split_by_items — {composition}", composition, 5, fixture))

    return scenarios


def _render_scenario(label: str, composition: str, days: int, fixture: Fixture, out_dir: Path) -> str:
    lines = [f"### Форма: {label}", f"Состав: {composition}"]
    try:
        g = generate_all(fixture, out_dir)
    except Exception as e:  # noqa: BLE001 — разведка: сбой формы фиксируем в отчёте, не роняем прогон
        lines.append(f"\n**форма не собралась:** {e}\n")
        return "\n".join(lines)

    lines.append(f"Days: {days}")
    lines.append(f"Flow: {g.flow}\n")
    lines.append("**КП:**\n" + "\n".join(_kp_lines(g)) + "\n")

    if g.flow == "supply":
        lines.append("**Договор поставки (единственный документ для этой формы):**\n"
                      + "\n".join(_full_lines(g)) + "\n")
        lines.append("*(авто-путь/Спецификация неприменимы — в договоре поставки нет "
                      "маркера {{PAYMENT_SECTION}} и Спецификации как документа.)*")
    else:
        lines.append("**Спецификация (через редактор, full):**\n"
                      + "\n".join(_full_lines(g)) + "\n")
        lines.append("**Спецификация (авто-путь, без редактора оплаты — баг A5, docs/TECH_DEBT.md):**\n"
                      + "\n".join(_payment_lines_from_data(g.data)))

    return "\n".join(lines)


def main() -> None:
    out_dir = Path(tempfile.mkdtemp(prefix="payment_matrix_"))
    scenarios = _build_scenarios()
    blocks = [_render_scenario(label, composition, days, fixture, out_dir)
              for label, composition, days, fixture in scenarios]
    text = "# Матрица условий оплаты (дословный вывод движка)\n\n" + "\n\n---\n\n".join(blocks) + "\n"
    OUT_MD.write_text(text, encoding="utf-8")

    # ponytail: минимальная самопроверка нетривиального цикла/ветвления
    assert OUT_MD.exists()
    assert text.count("### Форма:") == 10, text.count("### Форма:")
    assert "Договор поставки" in text and "Спецификация (через редактор" in text
    print(f"OK: {OUT_MD} ({len(scenarios)} форм)")


if __name__ == "__main__":
    main()

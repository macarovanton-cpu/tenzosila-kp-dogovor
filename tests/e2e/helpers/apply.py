"""Унифицированный применятель сценария к UI."""
from __future__ import annotations

from pathlib import Path

from tests.e2e.pages.kp_page import KpPage, save_download
from tests.e2e.scenarios import Scenario


def apply_scenario(kp: KpPage, scenario: Scenario) -> None:
    kp.set_kp_number(scenario.kp_number)
    kp.set_client_name(scenario.client_name)

    kp.select_line(scenario.model_line)
    kp.set_max_load(scenario.model_max)
    kp.set_length(scenario.model_length)

    if scenario.dual_range:
        kp.toggle_dual_range(True)

    for opt in scenario.options:
        kp.toggle_option(opt.block_label, opt.option_label, on=True)

    if scenario.verification_doer:
        # Применяем только если опция «Первичная поверка» включена в сценарии.
        verification_enabled = any(
            "Первичная поверка" in o.option_label for o in scenario.options
        )
        if verification_enabled:
            kp.set_verification_doer(scenario.verification_doer)

    kp.open_payment_panel()
    kp.select_payment_preset(scenario.payment_preset_label)
    if scenario.payment_custom_text:
        kp.set_payment_custom_text(scenario.payment_custom_text)


def generate_and_save(
    kp: KpPage, scenario: Scenario, output_dir: Path
) -> Path:
    download = kp.generate()
    target = output_dir / f"{scenario.slug}.docx"
    return save_download(download, target)


__all__ = ["apply_scenario", "generate_and_save"]

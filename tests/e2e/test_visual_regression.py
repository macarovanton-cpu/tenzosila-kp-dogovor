"""Visual regression: рендерим DOCX в PNG и сравниваем с baseline.

Запуск:
- `pytest -m "e2e and visual" tests/e2e` — обычная проверка
- `pytest -m e2e tests/e2e --update-baseline` — пересоздать baseline

Зависит от soffice + poppler. Если их нет — тест помечается xfail
(не блокирует e2e-content).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.e2e.helpers.apply import apply_scenario, generate_and_save
from tests.e2e.helpers.docx_to_png import PopplerMissing, docx_to_png
from tests.e2e.helpers.visual_diff import diff_images
from tests.e2e.scenarios.gipsobeton import GIPSOBETON
from tests.e2e.scenarios.kirova import (
    KIROVA_WITH_VERIFICATION,
    KIROVA_WITHOUT_VERIFICATION,
)
from tests.e2e.scenarios.stress_max import STRESS_MAX

OUTPUT = Path(__file__).resolve().parent.parent / "output" / "visual"
BASELINE_PNG = Path(__file__).resolve().parent.parent / "baseline" / "png"


SCENARIOS = [
    pytest.param(GIPSOBETON, id=GIPSOBETON.slug),
    pytest.param(KIROVA_WITH_VERIFICATION, id=KIROVA_WITH_VERIFICATION.slug),
    pytest.param(KIROVA_WITHOUT_VERIFICATION, id=KIROVA_WITHOUT_VERIFICATION.slug),
    pytest.param(STRESS_MAX, id=STRESS_MAX.slug),
]


@pytest.mark.visual
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_visual_regression(kp_page, update_baseline, scenario):
    apply_scenario(kp_page, scenario)
    docx = generate_and_save(kp_page, scenario, OUTPUT)

    target_dir = OUTPUT / scenario.slug
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        actual_pngs = docx_to_png(docx, target_dir, dpi=150)
    except FileNotFoundError as e:
        pytest.xfail(f"soffice не найден: {e}")
    except PopplerMissing as e:
        pytest.xfail(str(e))

    baseline_dir = BASELINE_PNG / scenario.slug
    baseline_dir.mkdir(parents=True, exist_ok=True)

    if update_baseline:
        for actual in actual_pngs:
            shutil.copy2(actual, baseline_dir / actual.name)
        pytest.skip(
            f"Baseline обновлён: {len(actual_pngs)} страниц → {baseline_dir}"
        )

    failures: list[str] = []
    for actual in actual_pngs:
        baseline = baseline_dir / actual.name
        if not baseline.exists():
            failures.append(
                f"Нет baseline для {actual.name}. "
                f"Запусти `pytest -m e2e --update-baseline` для генерации."
            )
            continue
        result = diff_images(actual, baseline, threshold_pct=5.0)
        if not result.match:
            failures.append(
                f"{actual.name}: diff {result.diff_pct:.3f}% > 5.0% "
                f"({result.reason or 'pixel diff'}); "
                f"diff-image: {result.diff_image_path}"
            )

    assert not failures, "Visual diff:\n" + "\n".join(failures)

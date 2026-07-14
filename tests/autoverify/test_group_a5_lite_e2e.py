"""B9 остаток 2/2: страж A5 через РЕАЛЬНЫЙ пайплайн (generate_all), не юнит.

`tests/contracts/test_spec_v2_payment_guard.py` уже проверяет
`_assert_full_payment_lines` изолированно, на ЗАРУЧНУЮ написанных lite-строках.
Но ни одна фикстура autoverify/golden не прогоняла lite-путь через реальный
`generate_all` — там `payment_rows` всегда непустые, и `data["_payment_lines"]`
(override) ставится раньше, чем страж успевает увидеть fallback
`СПЕЦ_ОПЛАТА_П1..6` (реальный вывод `render_payment_block`, не ручной текст).

Не golden: `freeze.py`/`test_golden.py` сравнивают дамп DOCX, а здесь генерация
обязана УПАСТЬ (PaymentLinesLiteError) — сравнивать нечего. Не JSON-фикстура в
`tests/autoverify/fixtures/`: тот каталог параметризует общую session-фикстуру
`generated` (conftest.py) для ВСЕХ тестов autoverify — паденье `generate_all`
там уронило бы фикстуру для каждого теста, использующего `generated`. Поэтому
здесь — самостоятельный тест: берёт существующую spec-фикстуру, обнуляет
`payment_rows` и гоняет `generate_all` напрямую.
"""
from __future__ import annotations

import dataclasses

import pytest

from src.contracts.spec_v2_filler import PaymentLinesLiteError
from tests.autoverify.fixtures import load_fixture
from tests.autoverify.runner import generate_all


def test_a5_lite_payment_lines_blocked_via_real_pipeline(tmp_path) -> None:
    """payment_rows=[] (менеджер не заполнил оплату) → страж рушит генерацию.

    `_build_payment_rows` не сеет строки из снапшота, если `payment_rows`
    явно задан (даже пустым списком) — как в проде: after import, до нажатия
    «Заполнить по умолчанию». `data["_payment_lines"]` не ставится
    (`if prows: ...` в runner.py), fallback читает КП-lite слоты
    `СПЕЦ_ОПЛАТА_П1..6`, которые `build_specification_from_kp_snapshot` уже
    заполнил через `render_payment_block` (тире-строки, без «2.N.») — страж
    обязан их поймать.
    """
    fixture = dataclasses.replace(
        load_fixture("fundament_montazh_poverka"), payment_rows=[],
    )
    with pytest.raises(PaymentLinesLiteError):
        generate_all(fixture, tmp_path)

from pathlib import Path

import pytest

FIXTURE_DEALER = Path(__file__).parent / "fixtures" / "2026_03_01_Прайс_дилер_экспорт.pdf"
FIXTURE_RETAIL = Path(__file__).parent / "fixtures" / "2026_03_01_Прайс_розница_Tenzosila.pdf"


@pytest.mark.skip(
    reason=(
        "Задача 4: сборка + дедуп — объединение дилерского и розничного прайсов "
        "в единый prices.json без дублей"
    )
)
def test_price_merge_and_dedup():
    pass

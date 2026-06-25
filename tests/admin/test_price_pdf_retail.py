from pathlib import Path

import pytest

FIXTURE_RETAIL = Path(__file__).parent / "fixtures" / "2026_03_01_Прайс_розница_Tenzosila.pdf"


@pytest.mark.skip(
    reason=(
        "Задача 3: парсер розничного PDF — услуги/навесы/ОРИОН"
    )
)
def test_retail_pdf_parsed():
    pass

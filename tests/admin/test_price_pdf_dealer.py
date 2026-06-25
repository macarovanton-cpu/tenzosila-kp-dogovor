from pathlib import Path

import pytest

FIXTURE_DEALER = Path(__file__).parent / "fixtures" / "2026_03_01_Прайс_дилер_экспорт.pdf"


@pytest.mark.skip(
    reason=(
        "Задача 2: парсер дилерского PDF — сверка цен и точное совпадение "
        "model_id с prices.json"
    )
)
def test_dealer_pdf_parsed():
    pass

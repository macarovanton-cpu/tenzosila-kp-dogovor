"""Константы конфигуратора КП ВЕСТА."""
from __future__ import annotations

from pathlib import Path

# Пути к справочникам
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
MODELS_JSON: Path = DATA_DIR / "models.json"
PRICES_JSON: Path = DATA_DIR / "prices.json"
PAYMENT_TERMS_JSON: Path = DATA_DIR / "payment_terms.json"
OPTIONS_META_JSON: Path = DATA_DIR / "options.json"

# НДС — в прайсе цены уже с НДС 22%
VAT_RATE: float = 0.22

# Сроки по умолчанию
DEFAULT_TOTAL_TERM_DAYS: int = 35
DEFAULT_KP_VALID_DAYS: int = 15

# Коридоры цен
SYNTHETIC_DEALER_FACTOR: float = 0.92  # для UNKNOWN-опций 22м
MAX_COEFF: float = 1.4                 # верхняя граница слайдера (× retail)
MIN_COEFF_B: float = 0.6               # нижняя граница для класса B

# Шаги слайдера
SLIDER_STEP_LARGE: int = 10_000        # retail > 1 000 000
SLIDER_STEP_SMALL: int = 5_000
SLIDER_THRESHOLD: int = 1_000_000

# Линейки и длины в scope MVP
LINES: list[str] = ["С", "СЛ", "Ф", "ФЛ", "П"]
LENGTHS: list[int] = [18, 20, 22, 24]

# Порядок блоков опций в UI (13 штук)
OPTION_BLOCKS_ORDER: list[str] = [
    "ramps",
    "frames",
    "fences",
    "hatches",
    "foundations",
    "construction_works",
    "concrete_on_frame",
    "canopy",
    "pak_orion",
    "misc",
    "install",
    "delivery",
    "verification",
]

# Видимые названия блоков
BLOCK_LABELS: dict[str, str] = {
    "ramps": "Пандусы",
    "frames": "Рама",
    "fences": "Ограждение",
    "hatches": "Люки",
    "foundations": "Фундамент",
    "construction_works": "Стройработы",
    "concrete_on_frame": "Бетонное основание",
    "canopy": "Навес под ключ",
    "pak_orion": "ПАК ОРИОН",
    "misc": "Мелочи (закладные, резина, калибровка)",
    "install": "Монтаж",
    "delivery": "Доставка",
    "verification": "Поверка",
}

# Префиксы ключей опций по блокам
BLOCK_KEY_PREFIXES: dict[str, tuple[str, ...]] = {
    "ramps": ("ramp_set_",),
    "frames": ("frame_",),
    "fences": ("fence_",),
    "hatches": ("hatches_",),
    "foundations": (
        "foundation_lite_",
        "foundation_std_",
        "foundation_s_f_",
        "foundation_supervision",
    ),
    "construction_works": ("construction_works_",),
    "concrete_on_frame": ("concrete_base_on_frame",),
    "canopy": ("canopy_turnkey_",),
    "pak_orion": (
        "orion_lite",
        "orion_standard",
        "orion_standard_plus",
        "orion_auto",
        "orion_auto_plus",
        "orion_cable_poles",
    ),
    "misc": ("embedded_parts", "rubber_t_6m", "factory_calibration"),
    "install": ("install_default",),
    "delivery": ("delivery_default",),
    "verification": ("verification_default",),
}

# Опции, у которых показывается поле "Количество"
QTY_ENABLED_BLOCKS: set[str] = {"ramps", "foundations"}

# Единицы измерения по блокам
UNIT_BY_BLOCK: dict[str, str] = {
    "ramps": "компл",
    "foundations": "компл",
}

# Ориентировочные сроки исполнения (дни) по блокам — для spec_items
TERM_DAYS_BY_BLOCK: dict[str, int] = {
    "ramps": 35,
    "frames": 35,
    "fences": 35,
    "hatches": 35,
    "foundations": 30,
    "construction_works": 30,
    "concrete_on_frame": 30,
    "canopy": 45,
    "pak_orion": 35,
    "misc": 35,
    "install": 10,
    "delivery": 7,
    "verification": 5,
}

DEFAULT_MODEL_TERM_DAYS: int = 35  # срок производства весов

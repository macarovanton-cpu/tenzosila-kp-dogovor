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
MANAGERS_JSON: Path = DATA_DIR / "managers.json"

# НДС — в прайсе цены уже с НДС 22%
VAT_RATE: float = 0.22

# Срок действия КП по умолчанию (дни). Срок исполнения проекта рассчитывается
# по составу спецификации — см. spec_builder.calculate_default_term_days.
DEFAULT_KP_VALID_DAYS: int = 15

# Коридоры цен
SYNTHETIC_DEALER_FACTOR: float = 0.92  # для UNKNOWN-опций 22м
MAX_COEFF: float = 1.4                 # верхняя граница слайдера (× retail)
MIN_COEFF_B: float = 0.6               # нижняя граница для класса B

# Шаг слайдера — см. pricing.calc_slider_step()

# Линейки и длины в scope MVP
LINES: list[str] = ["С", "СЛ", "Ф", "ФЛ", "П"]
LENGTHS: list[int] = [18, 20, 22, 24]

# Порядок блоков опций в UI и spec-таблице.
# Сначала все «опции весов» (role=None: рамы/ограждения/пандусы/люки/мелочи) —
# чтобы они слились в DOCX с весами по vMerge. Затем — позиции с собственным
# сроком отдельной строкой: ОРИОН, стройработы, навес, фундамент, монтаж,
# доставка, поверка.
OPTION_BLOCKS_ORDER: list[str] = [
    "ramps",
    "frames",
    "fences",
    "hatches",
    "misc",
    "pak_orion",
    "construction_works",
    "concrete_on_frame",
    "canopy",
    "foundations",
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


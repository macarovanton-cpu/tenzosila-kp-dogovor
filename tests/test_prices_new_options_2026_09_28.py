"""Д04: прайс 28.09.2026 — записи новых опций."""
import json
from pathlib import Path

LIVE = json.loads((Path(__file__).parents[1] / "data" / "prices.json").read_text(encoding="utf-8"))

A, B = "A_retail_and_dealer", "B_retail_only"
ALL_LENS = [12, 16, 18, 20, 22, 24]
ALL5 = ["С", "СЛ", "Ф", "ФЛ", "П"]
FS = "ВЕСТА-Ф/С"
NOTE_PRICE = "Прайс 28.09.2026."
NOTE_REQ = "В прайсе 28.09.2026 — по запросу."

# ключ -> (label, линейки, длины, розница, дилерская, discount_pct, класс, по запросу)
NEW: dict[str, tuple] = {}


def _per_len(prefix: str, label: str, lines: list[str], retail: list, dealer: list | None, cls: str) -> None:
    for i, ln in enumerate(ALL_LENS):
        r = retail[i]
        d = dealer[i] if dealer else None
        NEW[f"{prefix}_{ln}"] = (label.format(ln), lines, [ln], r, d, 5 if d else None, cls, r is None)


_per_len("kbu_p06_35_l", "Комплект бесфундаментной установки с опорными плитами П06.35.Л, {}м", ["СЛ", "ФЛ"],
         [290000, 300000, 300000, 310000, 310000, 310000],
         [275500, 285000, 285000, 294500, 294500, 294500], A)
_per_len("kbu_p06_44", "Комплект бесфундаментной установки с опорными плитами П06.44, {}м", ["С", "Ф"],
         [390000, 400000, 400000, 410000, 410000, 410000],
         [370500, 380000, 380000, 389500, 389500, 389500], A)
_per_len("kbu_p08_44", "Комплект бесфундаментной установки с опорными плитами П08.44, {}м", ["С", "Ф"],
         [440000, 450000, 450000, 460000, 460000, 460000],
         [418000, 427500, 427500, 437000, 437000, 437000], A)
NEW["ramp_set_f_s_8mm"] = (f"Комплект пандусов под весы {FS} (L=3,9м), 8мм", ["С", "Ф", "П"], ALL_LENS, 430000, 395600, 8, A, False)
NEW["ramp_set_concrete"] = ("Комплект пандусов бетонных под весы ВЕСТА (L=3,6м)", ALL5, ALL_LENS, 275000, 261250, 5, A, False)
NEW["foundation_heating_gorynych_5"] = ("Подогрев фундамента «Горыныч 5» (оборудование)", ALL5, ALL_LENS, None, None, None, B, True)
NEW["shefmontazh"] = ("Шеф-монтаж и пусконаладка", ["С", "СЛ", "Ф", "ФЛ"], ALL_LENS, 140000, None, None, B, False)
NEW["ppr_documentation"] = ("Разработка ППР и исполнительной документации", ALL5, ALL_LENS, 50000, None, None, B, False)
_REQ = [None, None, None, None, None, None]
_per_len("canopy", "Навес для ВЕСТА, {}м", ALL5, [None, None, 2800000, 3000000, 3200000, None], None, B)
_per_len("foundation_under_canopy", "Фундамент под навес для ВЕСТА, {}м", ALL5, [None, None, 1100000, 1350000, 1480000, None], None, B)
_per_len("canopy_installation", "Монтаж навеса для ВЕСТА, {}м", ALL5, [None, None, 1600000, 1650000, 1700000, None], None, B)
NEW["canopy_lighting"] = ("Освещение под навесом", ALL5, ALL_LENS, None, None, None, B, True)


def test_new_option_values() -> None:
    for key, (label, lines, lens, retail, dealer, disc, cls, req) in NEW.items():
        e = LIVE["options"][key]
        assert e["label"] == label, key
        assert e["applies_to_lines"] == lines, key
        assert e["applies_to_lengths"] == lens, key
        assert (e["price_retail"], e["price_dealer_ru"], e["discount_pct"]) == (retail, dealer, disc), key
        assert e["price_class"] == cls, key
        assert e.get("on_request", False) is req, key
        assert ("on_request" in e) is req, key
        assert e["notes"] == (NOTE_REQ if req else NOTE_PRICE), key

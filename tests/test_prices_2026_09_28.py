"""Д03: прайс 28.09.2026 — значения таблицы и отсутствие лишних изменений."""
import json
from pathlib import Path

LIVE = json.loads((Path(__file__).parents[1] / "data" / "prices.json").read_text(encoding="utf-8"))
OLD = json.loads((Path(__file__).parent / "admin" / "fixtures" / "prices_2026_03_01.json").read_text(encoding="utf-8"))

A, B, C = "A_retail_and_dealer", "B_retail_only", "C_manual_range"
LENS5 = [16, 18, 20, 22, 24]

# (ключ) -> (розница, класс, дилерская или None, range или None)
OPTIONS: dict[str, tuple[int, str, int | None, tuple[int, int] | None]] = {}


def _add(prefix: str, lens: list[int], retail: list[int], cls: str, dealer: list[int] | None = None) -> None:
    for i, ln in enumerate(lens):
        OPTIONS[f"{prefix}_{ln}"] = (retail[i], cls, dealer[i] if dealer else None, None)


OPTIONS["frame_12"] = (110000, B, None, None)
_add("frame", LENS5, [140000, 140000, 170000, 170000, 170000], A, [128800, 128800, 156400, 156400, 156400])
_add("fence_light", LENS5, [115000, 115000, 130000, 130000, 130000], A, [105800, 105800, 119600, 119600, 119600])
_add("fence_norma", LENS5, [148000, 148000, 165000, 165000, 165000], A, [136160, 136160, 151800, 151800, 151800])
_add("hatches_fl", [16, 18, 22], [220000, 220000, 240000], A, [202400, 202400, 220800])
_add("hatches_f", [16, 18, 22], [165000, 165000, 180000], A, [151800, 151800, 165600])
for _n, _c, _rng, _b in [
    ("foundation_lite_sl_fl", 1100000, (800000, 3600000), [1250000, 1250000, 1370000, 1500000, 1500000]),
    ("foundation_std_sl_fl", 1250000, (800000, 3600000), [1400000, 1400000, 1590000, 1680000, 1680000]),
    ("foundation_s_f", 1400000, (900000, 4050000), [1550000, 1550000, 1690000, 1850000, 1850000]),
]:
    OPTIONS[f"{_n}_12"] = (_c, C, None, _rng)
    _add(_n, LENS5, _b, B)
_add("construction_works", [16, 18, 20, 22], [430000, 430000, 460000, 460000], B)
_add("pag_slabs", [12, 16, 18, 20, 22, 24], [730000, 810000, 810000, 875000, 875000, 875000], B)
OPTIONS["foundation_supervision"] = (130000, B, None, None)
OPTIONS["orion_cable_poles"] = (160000, B, None, None)

MODELS = {
    "vesta-фл-60-12": (1131500, 1040980),
    "vesta-сл-60-12": (1260013, 1159212),
    "vesta-ф-60-12": (1290980, 1187702),
    "vesta-ф-60-16": (1682817, 1548192),
    "vesta-с-60-12": (1358581, 1249895),
}


def test_option_values() -> None:
    for key, (retail, cls, dealer, rng) in OPTIONS.items():
        e = LIVE["options"][key]
        assert e["price_retail"] == retail, key
        assert e.get("price_class") == cls, key
        if cls == A:
            assert e["price_dealer_ru"] == dealer and e["discount_pct"] == 8, key
        if rng:
            assert (e["range_min"], e["range_max"]) == rng, key
        else:
            assert "range_min" not in e and "range_max" not in e, key


def test_model_values() -> None:
    for mid, (retail, dealer) in MODELS.items():
        m = LIVE["models"][mid]
        assert (m["retail"], m["dealer_ru"]) == (retail, dealer), mid


def _flat(d: dict) -> dict:
    out = {}
    for sect in ("models", "options"):
        for k, v in d[sect].items():
            for f, x in v.items():
                out[(sect, k, f)] = x
            out[(sect, k, "__keys__")] = tuple(v)
    return out


def test_no_unexpected_changes() -> None:
    """Дифф копия v0.5 -> живой прайс по парам (ключ, поле) = ровно список задачи."""
    old, new = _flat(OLD), _flat(LIVE)
    changed = {p for p in old.keys() | new.keys() if old.get(p, "<нет>") != new.get(p, "<нет>")}
    changed = {p for p in changed if p[2] != "__keys__"}
    expected = set()
    for key, (retail, cls, dealer, rng) in OPTIONS.items():
        expected.add(("options", key, "price_retail"))
        o = OLD["options"][key]
        if o.get("price_class") != cls:
            expected.add(("options", key, "price_class"))
        if cls == A:
            for f, v in (("price_dealer_ru", dealer), ("discount_pct", 8)):
                if o.get(f) != v:
                    expected.add(("options", key, f))
        if not rng:
            expected |= {("options", key, f) for f in ("range_min", "range_max") if f in o}
    for mid in MODELS:
        expected |= {("models", mid, "retail"), ("models", mid, "dealer_ru")}
    expected = {p for p in expected if old.get(p, "<нет>") != new.get(p, "<нет>")}
    assert changed == expected, (changed - expected, expected - changed)
    assert set(LIVE["options"]) == set(OLD["options"]) and set(LIVE["models"]) == set(OLD["models"])
    assert {k for k in OLD if k not in ("models", "options", "_meta")} == {k for k in LIVE if k not in ("models", "options", "_meta")}

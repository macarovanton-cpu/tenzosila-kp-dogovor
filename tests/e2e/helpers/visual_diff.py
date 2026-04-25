"""PNG-diff через Pillow ImageChops с устойчивостью к LibreOffice-антиалиасингу."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops


@dataclass
class DiffResult:
    match: bool
    diff_pct: float
    diff_image_path: Path | None
    reason: str = ""


def diff_images(
    actual: Path,
    baseline: Path,
    *,
    threshold_pct: float = 0.5,
    pixel_intensity_tolerance: int = 8,
    diff_out: Path | None = None,
) -> DiffResult:
    """Сравнить две PNG.

    threshold_pct — процент допустимо различающихся пикселей (0..100).
    pixel_intensity_tolerance — на сколько может отличаться канал, чтобы не
    считаться расхождением (антиалиасинг шрифтов даёт диффы 1–5 единиц).
    """
    a = Image.open(actual).convert("RGB")
    b = Image.open(baseline).convert("RGB")
    if a.size != b.size:
        return DiffResult(
            match=False,
            diff_pct=100.0,
            diff_image_path=None,
            reason=f"Размеры различаются: actual={a.size}, baseline={b.size}",
        )

    diff = ImageChops.difference(a, b)
    bbox = diff.getbbox()
    if not bbox:
        return DiffResult(match=True, diff_pct=0.0, diff_image_path=None)

    bad = 0
    for px in diff.getdata():
        if any(c > pixel_intensity_tolerance for c in px):
            bad += 1
    total = a.width * a.height
    pct = (bad / total) * 100 if total else 0.0
    matched = pct <= threshold_pct
    saved: Path | None = None
    if not matched:
        saved = diff_out or actual.with_name(actual.stem + "_diff.png")
        diff.save(saved)
    return DiffResult(match=matched, diff_pct=pct, diff_image_path=saved)


__all__ = ["DiffResult", "diff_images"]

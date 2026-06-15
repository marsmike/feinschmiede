"""Regression: stacked-bar total labels must not be overlapped by bars.

The chart total labels sit at y=320 with maxheight=24 → bbox y=320..344. The
gold Series D accent band sits at the very top of each bar. Before this was
fixed (2026-05-15) the bars were hand-tuned with sizes that drifted from the
totals they were labelling, so the tallest bar (P5, total 14.1) had its
accent band start at y=340 — overlapping the total label by 4px. From a
distance the "13.4" / "14.1" totals looked clipped.

The fix: bars are now proportional to totals with scale = 480 / max_total,
bottom-anchored at y=835. Tallest bar tops at y=355, giving 11px clearance
below the total-label row.

This test reads the DSL source and asserts the invariant directly so any
future hand-tune drifts back into the danger zone fail loudly.
"""
from __future__ import annotations

import re
from pathlib import Path


LAYOUT = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff" / "layouts" / "stacked-bar.slide.dsl"

# Total labels live at y=320, maxheight=24 → bottom y=344. Bar accent bands
# (top of each bar) must start at this y or later.
TOTAL_LABEL_BOTTOM = 344
SAFE_GAP = 10  # px clearance between label bottom and bar top
BAR_TOP_MIN = TOTAL_LABEL_BOTTOM + SAFE_GAP  # 354

RECT_RE = re.compile(
    r"^\s*rect\s+(?P<x>\d+),(?P<y>\d+)\s+(?P<w>\d+)x(?P<h>\d+)\s+"
    r"fill:(?P<fill>\S+)",
    re.MULTILINE,
)


def _accent_rects() -> list[tuple[int, int]]:
    """Return [(x, y)] of every fill:accent rect in the bar zone."""
    src = LAYOUT.read_text()
    rects: list[tuple[int, int]] = []
    for m in RECT_RE.finditer(src):
        if m["fill"] != "accent":
            continue
        x, y = int(m["x"]), int(m["y"])
        # Bar zone: x in [100, 1500] (5 bars at 140..1260, each 200 wide).
        if 100 <= x <= 1500:
            rects.append((x, y))
    return rects


def test_stacked_bar_has_five_accent_bands():
    """Five bars, five gold accent caps. If a future edit removes one we
    notice."""
    rects = _accent_rects()
    assert len(rects) == 5, f"expected 5 accent rects, got {len(rects)}: {rects}"


def test_stacked_bar_accent_bands_clear_total_labels():
    """Every bar's top edge (accent band) must clear the total-label row
    by at least SAFE_GAP px. Regression for the 'totals 13.4/14.1
    obscured by gold band' bug, 2026-05-15."""
    rects = _accent_rects()
    violations = [
        (x, y) for x, y in rects if y < BAR_TOP_MIN
    ]
    assert not violations, (
        f"bar accent band(s) intrude on the total-label safe zone "
        f"(y < {BAR_TOP_MIN}): {violations}"
    )

"""Regression: risk-matrix markers must have a stroke so they're visible
against same-color severity zone tints.

Before 2026-05-15 the markers had no stroke and `severity_color`-tinted
fills. When a risk's severity matched its cell's severity zone (e.g. a
medium-gold oval sitting on the medium-gold zone background at 18%
opacity) the oval blended into the cell. Visually only 2 of 5 markers
appeared; the other 3 looked like bare numbers.

The fix adds `stroke:paper stroke-width:3` to every marker — a cream
ring that contrasts with every possible severity tint.
"""
from __future__ import annotations

import re
from pathlib import Path


LAYOUT = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff" / "layouts" / "risk-matrix.slide.dsl"

# Match the 60×60 markers (the matrix dots). The legend dots are 32×32 and
# don't have the contrast issue since they sit on the cream paper, not on
# tinted cells.
MARKER_RE = re.compile(
    r"^\s*shape\s+[^\n]*60x60\s+kind:oval([^\n]*)$",
    re.MULTILINE,
)


def _markers() -> list[str]:
    src = LAYOUT.read_text()
    return [m.group(1) for m in MARKER_RE.finditer(src)]


def test_risk_matrix_has_ten_marker_slots():
    markers = _markers()
    assert len(markers) == 10, f"expected 10 marker slots, got {len(markers)}"


def test_risk_matrix_markers_have_visible_stroke():
    """Every marker must carry a stroke — without it markers blend into
    same-color severity zone tints and disappear."""
    markers = _markers()
    missing = [i for i, m in enumerate(markers) if "stroke:" not in m]
    assert not missing, (
        f"markers {missing} lack a stroke — they will disappear into "
        f"matching severity zone tints (was the bug fixed 2026-05-15)"
    )

"""Regression: funnel stages must be visually distinguishable.

Before 2026-05-15 the funnel painted stages 1, 2, 4 all with `fill:ink`
and stage 3 with `fill:accent`. Stage 1 and stage 2 are adjacent and the
identical ink fill made them blend into one tall band — visually you saw
3 stages, not 4. The fix alternates the navy ramp so every adjacent pair
has distinct fills.

This invariant is enforced statically from the DSL.
"""
from __future__ import annotations

import re
from pathlib import Path


LAYOUT = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff" / "layouts" / "funnel.slide.dsl"

SHAPE_RE = re.compile(
    r"^\s*shape\s+(?P<x>\d+),(?P<y>\d+)\s+(?P<w>\d+)x(?P<h>\d+)\s+kind:trapezoid"
    r"(?P<rest>.*)$",
    re.MULTILINE,
)


def _funnel_fills() -> list[str]:
    """Return fill tokens for the 4 funnel trapezoids in y order."""
    src = LAYOUT.read_text()
    bands = []
    for m in SHAPE_RE.finditer(src):
        y = int(m["y"])
        rest = m["rest"]
        fill = next(
            (tok.split(":", 1)[1] for tok in rest.split() if tok.startswith("fill:")),
            None,
        )
        # Funnel bands sit in y range 460..860. Excludes other trapezoids
        # that might be added to the layout in the future.
        if 400 <= y <= 900 and fill is not None:
            bands.append((y, fill))
    bands.sort()
    return [fill for _, fill in bands]


def test_funnel_has_four_bands():
    fills = _funnel_fills()
    assert len(fills) == 4, f"expected 4 funnel bands, got {len(fills)}: {fills}"


def test_funnel_adjacent_bands_have_distinct_fills():
    """No two consecutive bands share a fill, otherwise the boundary
    between them disappears."""
    fills = _funnel_fills()
    collisions = [
        (i, fills[i], fills[i + 1])
        for i in range(len(fills) - 1)
        if fills[i] == fills[i + 1]
    ]
    assert not collisions, (
        f"adjacent funnel bands share a fill — they will visually merge: "
        f"{collisions}"
    )

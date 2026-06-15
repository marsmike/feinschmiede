"""Regression: the three pyramid tiers must form a coherent silhouette.

Before 2026-05-15 the layout used MSO TRAPEZOID with its default adj (~0.25),
which makes the narrow edge 50% of the wide edge. The three tiers were
therefore widths that didn't match across boundaries:

  apex base = 320           middle bottom = 420         base bottom = 620
  middle top = 210 (×)      base top = 310 (×)

…producing visible "steps" between each tier rather than a pyramid silhouette.

The fix sets explicit adj1 values so each tier's narrow edge matches the
neighbour's wide edge: middle top = apex base (320) and base top = middle
bottom (420). This test asserts the invariant directly from the DSL so
any future hand-tune keeps the silhouette flush.
"""
from __future__ import annotations

import re
from pathlib import Path


LAYOUT = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff" / "layouts" / "pyramid.slide.dsl"

SHAPE_RE = re.compile(
    r"^\s*shape\s+(?P<x>\d+),(?P<y>\d+)\s+(?P<w>\d+)x(?P<h>\d+)\s+kind:(?P<kind>\S+)"
    r"(?P<rest>.*)$",
    re.MULTILINE,
)


def _parse_kwargs(rest: str) -> dict[str, str]:
    kw: dict[str, str] = {}
    for token in rest.split():
        if ":" in token:
            k, _, v = token.partition(":")
            kw[k] = v
    return kw


def _shapes() -> list[dict]:
    src = LAYOUT.read_text()
    out = []
    for m in SHAPE_RE.finditer(src):
        kw = _parse_kwargs(m["rest"])
        out.append({
            "x": int(m["x"]), "y": int(m["y"]),
            "w": int(m["w"]), "h": int(m["h"]),
            "kind": m["kind"],
            "adj1": float(kw.get("adj1", 0)) if "adj1" in kw else None,
        })
    return out


def _trapezoid_narrow_width(shape: dict) -> int:
    """Width of the trapezoid's narrow edge given adj1 inset fraction.

    Per OOXML 20.1.10.55, TRAPEZOID's `adj` is the inset of the narrow edge
    from each side as a fraction of `min(w, h)`, NOT width. So:
        inset_per_side = adj1 * min(w, h)
        narrow = w − 2·inset_per_side
    The previous version of this test used `adj * w` which silently passed
    for one tier and would have masked a future regression."""
    assert shape["kind"] == "trapezoid"
    adj = shape["adj1"]
    assert adj is not None, "trapezoid is missing adj1"
    ss = min(shape["w"], shape["h"])
    inset = adj * ss
    return round(shape["w"] - 2 * inset)


def test_pyramid_apex_base_meets_middle_top():
    shapes = _shapes()
    apex = next(s for s in shapes if s["kind"] == "triangle")
    middle = [s for s in shapes if s["kind"] == "trapezoid"][0]
    apex_base_width = apex["w"]
    middle_top_width = _trapezoid_narrow_width(middle)
    # Allow ±1 px slack for adj1 rounding (we store at 0.001 precision).
    assert abs(apex_base_width - middle_top_width) <= 1, (
        f"apex base ({apex_base_width}) ≠ middle top ({middle_top_width}) — "
        f"tiers don't form a pyramid silhouette"
    )


def test_pyramid_middle_bottom_meets_base_top():
    shapes = _shapes()
    trapezoids = [s for s in shapes if s["kind"] == "trapezoid"]
    middle, base = trapezoids[0], trapezoids[1]
    middle_bottom_width = middle["w"]  # wide edge = full width
    base_top_width = _trapezoid_narrow_width(base)
    assert abs(middle_bottom_width - base_top_width) <= 1, (
        f"middle bottom ({middle_bottom_width}) ≠ base top ({base_top_width}) — "
        f"tiers don't form a pyramid silhouette"
    )


def test_pyramid_tiers_stack_vertically():
    """Each tier's top y must match the previous tier's bottom y, otherwise
    you get a vertical gap between tiers."""
    shapes = _shapes()
    apex = next(s for s in shapes if s["kind"] == "triangle")
    trapezoids = [s for s in shapes if s["kind"] == "trapezoid"]
    middle, base = trapezoids[0], trapezoids[1]
    assert apex["y"] + apex["h"] == middle["y"], "apex bottom ≠ middle top"
    assert middle["y"] + middle["h"] == base["y"], "middle bottom ≠ base top"

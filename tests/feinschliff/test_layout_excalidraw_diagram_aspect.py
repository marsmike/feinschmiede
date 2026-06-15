"""Regression: excalidraw-diagram slot aspect must roughly match the
natural aspect of a typical rendered Excalidraw scene.

Before 2026-05-15 the slot was 1720×480 (aspect 3.58:1). The default
fixture (5 boxes in a horizontal chain) renders to a 3440×480 PNG
(aspect 7.17:1). python-pptx's `add_picture(... width=W, height=H)`
stretches images to fill, so the wide PNG was squeezed horizontally
by 50% and the boxes rendered nearly square — losing the
"horizontal flow" intent.

The fix shrinks the slot to 1720×320 (aspect 5.4:1), much closer to
the natural diagram aspect. The freed vertical space is reallocated
to push the "So what:" caption and source up.

This test pins the slot dimensions so a future tall-slot regression
fails immediately rather than silently distorting diagrams.
"""
from __future__ import annotations

import re
from pathlib import Path


LAYOUT = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff" / "layouts" / "excalidraw-diagram.slide.dsl"

EXCAL_SLOT_RE = re.compile(
    r"^\s*excalidraw\s+diagram\s+(?P<x>\d+),(?P<y>\d+)\s+(?P<w>\d+)x(?P<h>\d+)",
    re.MULTILINE,
)


def test_excalidraw_diagram_slot_aspect_is_horizontal():
    src = LAYOUT.read_text()
    m = EXCAL_SLOT_RE.search(src)
    assert m, "could not find excalidraw diagram slot in layout"
    w, h = int(m["w"]), int(m["h"])
    aspect = w / h
    # Natural rendered aspect of typical fixtures is ~5–7:1. Anything below
    # 4:1 squeezes boxes into squares; above 8:1 leaves the diagram too
    # short to be readable.
    assert 4.5 <= aspect <= 8.0, (
        f"excalidraw-diagram slot is {w}×{h} (aspect {aspect:.2f}:1) — "
        f"outside the 4.5–8.0 range that keeps horizontal-flow diagrams "
        f"from being stretched vertically"
    )

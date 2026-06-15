"""Regression: process-flow chevrons must have explicit adj1 wide enough
for their text to fit in the body.

Before 2026-05-15 the chevrons had no `adj1`, so they used the OOXML
default of 50000 (=0.5), which renders a degenerate zero-body chevron
(notch tip meeting point base in the middle). LibreOffice quietly draws
something nicer when adj is unspecified, but PowerPoint honors the
default — so the same PPTX rendered differently in the two viewers.

The fix sets adj1=0.15 explicitly, yielding body width = 252 px (text
maxwidth = 240 fits). This test enforces both invariants statically.
"""
from __future__ import annotations

import re
from pathlib import Path


LAYOUT = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff" / "layouts" / "process-flow.slide.dsl"

CHEVRON_RE = re.compile(
    r"^\s*shape\s+(?P<x>\d+),(?P<y>\d+)\s+(?P<w>\d+)x(?P<h>\d+)\s+kind:chevron"
    r"(?P<rest>.*)$",
    re.MULTILINE,
)
# Overlay text only (sits on chevrons at y in 480..840). Header text
# (tracker / action_title at y<300) is full-width and shouldn't count.
OVERLAY_TEXT_RE = re.compile(
    r"^\s*text\s+(?P<x>\d+),(?P<y>\d+)[^\n]*maxwidth:(?P<mw>\d+)",
    re.MULTILINE,
)


def _chevrons() -> list[dict]:
    src = LAYOUT.read_text()
    out = []
    for m in CHEVRON_RE.finditer(src):
        rest = m["rest"]
        adj1 = None
        for tok in rest.split():
            if tok.startswith("adj1:"):
                adj1 = float(tok.split(":", 1)[1])
        out.append({
            "w": int(m["w"]), "h": int(m["h"]), "adj1": adj1,
        })
    return out


def _chevron_body_width(c: dict) -> int:
    """body_width = w − 2 · adj1 · min(w, h)."""
    ss = min(c["w"], c["h"])
    inset = c["adj1"] * ss
    return round(c["w"] - 2 * inset)


def test_process_flow_has_five_chevrons():
    chevrons = _chevrons()
    assert len(chevrons) == 5, f"expected 5 chevrons, got {len(chevrons)}"


def test_process_flow_chevrons_have_explicit_adj1():
    """Without explicit adj1 the chevron defaults to OOXML adj=0.5 which is
    a degenerate zero-body chevron in PowerPoint (LibreOffice forgives this
    but the two viewers diverge)."""
    chevrons = _chevrons()
    missing = [i for i, c in enumerate(chevrons) if c["adj1"] is None]
    assert not missing, f"chevrons {missing} are missing adj1 — will render inconsistently across viewers"


def test_process_flow_chevron_body_fits_text():
    """The chevron's body width must be at least as wide as the maxwidth
    of any text overlaid on the chevron."""
    chevrons = _chevrons()
    src = LAYOUT.read_text()
    # Overlay text on chevrons sits in y range 480..840.
    text_widths = [
        int(m.group("mw")) for m in OVERLAY_TEXT_RE.finditer(src)
        if 480 <= int(m.group("y")) <= 840
    ]
    max_text = max(text_widths) if text_widths else 0
    body_widths = [_chevron_body_width(c) for c in chevrons]
    min_body = min(body_widths)
    assert min_body >= max_text, (
        f"chevron body width {min_body} < text maxwidth {max_text} — "
        f"text will spill into the notch/point regions"
    )

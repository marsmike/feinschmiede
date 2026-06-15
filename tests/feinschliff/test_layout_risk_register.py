"""Regression: risk-register severity badges must fully contain their
text labels.

Before 2026-05-15 every severity text was placed at the same y as the
row body text (e.g. y=520) with maxheight=24. The colored severity rect
sat at y=510 with h=40, so the rect bottom was y=550 and the text bbox
was 520..544. That sounds fine, but body font is 26 px and PPTX's
default line height is ~1.2x — so the *rendered* text glyphs extended
to ~y=552, two pixels below the rect bottom. From a distance the
"medium" / "high" / "low" labels looked half-clipped on every row.

The fix shifts each severity text up by 4 px and increases maxheight
to 32, fully containing the rendered line within the rect.

This test enforces that for every severity row.
"""
from __future__ import annotations

import re
from pathlib import Path


LAYOUT = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff" / "layouts" / "risk-register.slide.dsl"

# Severity rect: `rect 900,Y 140x40 fill:"..."` — width 140, height 40.
RECT_RE = re.compile(
    r"^\s*rect\s+900,(?P<y>\d+)\s+140x(?P<h>\d+)\s+fill:",
    re.MULTILINE,
)
# Severity text: `text 920,Y style:body color:paper maxwidth:120 maxheight:H ...`
TEXT_RE = re.compile(
    r"^\s*text\s+920,(?P<y>\d+)\s+style:body color:paper\s+maxwidth:120\s+maxheight:(?P<mh>\d+)",
    re.MULTILINE,
)

# Body font height: 26 px font + 6 px line-height padding = ~32 px rendered glyph
# extent for a single line (Noto Sans at 1.2 line-height).
BODY_RENDERED_HEIGHT = 32


def _severity_pairs() -> list[tuple[dict, dict]]:
    src = LAYOUT.read_text()
    rects = [{"y": int(m["y"]), "h": int(m["h"])} for m in RECT_RE.finditer(src)]
    texts = [{"y": int(m["y"]), "mh": int(m["mh"])} for m in TEXT_RE.finditer(src)]
    # Pair them up in source order — both lists should have same length.
    assert len(rects) == len(texts), (
        f"severity rect/text count mismatch: {len(rects)} rects, {len(texts)} texts"
    )
    return list(zip(rects, texts))


def test_risk_register_has_seven_severity_rows():
    """Header + 7 risk rows = 7 severity badges."""
    pairs = _severity_pairs()
    assert len(pairs) >= 4, f"expected ≥4 severity rows, got {len(pairs)}"


def test_risk_register_severity_text_fits_inside_badge():
    """The rendered text line (using ~32 px line height for 26 px body
    font) must fit vertically inside the colored severity rect."""
    pairs = _severity_pairs()
    failures = []
    for i, (rect, txt) in enumerate(pairs):
        rect_top, rect_bottom = rect["y"], rect["y"] + rect["h"]
        # Rendered text extent: text top → top + max(maxheight, BODY_RENDERED_HEIGHT)
        text_top = txt["y"]
        text_bottom = txt["y"] + max(txt["mh"], BODY_RENDERED_HEIGHT)
        if text_top < rect_top or text_bottom > rect_bottom:
            failures.append(
                f"row {i}: text [{text_top}..{text_bottom}] not contained "
                f"in rect [{rect_top}..{rect_bottom}]"
            )
    assert not failures, "severity text overflows badge:\n" + "\n".join(failures)

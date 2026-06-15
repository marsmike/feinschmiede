"""Cross-cutting static checks on every `.slide.dsl` in `layouts/`.

These rules are distilled from the defect pass on 2026-05-15:

- **adj1 on MSO shapes with adjustment handles** — `kind:trapezoid` and
  `kind:chevron` shapes MUST specify an explicit `adj1`. The OOXML
  default for both is 50000 (=0.5), which is a *degenerate* render in
  PowerPoint (zero-body trapezoid / zero-body chevron). LibreOffice
  silently substitutes a more pleasing default — so the same PPTX
  renders differently in the two viewers. Source: D17 (pyramid) and
  D20 (process-flow) regressions, 2026-05-15.

  Other adjustable shapes (`pie`, `arc`, `block-arc`) can drift the
  same way but they're rarer; the rule is opt-in via this list.

Adding new shape kinds with adjustment handles? Append them to
`ADJUSTABLE_KINDS` below.
"""
from __future__ import annotations

import re
from pathlib import Path


LAYOUT_DIR = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff" / "layouts"
ADJUSTABLE_KINDS = {"trapezoid", "chevron"}

# Match: `shape X,Y WxH kind:NAME …` — captures the shape's full line.
SHAPE_LINE_RE = re.compile(r"^\s*shape\s+[^\n]+kind:(?P<kind>\S+)[^\n]*$", re.MULTILINE)


def _find_unadjusted_shapes() -> list[tuple[Path, int, str]]:
    """Return (layout, line_no, shape_kind) tuples for every shape in
    ADJUSTABLE_KINDS that lacks an explicit `adj1:` kwarg."""
    out: list[tuple[Path, int, str]] = []
    for layout in sorted(LAYOUT_DIR.glob("*.slide.dsl")):
        src = layout.read_text()
        for m in SHAPE_LINE_RE.finditer(src):
            kind = m["kind"]
            if kind not in ADJUSTABLE_KINDS:
                continue
            line = m.group(0)
            if "adj1:" not in line:
                line_no = src[:m.start()].count("\n") + 1
                out.append((layout, line_no, kind))
    return out


def test_every_adjustable_shape_has_explicit_adj1():
    """Static guarantee: no layout ships a `kind:trapezoid` or
    `kind:chevron` without an explicit `adj1:`."""
    violations = _find_unadjusted_shapes()
    msgs = [
        f"  {layout.name}:{line_no} — kind:{kind} without adj1"
        for layout, line_no, kind in violations
    ]
    assert not violations, (
        f"{len(violations)} shape(s) lack explicit adj1 — will render "
        f"inconsistently across LibreOffice / PowerPoint / Keynote:\n"
        + "\n".join(msgs)
    )

"""Regression: v-model must show the V silhouette, not two parallel columns.

Before 2026-05-15 the v-model placed every left-pair at the same x and
every right-pair at the same x, with horizontal hairlines between rows.
Visually you saw three flat columns ("VERIFICATION PHASE / connectors /
VALIDATION PHASE") and no V at all — Mike flagged this as a regression
("we already solved that").

The fix stair-steps each successive pair inward toward the central pivot
so the left-x increases monotonically and the right-x decreases
monotonically across the 4 rows, tracing the V. Two thin diagonal lines
reinforce the silhouette and converge at the pivot.

This test enforces the structure statically from the DSL.
"""
from __future__ import annotations

import re
from pathlib import Path


LAYOUT = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff" / "layouts" / "v-model.slide.dsl"

H_HD_RE = re.compile(
    r"^\s*text\s+(?P<x>\d+),(?P<y>\d+)\s+style:h-hd[^\n]*"
    r"maxwidth:(?P<mw>\d+)[^\n]*?(?P<align>align:right)?[^\n]*"
    r'"\{\{\s*pairs\[(?P<i>\d+)\]\.(?P<side>left|right)_title\s*\}\}"',
    re.MULTILINE,
)
LINE_RE = re.compile(
    r"^\s*line\s+(?P<x1>\d+),(?P<y1>\d+)\s+(?P<x2>\d+),(?P<y2>\d+)",
    re.MULTILINE,
)


def _pair_titles() -> list[dict]:
    """Return one record per pair: {i, left_x, right_edge}."""
    src = LAYOUT.read_text()
    by_index: dict[int, dict] = {}
    for m in H_HD_RE.finditer(src):
        i = int(m["i"])
        x = int(m["x"])
        mw = int(m["mw"])
        side = m["side"]
        rec = by_index.setdefault(i, {"i": i})
        if side == "left":
            rec["left_x"] = x
        else:  # right
            rec["right_edge"] = x + mw  # align:right → text touches x + maxwidth
    return [by_index[i] for i in sorted(by_index)]


def _diagonal_lines() -> list[tuple[int, int, int, int]]:
    src = LAYOUT.read_text()
    return [
        (int(m["x1"]), int(m["y1"]), int(m["x2"]), int(m["y2"]))
        for m in LINE_RE.finditer(src)
    ]


def test_v_model_has_four_pairs():
    pairs = _pair_titles()
    assert len(pairs) == 4, f"expected 4 pairs, got {len(pairs)}: {pairs}"


def test_v_model_left_phases_stairstep_inward():
    """Each successive verification phase must indent further right —
    otherwise the left side of the V is just a vertical column."""
    pairs = _pair_titles()
    left_xs = [p["left_x"] for p in pairs]
    for i in range(1, len(left_xs)):
        assert left_xs[i] > left_xs[i - 1], (
            f"pair {i} left_x {left_xs[i]} ≤ pair {i-1} left_x {left_xs[i-1]} — "
            f"left phases are not stair-stepping toward the pivot"
        )


def test_v_model_right_tests_stairstep_inward():
    """Each successive validation test must end further left."""
    pairs = _pair_titles()
    right_edges = [p["right_edge"] for p in pairs]
    for i in range(1, len(right_edges)):
        assert right_edges[i] < right_edges[i - 1], (
            f"pair {i} right_edge {right_edges[i]} ≥ pair {i-1} "
            f"right_edge {right_edges[i-1]} — right tests are not "
            f"stair-stepping toward the pivot"
        )


def test_v_model_has_two_diagonal_lines_converging():
    """Two diagonals tracing the V — left descends rightward, right
    descends leftward, meeting near the pivot."""
    lines = _diagonal_lines()
    assert len(lines) >= 2, f"expected ≥2 diagonal lines, got {len(lines)}"
    # Find the left-descending one (x1 < x2) and right-descending (x1 > x2).
    left_down = [ln for ln in lines if ln[0] < ln[2] and ln[1] < ln[3]]
    right_down = [ln for ln in lines if ln[0] > ln[2] and ln[1] < ln[3]]
    assert left_down, "no left-side diagonal descending right"
    assert right_down, "no right-side diagonal descending left"
    # Their bottom ends should converge near the slide center (x ≈ 960).
    left_bottom_x = left_down[0][2]
    right_bottom_x = right_down[0][2]
    gap = abs(left_bottom_x - right_bottom_x)
    assert gap < 200, (
        f"V diagonals don't converge — bottom gap {gap} px is too wide "
        f"(left ends at x={left_bottom_x}, right at x={right_bottom_x})"
    )

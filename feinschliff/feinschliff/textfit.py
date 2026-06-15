"""textfit — compatibility shim.

The original ``feinschliff.textfit`` module (pure-Python text fitting
helpers) has been folded into ``feinschliff.slot_budget`` and delegates
measurement to ``feinschmiede.text.measure``. This shim re-exports the
public API so that callers that import from ``feinschliff.textfit`` keep
working without changes.

Deprecated: new code should import directly from ``feinschliff.slot_budget``
or ``feinschmiede.text.measure``.
"""
from __future__ import annotations

import math

from feinschliff.slot_budget import (
    chars_per_line,
)
from feinschmiede.geometry.units import EMU_PER_PT


# ── core fitting helpers ──────────────────────────────────────────────────────

def measure_height_emu(
    text: str,
    *,
    font: str,
    size_pt: float,
    bold: bool = False,
    width_emu: int,
    line_height: float = 1.2,
) -> int:
    """Estimate the height (EMU) that *text* occupies in a box of *width_emu*.

    Uses the char-ratio model from ``feinschliff.slot_budget.chars_per_line``
    to compute wrapped-line count, then converts to EMU.
    """
    if not text or size_pt <= 0 or width_emu <= 0:
        return 0

    cpl = chars_per_line(font, size_pt, bold, width_emu)
    if cpl <= 0:
        return 0

    # Wrap text into lines using the estimated chars-per-line.
    lines = 0
    for paragraph in text.split("\n"):
        if not paragraph:
            lines += 1
            continue
        lines += max(1, math.ceil(len(paragraph) / cpl))

    # Height model: (n-1) inter-line gaps + 1 em box.
    # Mirrors the max_lines property on SlotBudget.
    em_pt = size_pt
    line_h_pt = size_pt * line_height
    height_pt = max(em_pt, (lines - 1) * line_h_pt + em_pt)
    return int(height_pt * EMU_PER_PT)


def fits(
    text: str,
    *,
    font: str,
    size_pt: float,
    bold: bool = False,
    width_emu: int,
    height_emu: int,
    line_height: float = 1.2,
) -> bool:
    """Return True when *text* fits in the given box without overflow."""
    if not text or height_emu <= 0 or width_emu <= 0:
        return True
    measured = measure_height_emu(
        text, font=font, size_pt=size_pt, bold=bold,
        width_emu=width_emu, line_height=line_height,
    )
    return measured <= height_emu


def autoshrink_size(
    text: str,
    *,
    font: str,
    max_size_pt: float,
    min_size_pt: float = 10.0,
    bold: bool = False,
    width_emu: int,
    height_emu: int,
    line_height: float = 1.2,
) -> float:
    """Binary-search for the largest font size ≤ *max_size_pt* at which *text*
    fits, down to *min_size_pt* (the floor).

    Returns the fitted size in pt (may equal *min_size_pt* when even the
    floor overflows — the emitter clips in that case).
    """
    if fits(text, font=font, size_pt=max_size_pt, bold=bold,
            width_emu=width_emu, height_emu=height_emu, line_height=line_height):
        return max_size_pt

    lo, hi = min_size_pt, max_size_pt
    for _ in range(20):  # binary search, converges quickly
        mid = (lo + hi) / 2
        if mid <= min_size_pt:
            return min_size_pt
        if fits(text, font=font, size_pt=mid, bold=bold,
                width_emu=width_emu, height_emu=height_emu, line_height=line_height):
            lo = mid
        else:
            hi = mid
        if hi - lo < 0.1:
            break
    return max(min_size_pt, lo)

"""feinschliff/tests/test_slot_budget_sweep.py

End-to-end honesty pin for the overflow gate: the first content length that
trips `slot-overflow` on a 12in-deck probe slot must sit within ±10% of a
PIL-measured greedy-wrap ground truth (a corporate-pack slide-08 class probe:
920×787px box, size:16pt — true capacity ≈ 800–850 chars with DejaVu Sans;
the pre-fix gate said 1658, and after the size-pt fix but before font-face
parity the gap was 8.6%).

# budget.font_family now resolves to the real DejaVu face (same as the
# emitter's fit paths), so the residual gap vs PIL truth is
# wrap-algorithm rounding only."""
import math

import pytest

from feinschliff.content_validator import validate_content
from feinschliff.dsl.parser import parse_lines
from feinschliff.slot_budget import compute_slot_budgets
from feinschmiede.dsl.tokens import Tokens
from feinschmiede.text import measure

FACE = "DejaVu Sans"
RAW_12IN = {
    "color": {"ink": "#000000", "paper": "#FFFFFF", "graphite": "#444444"},
    "font-family": {"display": [FACE], "body": [FACE]},
    "font-size": {"body": "16px"},
    "font-weight": {"regular": 400},
    "slide": {"width_emu": 10969625, "height_emu": 6170613,
              "width": 1920, "height": 1080},
}
_WORDS = ("revenue growth margin pipeline churn uplift retention onboarding "
          "expansion forecast quarter enterprise customers benchmark velocity").split()


def _probe_text(n_chars: int) -> str:
    words, i = [], 0
    while sum(len(w) for w in words) + max(0, len(words) - 1) < n_chars:
        words.append(_WORDS[i % len(_WORDS)])
        i += 1
    return " ".join(words)[:n_chars].rstrip()


def _pil_ground_truth(box_w_px: float, box_h_px: float, *, size_pt: float,
                      px_per_pt: float, line_height: float = 1.2) -> int:
    """Chars of running text that fit the box: greedy word wrap measured
    with the real font file via PIL — independent of textfit's math."""
    from PIL import ImageFont
    path = measure.find_font_file(FACE)
    assert path is not None
    size_px = size_pt * px_per_pt
    probe = 100.0
    font = ImageFont.truetype(str(path), int(probe))

    def width(s: str) -> float:
        return font.getlength(s) * (size_px / probe)

    max_lines = math.floor(box_h_px / (size_px * line_height))
    placed_lines: list[str] = []
    line = ""
    i = 0
    # All words in _WORDS fit on one line at this box width; no single-word-wider-than-box guard needed.
    while i < 20_000:
        word = _WORDS[i % len(_WORDS)]
        i += 1
        cand = word if not line else f"{line} {word}"
        if width(cand) <= box_w_px:
            line = cand
            continue
        placed_lines.append(line)
        if len(placed_lines) >= max_lines:
            # `line` starts line max_lines+1 — excluded; placed_lines is exactly full.
            return len(" ".join(placed_lines))
        line = word
    raise AssertionError("unreachable")


def test_gate_threshold_within_10pct_of_pil_truth():
    if measure.find_font_file(FACE) is None:
        pytest.skip(f"{FACE} not resolvable on this machine")
    tokens = Tokens.from_dict(dict(RAW_12IN), brand_name="t")
    nodes, _ = parse_lines(
        'canvas 1920x1080\n'
        'text 100,100 "{{ probe }}" style:body size:16pt maxwidth:920 maxheight:787',
        source="<test>",
    )
    budgets = compute_slot_budgets(nodes, tokens)
    px_per_pt = 1.0 / budgets["probe"].px_to_pt          # ≈ 2.2229

    truth = _pil_ground_truth(920, 787, size_pt=16.0, px_per_pt=px_per_pt)
    assert 600 < truth < 1400, f"sanity: implausible ground truth {truth}"

    # Binary-search the first length the gate rejects.
    lo, hi = 50, 4000
    while lo < hi:
        mid = (lo + hi) // 2
        defects = validate_content({"probe": _probe_text(mid)}, slot_budgets=budgets)
        if any(d.kind == "slot-overflow" for d in defects):
            hi = mid
        else:
            lo = mid + 1
    threshold = lo

    # Residual gap is wrap-algorithm rounding (~1%); ±10% is a generous guard.
    assert abs(threshold - truth) <= 0.10 * truth, (
        f"gate first-overflow at {threshold} chars vs PIL truth {truth} "
        f"(>±10% — the budget/emitter font-face or size conversions have drifted)"
    )

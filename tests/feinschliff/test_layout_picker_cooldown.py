"""Variety-penalty cooldown — once a layout wins, it gets a graduated
penalty for the next several positions in `layout_history` so equally-
scored siblings get a chance.

Window: -1 = -3.0, -2 = -2.0, -3 = -1.0, -4 = -0.5. Variety-exempt
layouts (framing moments, profile `variety_exempt: true`) skip the
penalty entirely so the same cover doesn't get demoted.
"""
from __future__ import annotations

from feinschliff.layout_picker import pick_layout

# Three siblings, all content-columns with concept_count fit — equally
# strong on raw affinity score, so variety-penalty is what decides.
_PROFILES = {
    "two-column-cards": {"role": "content-columns", "ideal_count": (2, 3),
                         "data": "none", "comp": False},
    "horizontal-bullets": {"role": "content-columns", "ideal_count": (2, 3),
                           "data": "none", "comp": False},
    "vertical-bullets": {"role": "content-columns", "ideal_count": (2, 3),
                         "data": "none", "comp": False},
}


def _winner(history):
    out = pick_layout(role="content-columns", concept_count=2,
                     layout_history=history, profiles=_PROFILES, top_k=3)
    return out[0]["layout"]


def test_just_used_layout_loses_to_alternatives():
    # `horizontal-bullets` just won — without cooldown it would win again
    # on the alphabetical tiebreak. Cooldown should let another sibling
    # take it.
    assert _winner(["horizontal-bullets"]) != "horizontal-bullets"


def test_cooldown_two_slides_back_still_demoted():
    # Penalty curve: -3.0 / -2.0 / -1.0 / -0.5 across positions -1..-4.
    # Two slides back keeps `horizontal-bullets` at -1.0 → below 5.00
    # siblings, so a different layout still wins.
    assert _winner(["horizontal-bullets", "x"]) != "horizontal-bullets"
    assert _winner(["horizontal-bullets", "x", "y"]) != "horizontal-bullets"


def test_cooldown_exhausted_beyond_window():
    # Same layout five slides ago is outside the 4-slot window entirely —
    # `horizontal-bullets` returns to the alphabetical-tiebreak winner.
    assert _winner(["horizontal-bullets", "a", "b", "c", "d", "e"]) == "horizontal-bullets"

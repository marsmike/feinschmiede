"""Picker variety probe at scale — synthetic 100-slide deck
exercising the brand-aware deck-map bias + cooldown together. Measures
back-to-back streaks and Gini concentration so a future regression
that makes a strong layout dominate again surfaces immediately.

No render: the test calls plan_deck_layouts directly with synthetic
content-role signals, so it costs <1 s and is safe for CI.
"""
from __future__ import annotations

from collections import Counter

import pytest

from feinschliff.layout_budget import plan_deck_layouts
from feinschliff.layout_profile import build_profile_table


_PROFILES = {
    # Three sibling brand layouts, all content-columns, identical
    # affinity. Cooldown is what should make them rotate.
    "alpha-cards":   {"role": "content-columns", "ideal_count": (2, 4),
                      "data": "none", "comp": False},
    "beta-cards":    {"role": "content-columns", "ideal_count": (2, 4),
                      "data": "none", "comp": False},
    "gamma-cards":   {"role": "content-columns", "ideal_count": (2, 4),
                      "data": "none", "comp": False},
    "delta-cards":   {"role": "content-columns", "ideal_count": (2, 4),
                      "data": "none", "comp": False},
}
_DECK_MAP = {"content": ["alpha-cards", "beta-cards", "gamma-cards", "delta-cards"]}


def test_no_back_to_back_with_strong_cooldown():
    # 100 content slides — back-to-back same-layout pick is the v3 cookit
    # regression and must not recur with the cooldown weights in effect.
    signals = [{"role": "content-columns", "concept_count": 3} for _ in range(100)]
    plan = plan_deck_layouts(signals, profiles=_PROFILES, deck_map=_DECK_MAP)
    chosen = [s["layout"] for s in plan]
    for i in range(1, len(chosen)):
        assert chosen[i] != chosen[i - 1], (
            f"back-to-back repeat at index {i}: {chosen[i-1]} → {chosen[i]} "
            f"(sequence head: {chosen[:10]})")


def test_distribution_is_reasonably_even():
    # With 4 sibling layouts and 100 slides, each should land ~25 times.
    # Allow some asymmetry from alphabetical tiebreak but no layout
    # should be > 35% of the deck.
    signals = [{"role": "content-columns", "concept_count": 3} for _ in range(100)]
    plan = plan_deck_layouts(signals, profiles=_PROFILES, deck_map=_DECK_MAP)
    hist = Counter(s["layout"] for s in plan)
    max_share = max(hist.values()) / 100
    assert max_share < 0.36, f"one layout dominates ({max_share:.2%}): {hist}"

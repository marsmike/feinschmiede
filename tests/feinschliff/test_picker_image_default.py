"""Image-default bonus — when same-role siblings tie on affinity, the
one with an image slot wins. Presentations are a visual medium so the
default is image-driven; text-only is the exception.
"""
from __future__ import annotations

from feinschliff.layout_picker import pick_layout


_PROFILES = {
    "text-only-cards": {
        "role": "content-columns", "ideal_count": (2, 4),
        "data": "none", "comp": False,
    },
    "image-bearing-cards": {
        "role": "content-columns", "ideal_count": (2, 4),
        "data": "none", "comp": False,
        "slots": {
            "text_1": {"role": "title"},
            "text_2": {"role": "body"},
            "image":  {"role": "image", "class": "replace"},
        },
    },
}


def test_image_bearing_wins_on_equal_affinity():
    result = pick_layout(role="content-columns", concept_count=3, profiles=_PROFILES)
    assert result[0]["layout"] == "image-bearing-cards"
    assert "image-default(+1.5)" in result[0]["rationale"]


def test_text_only_still_wins_when_image_bearing_has_recency_penalty():
    # Cooldown -3 at slot -1 > the +1.5 image bonus. A recently-used
    # image-bearing layout loses to a fresh text-only sibling — variety
    # is non-negotiable.
    result = pick_layout(
        role="content-columns", concept_count=3,
        layout_history=["image-bearing-cards"],
        profiles=_PROFILES,
    )
    assert result[0]["layout"] == "text-only-cards"


def test_framing_roles_skip_image_default():
    # Closers, covers, agendas, quotes are framing chrome — the image
    # bonus should not apply, so a text-only cover doesn't lose to a
    # randomly image-bearing one.
    framing_profiles = {
        "text-cover": {
            "role": "title-primary", "ideal_count": (1, 2),
            "data": "none", "comp": False, "variety_exempt": True,
        },
        "image-cover": {
            "role": "title-primary", "ideal_count": (1, 2),
            "data": "none", "comp": False, "variety_exempt": True,
            "slots": {"image": {"role": "image", "class": "replace"}},
        },
    }
    result = pick_layout(role="title-primary", concept_count=1,
                         profiles=framing_profiles)
    # Both win on the same affinity, tiebreak goes alphabetically.
    assert result[0]["layout"] == "image-cover"
    # But the rationale does NOT include the image-default tag — the
    # bonus didn't apply (framing roles are gated).
    assert "image-default(+1.5)" not in result[0]["rationale"]

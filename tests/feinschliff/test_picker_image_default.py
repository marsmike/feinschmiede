"""Image-default bonus — content slides default to image-bearing layouts.
Uniform +1.5 density bonus + +0.5 tiebreak for image-count == concept_count.
Cooldown still dominates so layouts genuinely rotate.
"""
from __future__ import annotations

from feinschliff.layout_picker import pick_layout


def _content_profile(name, *, images=0, role="content-columns"):
    slots = {f"text_{i+1}": {"role": "body"} for i in range(2)}
    for i in range(images):
        slots[f"image_{i+1}"] = {"role": "image", "class": "replace"}
    return {
        "role": role, "ideal_count": (2, 4),
        "data": "none", "comp": False, "slots": slots,
    }


def test_image_bearing_wins_over_text_only():
    profiles = {
        "text-only-cards": _content_profile("text-only-cards"),
        "image-bearing-cards": _content_profile("image-bearing-cards", images=1),
    }
    result = pick_layout(role="content-columns", concept_count=3, profiles=profiles)
    assert result[0]["layout"] == "image-bearing-cards"


def test_uniform_density_bonus_keeps_rotation_alive():
    # 1I, 2I, 3I all get the same +1.5 density bonus. Without count-match,
    # alphabetical tiebreak picks the lex-first; after cooldown they rotate.
    profiles = {
        "one-img":   _content_profile("one-img",   images=1),
        "two-img":   _content_profile("two-img",   images=2),
        "three-img": _content_profile("three-img", images=3),
    }
    # concept_count != any image count → no count-match bonus, alphabetical wins.
    result = pick_layout(role="content-columns", concept_count=4, profiles=profiles)
    assert result[0]["layout"] == "one-img"


def test_count_match_tips_a_tie_but_does_not_dominate_cooldown():
    profiles = {
        # 2-img layout matches concept_count=2 → +0.5 tiebreak.
        "two-img-recently-used": _content_profile("two-img-recently-used", images=2),
        "three-img-fresh":       _content_profile("three-img-fresh", images=3),
    }
    # Without history, count-match makes 2-img layout win the tie.
    fresh = pick_layout(role="content-columns", concept_count=2, profiles=profiles)
    assert fresh[0]["layout"] == "two-img-recently-used"
    # With history (just used at -1), cooldown -3 overrides the +0.5 match.
    used = pick_layout(
        role="content-columns", concept_count=2,
        layout_history=["two-img-recently-used"],
        profiles=profiles,
    )
    assert used[0]["layout"] == "three-img-fresh"


def test_text_only_still_wins_when_image_bearing_has_recency_penalty():
    profiles = {
        "text-only": _content_profile("text-only"),
        "image-bearing": _content_profile("image-bearing", images=2),
    }
    result = pick_layout(
        role="content-columns", concept_count=3,
        layout_history=["image-bearing"],
        profiles=profiles,
    )
    assert result[0]["layout"] == "text-only"


def test_framing_roles_skip_image_default():
    framing = {
        "text-cover": _content_profile("text-cover", role="title-primary"),
        "image-cover": _content_profile("image-cover", images=1, role="title-primary"),
    }
    framing["text-cover"]["variety_exempt"] = True
    framing["image-cover"]["variety_exempt"] = True
    framing["text-cover"]["ideal_count"] = (1, 2)
    framing["image-cover"]["ideal_count"] = (1, 2)
    result = pick_layout(role="title-primary", concept_count=1, profiles=framing)
    assert "image-default" not in " ".join(result[0]["rationale"])

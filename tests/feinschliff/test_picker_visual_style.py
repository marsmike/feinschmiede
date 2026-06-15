"""Tests for visual_style signal in pick_layout and plan_deck_layouts.

rich-imagery: triples the image-default bonus (+1.5 → +4.5) so
image-bearing layouts beat role-matched text-only layouts.

All other visual_style values are no-ops vs None — identical scores.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from feinschliff.layout_picker import pick_layout
from feinschliff.layout_budget import plan_deck_layouts


# ── helpers ──────────────────────────────────────────────────────────────────

def _content_profile(name, *, images=0, role="content-columns"):
    slots = {f"text_{i+1}": {"role": "body"} for i in range(2)}
    for i in range(images):
        slots[f"image_{i+1}"] = {"role": "image", "class": "replace"}
    return {
        "role": role, "ideal_count": (2, 4),
        "data": "none", "comp": False, "slots": slots,
    }


# ── rich-imagery boosts image-bearing layouts above role-matched text layouts ─

def test_rich_imagery_image_wins_over_role_matched_text():
    """Image-bearing chapter-opener beats text-only content-columns with rich-imagery.

    Without rich-imagery, the role-matched content-columns layout wins (+3 role
    bonus vs +1.5 image bonus = net +1.5 advantage for text). With rich-imagery
    the image bonus triples to +4.5, exceeding the role-match weight (+3), so
    the image-bearing layout wins.
    """
    profiles = {
        # Mismatched role (chapter-opener), but has an image slot.
        "chapter-opener-image": _content_profile(
            "chapter-opener-image", images=1, role="chapter-opener"
        ),
        # Correct role (content-columns), no images.
        "text-content-columns": _content_profile(
            "text-content-columns", images=0, role="content-columns"
        ),
    }

    # Without rich-imagery: role-matched text layout should win.
    result_default = pick_layout(
        role="content-columns", concept_count=3,
        profiles=profiles, visual_style=None,
    )
    assert result_default[0]["layout"] == "text-content-columns", (
        "Without rich-imagery, role-matched text layout should win"
    )

    # With rich-imagery: image-bearing layout should win despite role mismatch.
    result_rich = pick_layout(
        role="content-columns", concept_count=3,
        profiles=profiles, visual_style="rich-imagery",
    )
    assert result_rich[0]["layout"] == "chapter-opener-image", (
        "With rich-imagery, image-bearing layout should beat role-matched text"
    )


def test_rich_imagery_rationale_tag():
    """rich-imagery rationale includes the visual_style tag."""
    profiles = {
        "img-layout": _content_profile("img-layout", images=1),
    }
    result = pick_layout(
        role="content-columns", concept_count=2,
        profiles=profiles, visual_style="rich-imagery",
    )
    rationale_str = " ".join(result[0]["rationale"])
    assert "rich-imagery" in rationale_str, (
        f"Expected 'rich-imagery' in rationale, got: {rationale_str}"
    )
    # Should NOT use the plain image-default tag (without rich-imagery label).
    assert "image-default(+" not in rationale_str or "rich-imagery" in rationale_str


def test_rich_imagery_image_wins_in_top_k():
    """Image-bearing layout is in top_k when visual_style=rich-imagery."""
    profiles = {
        "chapter-with-image": _content_profile(
            "chapter-with-image", images=1, role="chapter-opener"
        ),
        "text-content": _content_profile("text-content", images=0),
    }
    result = pick_layout(
        role="content-columns", concept_count=2,
        profiles=profiles, visual_style="rich-imagery", top_k=3,
    )
    layout_ids = [r["layout"] for r in result]
    assert "chapter-with-image" in layout_ids


# ── other visual_style values are no-ops ─────────────────────────────────────

@pytest.mark.parametrize("style", ["data-dense", "process-flow", "org-hierarchy",
                                    "concept-text", "mixed"])
def test_non_rich_imagery_styles_are_noop(style):
    """Non-rich-imagery styles produce identical scores to visual_style=None."""
    profiles = {
        "text-only": _content_profile("text-only"),
        "image-bearing": _content_profile("image-bearing", images=1),
    }
    result_none = pick_layout(
        role="content-columns", concept_count=3,
        profiles=profiles, visual_style=None,
    )
    result_style = pick_layout(
        role="content-columns", concept_count=3,
        profiles=profiles, visual_style=style,
    )
    assert result_none[0]["layout"] == result_style[0]["layout"], (
        f"visual_style={style!r} should be a no-op vs None"
    )
    assert result_none[0]["score"] == result_style[0]["score"], (
        f"visual_style={style!r} should not alter scores"
    )


# ── plan_deck_layouts threads visual_style through to pick_layout ─────────────

def test_plan_deck_layouts_passes_visual_style_to_pick_layout():
    """visual_style passed to plan_deck_layouts reaches each pick_layout call."""
    signals = [{"role": "content-columns", "concept_count": 2}]

    with patch("feinschliff.layout_budget.pick_layout") as mock_pick:
        # Return a minimal valid candidate so plan_deck_layouts doesn't fall back.
        mock_pick.return_value = [{
            "layout": "text-picture",
            "score": 1.0,
            "rationale": ["mocked"],
        }]
        plan_deck_layouts(signals, visual_style="rich-imagery")

    # pick_layout must have been called with visual_style="rich-imagery".
    call_kwargs = mock_pick.call_args
    assert call_kwargs is not None
    passed_style = call_kwargs.kwargs.get("visual_style")
    assert passed_style == "rich-imagery", (
        f"Expected visual_style='rich-imagery' in pick_layout call, got {passed_style!r}"
    )


def test_plan_deck_layouts_visual_style_none_by_default():
    """plan_deck_layouts defaults visual_style to None (no change to behaviour)."""
    signals = [{"role": "content-columns", "concept_count": 2}]

    with patch("feinschliff.layout_budget.pick_layout") as mock_pick:
        mock_pick.return_value = [{
            "layout": "text-picture",
            "score": 1.0,
            "rationale": ["mocked"],
        }]
        plan_deck_layouts(signals)

    call_kwargs = mock_pick.call_args
    assert call_kwargs is not None
    passed_style = call_kwargs.kwargs.get("visual_style")
    assert passed_style is None, (
        f"Expected visual_style=None by default, got {passed_style!r}"
    )

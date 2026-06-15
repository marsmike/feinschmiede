"""Speaker-notes emission tests.

Covers:
  - `build_presentation(..., notes=...)` writes the notes pane.
  - `build_multi_slide` accepts both 3-tuple (no notes) and 4-tuple
    (with notes) slide payloads in the same deck.
  - Empty / whitespace notes leave the slide without a materialised
    notes slide (we don't pollute the PPTX with empty notes).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.pptx_emit import build_multi_slide, build_presentation
from feinschmiede.dsl.tokens import load_tokens


REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
_CORE_BRANDS = REPO_ROOT / "brands"

# feinschliff-dark is now a theme under the feinschliff brand, not a standalone brand.
# Use the core feinschliff brand for speaker-notes tests (content is brand-agnostic).
BRAND_ROOT = _CORE_BRANDS / "feinschliff"


def _load_tokens_extra(brand_root: Path) -> object:
    """Load tokens for a brand."""
    return load_tokens(brand_root, brands_dir=brand_root.parent)


_DSL = """\
canvas 1920x1080
text 100,100 style:title "Hello"
"""


def _parse(dsl: str = _DSL):
    nodes, _ = parse_lines(dsl, source="<test>")
    return nodes


def test_build_presentation_writes_notes():
    if not BRAND_ROOT.exists():
        pytest.skip("feinschliff brand not available")
    tokens = _load_tokens_extra(BRAND_ROOT)
    notes = "Storyline: pain → demo → results.\n• Frame the cost.\n• Show the fix."
    prs = build_presentation(_parse(), tokens, notes=notes)

    slide = prs.slides[0]
    assert slide.has_notes_slide
    assert slide.notes_slide.notes_text_frame.text == notes


def test_build_presentation_no_notes_skips_notes_slide():
    if not BRAND_ROOT.exists():
        pytest.skip("feinschliff brand not available")
    tokens = _load_tokens_extra(BRAND_ROOT)
    prs = build_presentation(_parse(), tokens)
    # python-pptx exposes `has_notes_slide` only when one has been authored.
    assert not prs.slides[0].has_notes_slide


def test_build_presentation_empty_notes_skips_notes_slide():
    """Whitespace-only notes are a no-op, not an empty notes slide."""
    if not BRAND_ROOT.exists():
        pytest.skip("feinschliff brand not available")
    tokens = _load_tokens_extra(BRAND_ROOT)
    prs = build_presentation(_parse(), tokens, notes="   \n  ")
    assert not prs.slides[0].has_notes_slide


def test_build_multi_slide_mixed_payload_shapes():
    """3-tuples (no notes) and 4-tuples (with notes) coexist in one deck."""
    if not BRAND_ROOT.exists():
        pytest.skip("feinschliff brand not available")
    tokens = _load_tokens_extra(BRAND_ROOT)
    storyline = "Top-of-pyramid arc: pain → demo → results."
    payload = [
        (_parse(), tokens, None, storyline),                 # title slide w/ notes
        (_parse(), tokens, None),                            # content slide, no notes
        (_parse(), tokens, None, "• point A\n• point B"),    # content slide w/ notes
    ]
    prs = build_multi_slide(payload)

    s0, s1, s2 = prs.slides
    assert s0.has_notes_slide
    assert s0.notes_slide.notes_text_frame.text == storyline
    assert not s1.has_notes_slide
    assert s2.has_notes_slide
    assert "point A" in s2.notes_slide.notes_text_frame.text
    assert "point B" in s2.notes_slide.notes_text_frame.text

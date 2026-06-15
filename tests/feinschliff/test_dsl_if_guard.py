"""Regression test for the v2 DSL `if:` guard.

Bug C1: missing-key placeholders in `_interp` used to leak through as the
literal string `{{ … }}`. The emitter's `if:` guard only matched empty /
"false", so an optional `if:{{ cards[3].heading }}` node would render the
placeholder as visible text whenever the content dict had fewer than 4
cards. This test asserts both layers of the fix:

  1. `interpolate_nodes` resolves missing keys to "" (so `if:` becomes
     empty and the node is dropped).
  2. The emitter's `if:` guard treats any residual `{{ … }}` token as
     falsy (defense in depth).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from feinschliff.dsl.expander import expand_compounds, interpolate_nodes
from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.pptx_emit import build_presentation
from feinschmiede.dsl.tokens import load_tokens


REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
_CORE_BRANDS = REPO_ROOT / "brands"

# feinschliff-dark is now a theme under the feinschliff brand, not a standalone brand.
# Use the core feinschliff brand for DSL-guard tests (content is brand-agnostic).
BRAND_ROOT = _CORE_BRANDS / "feinschliff"


def _load_tokens_extra(brand_root: Path) -> object:
    """Load tokens for a brand."""
    return load_tokens(brand_root, brands_dir=brand_root.parent)


_DSL = """\
canvas 1920x1080
text 100,100 style:title if:{{ title }} "{{ title }}"
text 100,300 style:title if:{{ missing }} "{{ missing }}"
"""


def test_missing_key_resolves_to_empty_string():
    """`_interp` must collapse a missing key path to "" so `if:` guards work."""
    nodes, _ = parse_lines(_DSL, source="<test>")
    interp = interpolate_nodes(nodes, {"title": "Hello"})

    # The present-key node keeps its bound value.
    present = next(n for n in interp if n.kw_args.get("if") == "Hello")
    assert present.label == "Hello"

    # The missing-key node has its `if:` collapsed to "" — and its label too.
    missing = next(n for n in interp if n.label == "")
    assert missing.kw_args.get("if") == ""
    # No literal `{{ … }}` placeholder should remain anywhere on this node.
    for v in (*missing.pos_args, *missing.kw_args.values(), missing.label or ""):
        assert "{{" not in v and "}}" not in v


def test_build_presentation_suppresses_missing_if_node():
    """End-to-end: the emitter must drop the `if:{{ missing }}` text shape
    while still rendering the present-key text shape."""
    if not BRAND_ROOT.exists():
        pytest.skip("feinschliff brand not available")
    tokens = _load_tokens_extra(BRAND_ROOT)
    nodes, _ = parse_lines(_DSL, source="<test>")
    expanded, _diagnostics = expand_compounds(nodes, compounds={})
    interp = interpolate_nodes(expanded, {"title": "Hello"})

    prs = build_presentation(interp, tokens)
    slide = prs.slides[0]

    texts = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    texts.append(run.text)

    assert "Hello" in texts, f"present-key text missing, got {texts!r}"
    # The placeholder must not leak through as literal text.
    assert not any("{{" in t or "}}" in t for t in texts), (
        f"unresolved placeholder leaked into slide: {texts!r}"
    )


def test_emitter_treats_residual_placeholder_as_falsy():
    """Defense in depth: even if interpolation somehow left a `{{ … }}` in
    an `if:` condition, the emitter must still suppress the node."""
    if not BRAND_ROOT.exists():
        pytest.skip("feinschliff brand not available")
    tokens = _load_tokens_extra(BRAND_ROOT)
    # Hand-craft nodes with a leftover placeholder in `if:` (skip interpolation).
    dsl = (
        "canvas 1920x1080\n"
        'text 100,100 style:title if:{{leftover}} "should-not-render"\n'
        'text 100,300 style:title if:ok "ok-shows"\n'
    )
    nodes, _ = parse_lines(dsl, source="<test>")

    prs = build_presentation(nodes, tokens)
    slide = prs.slides[0]
    texts = [
        run.text
        for shape in slide.shapes
        if shape.has_text_frame
        for para in shape.text_frame.paragraphs
        for run in para.runs
    ]
    assert "ok-shows" in texts
    assert "should-not-render" not in texts

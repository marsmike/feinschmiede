"""Regression guard: compile_slide must resolve colors from the theme layer.

BSH-style packs carry color tokens ONLY in themes/<name>/tokens.json, with
no color block at brand level.  Before the fix, compile_slide called
load_tokens(brand_dir) and ignored the theme entirely — rendering failed
with a KeyError on color lookups, or silently used a wrong palette.

This test synthesises a minimal brand fixture in that shape and asserts
that the compiled slide's token bundle carries the theme's accent color.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from feinschliff.pipeline import compile_slide


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_theme_only_brand(root: Path) -> tuple[Path, str]:
    """Build a synthetic brand where color lives ONLY in themes/orange/tokens.json.

    Brand-level tokens.json carries fonts, slide dims, and $default_theme.
    The 'orange' theme carries the sole color block.
    Returns (brand_dir, theme_name).
    """
    brand_dir = root / "brands" / "themeonly"
    brand_dir.mkdir(parents=True)
    (brand_dir / "tokens.json").write_text(json.dumps({
        "$default_theme": "orange",
        "slide": {
            "width": "1920px", "height": "1080px",
            "width_emu": "9144000", "height_emu": "5143500",
        },
        "font-family": {"display": ["Noto Sans"], "body": ["Noto Sans"]},
        "font-size": {"display": "48px", "body": "18px"},
    }))
    theme_dir = brand_dir / "themes" / "orange"
    theme_dir.mkdir(parents=True)
    (theme_dir / "tokens.json").write_text(json.dumps({
        "color": {
            "accent":          "#FF6600",
            "background":      "#FFFFFF",
            "text":            "#1A1A1A",
            "neutral":         "#888888",
            "neutral-faint":   "#CCCCCC",
            "neutral-medium":  "#555555",
            "neutral-strong":  "#222222",
        },
    }))
    return brand_dir, "orange"


def _minimal_layout(tmp_path: Path) -> Path:
    """Write a trivial layout DSL that uses the accent color token."""
    layout = tmp_path / "minimal.slide.dsl"
    layout.write_text(
        "canvas 1920x1080\n"
        'text 100,100 style:title "{{ title }}"\n'
    )
    return layout


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_compile_slide_resolves_theme_color_block(tmp_path):
    """compile_slide with theme='orange' must surface the theme's accent color.

    The brand-level tokens.json carries NO color block; the 'orange' theme
    provides the only color definition.  Before the fix, this would fail with
    a KeyError when any downstream code looked up 'accent'.
    """
    brand_dir, theme = _make_theme_only_brand(tmp_path)
    layout = _minimal_layout(tmp_path)

    result = compile_slide(
        layout_path=layout,
        ctx={"title": "Smoke"},
        brand_dir=brand_dir,
        slide_index=1,
        diagrams_out_dir=tmp_path / "diagrams",
        theme=theme,
    )

    # compile_slide returns a CompileResult whose .tokens is the Tokens bundle.
    accent = result.tokens.color("accent")
    assert accent.upper() == "#FF6600", (
        f"expected theme accent #FF6600, got {accent!r}"
    )


def test_compile_slide_default_theme_via_brand_declaration(tmp_path):
    """compile_slide with theme=None must fall back to $default_theme from the brand.

    Same fixture: brand declares $default_theme='orange'; no explicit theme
    is passed to compile_slide.  The loader must read $default_theme and load
    the orange theme automatically.
    """
    brand_dir, _theme = _make_theme_only_brand(tmp_path)
    layout = _minimal_layout(tmp_path)

    # theme=None → load_tokens_with_theme picks $default_theme = 'orange'
    result = compile_slide(
        layout_path=layout,
        ctx={"title": "Smoke"},
        brand_dir=brand_dir,
        slide_index=1,
        diagrams_out_dir=tmp_path / "diagrams",
        theme=None,
    )

    accent = result.tokens.color("accent")
    assert accent.upper() == "#FF6600", (
        f"expected default theme accent #FF6600 via $default_theme, got {accent!r}"
    )

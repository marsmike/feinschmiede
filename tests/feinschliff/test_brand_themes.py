"""Tests for brand/theme split (Phase 1).

Covers:
  1. feinschliff brand has themes {default, claude}; default_theme == "default"
  2. Token resolution: themes/claude resolves color.accent to coral, but
     inherits font-family from brand (Noto Sans) unless overridden.
     (claude theme DOES override font-family, so we check the override works too.)
  3. Unmigrated pack (no themes/) synthesizes a single default theme.
  4. Bad theme name → friendly ValueError.
  5. tokens_hash differs between themes of the same brand.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from feinschmiede.brand.pack import BrandPack, ThemePack
from feinschmiede.dsl.tokens import load_tokens_with_theme


_REPO_ROOT = Path(__file__).resolve().parents[2]
_FEINSCHLIFF_BRANDS = _REPO_ROOT / "feinschliff" / "brands"


# ---------------------------------------------------------------------------
# 1. feinschliff brand has themes {default, claude}
# ---------------------------------------------------------------------------

def test_feinschliff_brand_has_expected_themes():
    """feinschliff brand directory ships themes: default, claude + 6 palette themes."""
    brand = BrandPack.load(_FEINSCHLIFF_BRANDS / "feinschliff")
    assert set(brand.themes.keys()) == {
        "default",
        "claude",
        "catppuccin-latte",
        "catppuccin-macchiato",
        "feinschliff-dark",
        "gruvbox-dark",
        "nord",
        "solarized-dark",
    }


def test_feinschliff_default_theme_name_is_default():
    """The brand's $default_theme token declares 'default'."""
    brand = BrandPack.load(_FEINSCHLIFF_BRANDS / "feinschliff")
    assert brand.default_theme_name == "default"


def test_feinschliff_default_theme_is_themePack():
    """BrandPack.default_theme returns a ThemePack with name 'default'."""
    brand = BrandPack.load(_FEINSCHLIFF_BRANDS / "feinschliff")
    dt = brand.default_theme
    assert isinstance(dt, ThemePack)
    assert dt.name == "default"
    assert dt.brand is brand


# ---------------------------------------------------------------------------
# 2. themes/claude resolves color.accent to coral, inherits brand structure
# ---------------------------------------------------------------------------

def test_claude_theme_accent_is_coral():
    """themes/claude overrides accent to coral (#CC785C)."""
    brand = BrandPack.load(_FEINSCHLIFF_BRANDS / "feinschliff")
    ct = brand.theme("claude")
    assert ct.tokens.color("accent").upper() == "#CC785C"


def test_default_theme_accent_is_gold():
    """themes/default keeps the feinschliff gold accent (#C9A24A)."""
    brand = BrandPack.load(_FEINSCHLIFF_BRANDS / "feinschliff")
    dt = brand.default_theme
    assert dt.tokens.color("accent").upper() == "#C9A24A"


def test_claude_theme_overrides_font_family():
    """themes/claude ships its own font-family overrides (serif display)."""
    brand = BrandPack.load(_FEINSCHLIFF_BRANDS / "feinschliff")
    ct = brand.theme("claude")
    display_fonts = ct.tokens.font_family("display")
    # Claude theme overrides display to Copernicus / EB Garamond (serif)
    assert "Copernicus" in display_fonts or "EB Garamond" in display_fonts


def test_default_theme_keeps_noto_sans():
    """themes/default keeps Noto Sans (the feinschliff brand font)."""
    brand = BrandPack.load(_FEINSCHLIFF_BRANDS / "feinschliff")
    dt = brand.default_theme
    display_fonts = dt.tokens.font_family("display")
    assert "Noto Sans" in display_fonts


def test_claude_theme_inherits_slide_dims():
    """Slide dimensions from the brand level are inherited by claude theme."""
    brand = BrandPack.load(_FEINSCHLIFF_BRANDS / "feinschliff")
    ct = brand.theme("claude")
    assert ct.tokens.slide("width") == 1920.0
    assert ct.tokens.slide("height") == 1080.0


# ---------------------------------------------------------------------------
# 3. Unmigrated pack → synthetic default theme
# ---------------------------------------------------------------------------

def test_unmigrated_brand_synthesizes_default_theme(tmp_path):
    """A brand directory without themes/ dir synthesizes a default ThemePack."""
    brand_dir = tmp_path / "brands" / "mypack"
    brand_dir.mkdir(parents=True)
    (brand_dir / "tokens.json").write_text(json.dumps({
        "color": {"accent": "#AABBCC"},
    }))

    brand = BrandPack.load(brand_dir)
    themes = brand.themes
    assert list(themes.keys()) == ["default"]
    assert themes["default"]._synthetic is True


# ---------------------------------------------------------------------------
# 4. Bad theme name → friendly ValueError
# ---------------------------------------------------------------------------

def test_bad_theme_name_raises_valueerror():
    """BrandPack.theme() raises ValueError with available themes listed."""
    brand = BrandPack.load(_FEINSCHLIFF_BRANDS / "feinschliff")
    with pytest.raises(ValueError, match="not found") as exc:
        brand.theme("nonexistent-theme-xyzzy")
    msg = str(exc.value)
    assert "default" in msg
    assert "claude" in msg


def test_load_tokens_with_theme_bad_name_raises():
    """load_tokens_with_theme with unknown theme name raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        load_tokens_with_theme(
            _FEINSCHLIFF_BRANDS / "feinschliff",
            "nonexistent-theme-xyzzy",
        )


# ---------------------------------------------------------------------------
# 5. tokens_hash differs between themes
# ---------------------------------------------------------------------------

def test_tokens_hash_differs_between_themes():
    """ThemePack.tokens_hash must differ between default and claude themes."""
    brand = BrandPack.load(_FEINSCHLIFF_BRANDS / "feinschliff")
    h_default = brand.theme("default").tokens_hash
    h_claude = brand.theme("claude").tokens_hash

    assert h_default != h_claude, "default and claude must produce different cache hashes"


def test_tokens_hash_is_12_hex_chars():
    """ThemePack.tokens_hash is 12 hex chars."""
    brand = BrandPack.load(_FEINSCHLIFF_BRANDS / "feinschliff")
    for theme_name in ["default", "claude"]:
        h = brand.theme(theme_name).tokens_hash
        assert len(h) == 12, f"{theme_name}: expected 12 chars, got {len(h)!r}"
        assert all(c in "0123456789abcdef" for c in h)


def test_feinschliff_default_accent_is_gold():
    """feinschliff default theme accent is gold (#C9A24A)."""
    tokens = load_tokens_with_theme(_FEINSCHLIFF_BRANDS / "feinschliff", "default")
    assert tokens.color("accent").upper() == "#C9A24A"

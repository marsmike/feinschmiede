"""Tests for lib.brand.BrandPack."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from feinschmiede.brand import BrandPack


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_TOKENS = {"color": {"accent": {"$value": "#C9A24A"}, "paper": "#FAF8F3"}}


def _write_brand(root: Path, name: str, tokens: dict | None = None, *, use_default: bool = True) -> Path:
    """Write a brand directory with tokens.json.

    When *tokens* is None and *use_default* is True (the default), a sensible
    default tokens dict is used.  Pass ``use_default=False`` to write an
    intentionally empty ``{}`` tokens file.
    """
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    if tokens is None and use_default:
        tok = _DEFAULT_TOKENS
    elif tokens is None:
        tok = {}
    else:
        tok = tokens
    (d / "tokens.json").write_text(json.dumps(tok))
    return d


# ---------------------------------------------------------------------------
# BrandPack.load
# ---------------------------------------------------------------------------

def test_load_sets_id(tmp_path):
    d = _write_brand(tmp_path, "alpha")
    pack = BrandPack.load(d)
    assert pack.id == "alpha"


def test_load_sets_name_alias(tmp_path):
    d = _write_brand(tmp_path, "beta")
    pack = BrandPack.load(d)
    assert pack.name == "beta"


def test_load_sets_root(tmp_path):
    d = _write_brand(tmp_path, "gamma")
    pack = BrandPack.load(d)
    assert pack.root == d


def test_load_reads_tokens(tmp_path):
    d = _write_brand(tmp_path, "delta", {"color": {"accent": {"$value": "#C9A24A"}}})
    pack = BrandPack.load(d)
    assert pack.tokens["color"]["accent"]["$value"] == "#C9A24A"


def test_load_tokens_hash_is_12_chars(tmp_path):
    d = _write_brand(tmp_path, "epsilon")
    pack = BrandPack.load(d)
    assert len(pack.tokens_hash) == 12
    assert all(c in "0123456789abcdef" for c in pack.tokens_hash)


def test_load_tokens_hash_matches_sha1_of_file(tmp_path):
    d = _write_brand(tmp_path, "zeta")
    raw = (d / "tokens.json").read_bytes()
    expected = hashlib.sha1(raw).hexdigest()[:12]
    pack = BrandPack.load(d)
    assert pack.tokens_hash == expected


def test_load_raises_when_no_tokens_json(tmp_path):
    d = tmp_path / "no-tokens"
    d.mkdir()
    with pytest.raises(FileNotFoundError, match="tokens.json"):
        BrandPack.load(d)


# ---------------------------------------------------------------------------
# layouts_path / compounds_path
# ---------------------------------------------------------------------------

def test_layouts_path_none_when_absent(tmp_path):
    d = _write_brand(tmp_path, "eta")
    pack = BrandPack.load(d)
    assert pack.layouts_path is None


def test_layouts_path_returned_when_present(tmp_path):
    d = _write_brand(tmp_path, "theta")
    (d / "layouts").mkdir()
    pack = BrandPack.load(d)
    assert pack.layouts_path == d / "layouts"


def test_compounds_path_none_when_absent(tmp_path):
    d = _write_brand(tmp_path, "iota")
    pack = BrandPack.load(d)
    assert pack.compounds_path is None


def test_compounds_path_returned_when_present(tmp_path):
    d = _write_brand(tmp_path, "kappa")
    (d / "compounds").mkdir()
    pack = BrandPack.load(d)
    assert pack.compounds_path == d / "compounds"


def test_tokens_path_returned_when_present(tmp_path):
    d = _write_brand(tmp_path, "lambda")
    pack = BrandPack.load(d)
    assert pack.tokens_path == d / "tokens.json"


# ---------------------------------------------------------------------------
# resolve_token
# ---------------------------------------------------------------------------

def test_resolve_token_finds_nested_value(tmp_path):
    d = _write_brand(tmp_path, "mu", {"color": {"accent": {"$value": "#C9A24A"}}})
    pack = BrandPack.load(d)
    result = pack.resolve_token("color.accent")
    assert result == {"$value": "#C9A24A"}


def test_resolve_token_bare_string(tmp_path):
    d = _write_brand(tmp_path, "nu", {"color": {"paper": "#FAF8F3"}})
    pack = BrandPack.load(d)
    result = pack.resolve_token("color.paper")
    assert result == "#FAF8F3"


def test_resolve_token_returns_none_for_missing_path(tmp_path):
    d = _write_brand(tmp_path, "xi", {"color": {"accent": "#aaa"}})
    pack = BrandPack.load(d)
    assert pack.resolve_token("color.does-not-exist") is None
    assert pack.resolve_token("totally.wrong.path") is None


def test_resolve_token_returns_none_for_empty_tokens(tmp_path):
    d = _write_brand(tmp_path, "omicron", use_default=False)
    pack = BrandPack.load(d)
    assert pack.resolve_token("color.accent") is None


# ---------------------------------------------------------------------------
# layout resolution — brand-local wins over toolkit
#
# Layout discovery moved off BrandPack onto the office picker (engine→office
# back-edge severance); these now exercise the office helper directly.
# ---------------------------------------------------------------------------

def test_find_layout_returns_brand_local_first(tmp_path, monkeypatch):
    from feinschliff.deck.picker import _resolve_layout_path

    d = _write_brand(tmp_path, "pi")
    layouts = d / "layouts"
    layouts.mkdir()
    layout_file = layouts / "my-layout.slide.dsl"
    layout_file.write_text("canvas 1920x1080")

    # Toolkit fallback should never be reached
    monkeypatch.setattr("feinschliff.layout_discovery.find_layout", lambda name: None)

    pack = BrandPack.load(d)
    result = _resolve_layout_path(pack.layouts_path, "my-layout")
    assert result == layout_file


def test_find_layout_falls_back_to_toolkit(tmp_path, monkeypatch):
    from feinschliff.deck.picker import _resolve_layout_path
    from feinschliff.layout_discovery import Layout
    d = _write_brand(tmp_path, "rho")
    toolkit_path = tmp_path / "toolkit-layout.slide.dsl"
    toolkit_path.write_text("canvas 1920x1080")

    monkeypatch.setattr(
        "feinschliff.layout_discovery.find_layout",
        lambda name: Layout(name=name, path=toolkit_path),
    )

    pack = BrandPack.load(d)
    result = _resolve_layout_path(pack.layouts_path, "toolkit-only")
    assert result == toolkit_path


def test_find_layout_returns_none_when_not_found(tmp_path, monkeypatch):
    from feinschliff.deck.picker import _resolve_layout_path

    d = _write_brand(tmp_path, "sigma")
    monkeypatch.setattr("feinschliff.layout_discovery.find_layout", lambda name: None)
    pack = BrandPack.load(d)
    assert _resolve_layout_path(pack.layouts_path, "nonexistent") is None


def test_find_layout_resolves_sibling_brand_prefix(tmp_path, monkeypatch):
    """``<brand>-<stem>`` resolves against a sibling brand pack."""
    from feinschliff.deck.picker import _resolve_layout_path

    packs = tmp_path / "brands"
    active = _write_brand(packs, "globex")
    (active / "layouts").mkdir()
    sibling = _write_brand(packs, "acme")
    sibling_layouts = sibling / "layouts"
    sibling_layouts.mkdir()
    target = sibling_layouts / "slide-25.slide.dsl"
    target.write_text("canvas 1920x1080")

    monkeypatch.setattr("feinschliff.layout_discovery.find_layout", lambda name: None)
    pack = BrandPack.load(active)
    assert _resolve_layout_path(pack.layouts_path, "acme-slide-25") == target


def test_find_layout_brand_prefix_handles_multiword_brand(tmp_path, monkeypatch):
    """Brand names containing ``-`` are matched by trying increasingly long prefixes."""
    from feinschliff.deck.picker import _resolve_layout_path

    packs = tmp_path / "brands"
    active = _write_brand(packs, "globex")
    (active / "layouts").mkdir()
    sibling = _write_brand(packs, "gs-ramspau")
    sibling_layouts = sibling / "layouts"
    sibling_layouts.mkdir()
    target = sibling_layouts / "slide-01.slide.dsl"
    target.write_text("canvas 1920x1080")

    monkeypatch.setattr("feinschliff.layout_discovery.find_layout", lambda name: None)
    pack = BrandPack.load(active)
    assert _resolve_layout_path(pack.layouts_path, "gs-ramspau-slide-01") == target


def test_find_layout_brand_prefix_unknown_brand_returns_none(tmp_path, monkeypatch):
    """Unknown prefix falls through; toolkit discovery is the last resort."""
    from feinschliff.deck.picker import _resolve_layout_path

    packs = tmp_path / "brands"
    active = _write_brand(packs, "globex")
    (active / "layouts").mkdir()

    monkeypatch.setattr("feinschliff.layout_discovery.find_layout", lambda name: None)
    pack = BrandPack.load(active)
    assert _resolve_layout_path(pack.layouts_path, "doesnotexist-slide-25") is None


def test_orchestrate_resolve_layout_path_handles_brand_prefix(tmp_path):
    """``resolve_layout_path`` (used by the deck builder) honours brand prefixes."""
    from feinschliff.deck.orchestrate import resolve_layout_path

    packs = tmp_path / "brands"
    active = _write_brand(packs, "globex")
    (active / "layouts").mkdir()
    sibling = _write_brand(packs, "acme")
    sibling_layouts = sibling / "layouts"
    sibling_layouts.mkdir()
    target = sibling_layouts / "slide-25.slide.dsl"
    target.write_text("canvas 1920x1080")

    assert resolve_layout_path(active, "acme-slide-25") == target


# ---------------------------------------------------------------------------
# find_compound
# ---------------------------------------------------------------------------

def test_find_compound_returns_brand_local_first(tmp_path):
    d = _write_brand(tmp_path, "tau")
    compounds = d / "compounds"
    compounds.mkdir()
    compound_file = compounds / "footer.dsl"
    compound_file.write_text("compound footer():\n  text 0,0 \"x\"\n")

    pack = BrandPack.load(d)
    result = pack.find_compound("footer")
    assert result is not None
    assert result.name == "footer"
    assert result.path == compound_file
    assert result.origin == "brand-local"


def test_find_compound_returns_none_when_not_found(tmp_path):
    # A brand with no compounds/ dir, and we use a name that won't exist
    # in the toolkit's real compounds/ either.
    d = _write_brand(tmp_path, "upsilon")
    pack = BrandPack.load(d)
    # Use an obviously-fake name that won't exist in the toolkit compounds/
    result = pack.find_compound("nonexistent-compound-xyzzy-abc")
    assert result is None


def test_find_compound_falls_back_to_toolkit(tmp_path):
    """A brand with no local compounds/ falls back to the toolkit's bundled ones."""
    # Brand has no compounds/ directory — only tokens.json.
    d = _write_brand(tmp_path, "zeta")
    pack = BrandPack.load(d)
    assert pack.compounds_path is None  # no local compounds

    # "card" is a real toolkit compound: compounds/card.dsl
    result = pack.find_compound("card")
    assert result is not None
    assert result.name == "card"
    assert result.path.is_file()
    assert result.path.name == "card.dsl"
    assert result.origin == "toolkit"


# ---------------------------------------------------------------------------
# Repr + equality
# ---------------------------------------------------------------------------

def test_repr_includes_id(tmp_path):
    d = _write_brand(tmp_path, "phi")
    pack = BrandPack.load(d)
    assert "phi" in repr(pack)


def test_equality_same_dir(tmp_path):
    d = _write_brand(tmp_path, "chi")
    p1 = BrandPack.load(d)
    p2 = BrandPack.load(d)
    assert p1 == p2


def test_inequality_different_dirs(tmp_path):
    d1 = _write_brand(tmp_path, "psi")
    d2 = _write_brand(tmp_path, "omega")
    assert BrandPack.load(d1) != BrandPack.load(d2)

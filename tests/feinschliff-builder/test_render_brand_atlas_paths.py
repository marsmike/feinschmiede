"""Path resolution of scripts/render_brand_atlas.py against the
post-restructure workspace (brands split across feinschliff/ and
feinschliff-extra/). Each brand renders only its own layouts (PR #98
pack isolation); there is no shared toolkit pool in the renderer."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "render_brand_atlas",
    Path(__file__).resolve().parents[2] / "feinschliff-builder" / "scripts" / "render_brand_atlas.py",
)
rba = importlib.util.module_from_spec(_SPEC)
# dataclasses resolves annotations via sys.modules[cls.__module__]
sys.modules["render_brand_atlas"] = rba
_SPEC.loader.exec_module(rba)


def test_brand_roots_cover_core_and_extra():
    assert "feinschliff" in rba.BRAND_ROOTS   # core plugin
    assert "annual-review" in rba.BRAND_ROOTS  # feinschliff-extra


def test_default_enumeration_covers_core_and_extra():
    brands = rba._all_brands()
    assert {"feinschliff", "scientific"} <= set(brands)


def test_discovery_returns_only_brand_layouts():
    # annual-review owns exactly its own layouts/ dir — no shared toolkit pool.
    ids = dict(rba._discover_layouts("annual-review"))
    assert "agenda" in ids               # brand ships its own agenda layout
    assert len(ids) == 13                # only the 13 annual-review layouts
    # feinschliff's toolkit layouts are NOT included for extra brands
    assert "2x2-matrix" not in ids
    assert rba._find_content("feinschliff", "agenda") is not None


def test_feinschliff_discovery_returns_its_own_layouts():
    # feinschliff owns the toolkit layouts under its own layouts/ dir
    ids = dict(rba._discover_layouts("feinschliff"))
    assert len(ids) >= 40                # the full toolkit catalog
    assert "2x2-matrix" in ids



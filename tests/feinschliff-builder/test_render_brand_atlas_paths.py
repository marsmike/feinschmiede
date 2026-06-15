"""Path resolution of scripts/render_brand_atlas.py against the
post-restructure workspace (brands split across feinschliff/ and
feinschliff-extra/, shared layouts under feinschliff/layouts/)."""
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


def test_discovery_finds_shared_and_brand_layouts():
    ids = dict(rba._discover_layouts("annual-review"))
    assert "agenda" in ids          # shared toolkit layout or brand override
    assert len(ids) >= 40           # the toolkit catalog is visible
    assert rba._find_content("feinschliff", "agenda") is not None



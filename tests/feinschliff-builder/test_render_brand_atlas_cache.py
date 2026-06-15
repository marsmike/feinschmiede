"""Regression: brand atlas mtime cache must include brand's own tokens/compounds.

Original bug (commit a823729): `_cache_inputs_mtime` only looked at layout
and content paths, not the brand's own tokens.json. Now covers brand's
own tokens.json, DESIGN.md, and compounds/*.dsl.

Note: extends-chain walking was removed; each brand pack is self-contained.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "feinschliff-builder"
SCRIPT = REPO_ROOT / "scripts" / "render_brand_atlas.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("render_brand_atlas", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["render_brand_atlas"] = module
    spec.loader.exec_module(module)
    return module


def _make_brand(root: Path, name: str) -> Path:
    brand = root / name
    brand.mkdir(parents=True, exist_ok=True)
    (brand / "tokens.json").write_text('{"colors": {}}')
    (brand / "DESIGN.md").write_text("---\nname: x\n---\n")
    return brand


def _set_mtime(path: Path, mtime: float) -> None:
    os.utime(path, (mtime, mtime))


def test_cache_invalidated_when_tokens_change(tmp_path):
    """Modifying the brand's own tokens.json must invalidate its cache entry."""
    mod = _load_script_module()
    brands = tmp_path / "brands"
    brand = _make_brand(brands, "mybrand")

    layout = tmp_path / "layout.slide.dsl"
    layout.write_text("# layout")
    content = tmp_path / "content.yaml"
    content.write_text("title: x")
    out_png = tmp_path / "out.png"
    out_png.write_text("png-bytes")

    t0 = time.time() - 1000
    for p in [layout, content, out_png, brand / "tokens.json", brand / "DESIGN.md"]:
        _set_mtime(p, t0)

    _set_mtime(brand / "tokens.json", t0 + 500)

    job = mod.LayoutJob(
        brand="mybrand",
        layout_id="x",
        layout_path=layout,
        content_path=content,
        out_png=out_png,
        index=1,
    )
    inputs_mtime = mod._cache_inputs_mtime(job, brand)
    assert inputs_mtime > out_png.stat().st_mtime, (
        "brand tokens.json mtime should be included in cache key; "
        f"got inputs_mtime={inputs_mtime}, png_mtime={out_png.stat().st_mtime}"
    )


def test_cache_stable_when_unrelated_brand_changes(tmp_path, monkeypatch):
    """Touching a sibling brand's tokens.json must NOT invalidate another brand's cache."""
    mod = _load_script_module()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    brands = tmp_path / "brands"
    sibling = _make_brand(brands, "nord")
    brand = _make_brand(brands, "mybrand")

    layout = tmp_path / "layout.slide.dsl"
    layout.write_text("# layout")
    content = tmp_path / "content.yaml"
    content.write_text("title: x")
    out_png = tmp_path / "out.png"
    out_png.write_text("png-bytes")

    t0 = time.time() - 1000
    for p in [layout, content, out_png,
              sibling / "tokens.json", sibling / "DESIGN.md",
              brand / "tokens.json", brand / "DESIGN.md"]:
        _set_mtime(p, t0)

    _set_mtime(sibling / "tokens.json", t0 + 500)

    job = mod.LayoutJob(
        brand="mybrand",
        layout_id="x",
        layout_path=layout,
        content_path=content,
        out_png=out_png,
        index=1,
    )
    assert mod._cache_inputs_mtime(job, brand) == out_png.stat().st_mtime

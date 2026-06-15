"""brand_bridge delegates token loading to dsl.tokens and caches per brand dir.

- repeated resolve() calls load tokens.json from disk exactly once
- the cache key includes tokens.json mtime, so an edited file is re-read
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from feinschmiede.diagrams import brand_bridge
from feinschmiede.diagrams.brand_bridge import BrandBridgeError, resolve


def _write_brand(root: Path, name: str, colors: dict[str, str]) -> Path:
    brand = root / name
    brand.mkdir()
    (brand / "tokens.json").write_text(json.dumps({"color": colors}))
    return brand


def test_repeated_resolve_loads_tokens_once(tmp_path, monkeypatch):
    brand = _write_brand(tmp_path, "myco", {
        "accent": "#111111", "paper": "#ffffff", "ink": "#000000",
    })
    calls: list[Path] = []
    real = brand_bridge._load_raw_tokens

    def counting(brand_root):
        calls.append(brand_root)
        return real(brand_root)

    monkeypatch.setattr(brand_bridge, "_load_raw_tokens", counting)
    for name in ("primary", "paper", "ink", "primary", "paper"):
        assert resolve(name, brand).startswith("#")
    assert len(calls) == 1


def test_tokens_json_edit_invalidates_cache(tmp_path):
    brand = _write_brand(tmp_path, "myco", {"accent": "#111111"})
    assert resolve("primary", brand) == "#111111"

    tokens_path = brand / "tokens.json"
    old_mtime_ns = tokens_path.stat().st_mtime_ns
    tokens_path.write_text(json.dumps({"color": {"accent": "#222222"}}))
    # Force a distinct mtime even on coarse-granularity filesystems.
    os.utime(tokens_path, ns=(old_mtime_ns + 1, old_mtime_ns + 1))
    assert resolve("primary", brand) == "#222222"


def test_missing_tokens_json_still_raises_brand_bridge_error(tmp_path):
    brand = tmp_path / "empty"
    brand.mkdir()
    with pytest.raises(BrandBridgeError, match="tokens.json missing"):
        resolve("primary", brand)

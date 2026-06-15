"""Tests for `$image_provider` propagation through brand discovery + tokens loader.

The `$image_provider` block lives at the top of `tokens.json`. It is read
by `lib.brand_discovery.discover_brands()` onto `Brand.image_provider_config`.
Each brand pack is self-contained (no extends inheritance).
"""
from __future__ import annotations

import json
from pathlib import Path

from feinschmiede.brand_discovery import discover_brands


# Minimal tokens.json scaffold required by the loader's schema. Tests that
# exercise `load_tokens` end-to-end against the merged schema need this;
# tests that only check `discover_brands` field population can use a
# leaner stub since discovery does not validate.
_VALID_TOKENS_BASE: dict[str, object] = {
    "color": {"ink": "#111111", "accent": "#ff0000", "paper": "#ffffff"},
    "font-family": {
        "display": ["Inter"],
        "body": ["Inter"],
        "mono": ["Consolas"],
    },
    "font-size": {"slide-title": "56px", "body": "18px", "eyebrow": "14px"},
    "font-weight": {"regular": 400, "semibold": 600, "bold": 700},
}


def _write_brand(
    root: Path,
    name: str,
    *,
    tokens_extra: dict | None = None,
) -> Path:
    """Stage a brand pack under `root/name/`. Returns the brand dir."""
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    body: dict = dict(_VALID_TOKENS_BASE)
    if tokens_extra:
        body.update(tokens_extra)
    (d / "tokens.json").write_text(json.dumps(body))
    return d


# ---------------------------------------------------------------------------
# discover_brands → Brand.image_provider_config
# ---------------------------------------------------------------------------


def test_brand_without_image_provider_has_none(tmp_path, monkeypatch):
    """A brand pack with no `$image_provider` → field is None."""
    bundled = tmp_path / "bundled" / "brands"
    _write_brand(bundled, "plain")
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    [b] = [x for x in discover_brands() if x.name == "plain"]
    assert b.image_provider_config is None


def test_brand_with_image_provider_populates_field(tmp_path, monkeypatch):
    """`$image_provider` in tokens.json → Brand carries the dict verbatim."""
    bundled = tmp_path / "bundled" / "brands"
    _write_brand(
        bundled,
        "with-provider",
        tokens_extra={
            "$image_provider": {
                "kind": "unsplash",
                "config": {"rate_limit": 50},
            }
        },
    )
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    [b] = [x for x in discover_brands() if x.name == "with-provider"]
    assert b.image_provider_config == {
        "kind": "unsplash",
        "config": {"rate_limit": 50},
    }



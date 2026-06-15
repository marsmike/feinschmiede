import json
import warnings
from pathlib import Path

import pytest

from feinschmiede.brand_discovery import discover_brands, find_brand


def _write_brand(root: Path, name: str) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    # tokens.json is the v2 brand marker. (V1's catalog.json detection was
    # removed in 2026-05-16 — no shipped brand ever used catalog.json under
    # the v2 pipeline.)
    (d / "tokens.json").write_text(json.dumps({"name": name, "colors": {}}))
    return d


def test_discover_brands_finds_bundled(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled" / "brands"
    _write_brand(bundled, "alpha")
    _write_brand(bundled, "beta")
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    brands = discover_brands()
    names = sorted(b.name for b in brands)
    assert names == ["alpha", "beta"]


def test_discover_brands_finds_env_path(tmp_path, monkeypatch):
    extra = tmp_path / "extra"
    _write_brand(extra, "gamma")
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", str(extra))
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: tmp_path / "no-bundled")
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    brands = discover_brands()
    assert any(b.name == "gamma" for b in brands)


def test_brand_dataclass_carries_paths(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled" / "brands"
    d = _write_brand(bundled, "delta")
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    [delta] = [b for b in discover_brands() if b.name == "delta"]
    assert delta.root == d
    assert delta.tokens_path == d / "tokens.json"


def test_plugin_brands_roots_walks_marketplace_layout(tmp_path, monkeypatch):
    """Marketplace-installed plugins live under ~/.claude/plugins/marketplaces/{m}/{plugin}/brands."""
    fake_home = tmp_path / "home"
    plugins = fake_home / ".claude" / "plugins"
    team = plugins / "marketplaces" / "acme-team" / "feinschliff-acme" / "brands"
    team.mkdir(parents=True)
    oss = plugins / "marketplaces" / "feinschliff" / "feinschliff" / "brands"
    oss.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    from feinschmiede.brand_discovery import _plugin_brands_roots
    roots = _plugin_brands_roots()
    assert team in roots
    assert oss in roots


def test_plugin_brands_roots_includes_sideload_layout(tmp_path, monkeypatch):
    """Sideloaded plugins live directly under ~/.claude/plugins/{plugin}/brands."""
    fake_home = tmp_path / "home"
    plugins = fake_home / ".claude" / "plugins"
    sideload = plugins / "legacy-plugin" / "brands"
    sideload.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    from feinschmiede.brand_discovery import _plugin_brands_roots
    roots = _plugin_brands_roots()
    assert sideload in roots


def test_cwd_dev_brands_roots_finds_in_place_checkout(tmp_path, monkeypatch):
    """When $CWD is inside a feinschliff/ git checkout, brands/ should be discovered."""
    checkout = tmp_path / "feinschliff-repo"
    (checkout / ".git").mkdir(parents=True)
    fb = checkout / "feinschliff"
    (fb / "brands").mkdir(parents=True)
    _write_brand(fb / "brands", "in-place-brand")
    # Run from somewhere inside the checkout.
    monkeypatch.chdir(fb / "brands" / "in-place-brand")

    from feinschmiede.brand_discovery import _cwd_dev_brands_roots
    roots = _cwd_dev_brands_roots()
    assert (fb / "brands") in roots


def test_find_brand_raises_with_diagnostic(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled" / "brands"
    _write_brand(bundled, "alpha")
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    found = find_brand("alpha")
    assert found.name == "alpha"

    with pytest.raises(ValueError) as exc:
        find_brand("does-not-exist")
    msg = str(exc.value)
    assert "does-not-exist" in msg
    assert "alpha" in msg          # lists available
    assert "[bundled]" in msg      # tags the searched source
    assert "FEINSCHLIFF_BRAND_PATH" in msg


def test_discover_brands_ignores_dir_without_brand_marker(tmp_path, monkeypatch):
    """A directory without `tokens.json` or `DESIGN.md` is not a brand."""
    bundled = tmp_path / "bundled" / "brands"
    empty_brand = bundled / "no-marker"
    empty_brand.mkdir(parents=True)

    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    assert "no-marker" not in {b.name for b in discover_brands()}


def test_discover_brands_warns_on_broken_image_provider(tmp_path, monkeypatch):
    """A brand whose `load_tokens` raises must (a) NOT crash discovery, (b)
    still surface that brand with `image_provider_config=None`, (c) emit a
    RuntimeWarning naming the brand, and (d) leave sibling brands unaffected.

    Regression guard against the prior `except Exception: pass` swallow that
    made misconfigured brands indistinguishable from brands with no provider
    declared.
    """
    bundled = tmp_path / "bundled" / "brands"
    # Broken brand: malformed JSON in tokens.json → JSONDecodeError, caught.
    broken = bundled / "image-provider-broken"
    broken.mkdir(parents=True)
    (broken / "tokens.json").write_text("{not valid json")
    # Good sibling: minimum valid tokens.json so load_tokens succeeds.
    good = bundled / "image-provider-good"
    good.mkdir(parents=True)
    (good / "tokens.json").write_text(json.dumps({
        "color": {"ink": "#111111", "accent": "#ff0000", "paper": "#ffffff"},
        "font-family": {
            "display": ["Inter"],
            "body": ["Inter"],
            "mono": ["Consolas"],
        },
        "font-size": {"slide-title": "56px", "body": "18px", "eyebrow": "14px"},
        "font-weight": {"regular": 400, "semibold": 600, "bold": 700},
        "$image_provider": {"kind": "unsplash", "config": {"rate_limit": 50}},
    }))

    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        brands = {b.name: b for b in discover_brands()}

    # (a) + (b): both brands surfaced; broken brand has no provider config.
    assert "image-provider-broken" in brands
    assert "image-provider-good" in brands
    assert brands["image-provider-broken"].image_provider_config is None

    # (c) RuntimeWarning fired, names the broken brand + the exception type.
    runtime_msgs = [
        str(w.message) for w in caught if issubclass(w.category, RuntimeWarning)
    ]
    matching = [m for m in runtime_msgs if "image-provider-broken" in m]
    assert matching, f"expected RuntimeWarning naming the broken brand; got {runtime_msgs}"
    assert "$image_provider" in matching[0]

    # (d) sibling unaffected.
    assert brands["image-provider-good"].image_provider_config == {
        "kind": "unsplash",
        "config": {"rate_limit": 50},
    }


def test_env_path_beats_same_named_plugin_brand(tmp_path, monkeypatch):
    """FEINSCHLIFF_BRAND_PATH is an explicit operator override — a same-named
    brand in an installed plugin must not shadow it (the verify-loop's
    --brand-pack contract depends on this)."""
    env_root = tmp_path / "env" / "brands"
    plugin_root = tmp_path / "plugin" / "brands"
    _write_brand(env_root, "omega")
    _write_brand(plugin_root, "omega")
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", str(env_root))
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: tmp_path / "no-bundled")
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [plugin_root])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    omega = find_brand("omega")
    assert omega.root == env_root / "omega", (
        f"plugin copy shadowed the env override: {omega.root}"
    )


def _fake_checkout(tmp_path, monkeypatch):
    """A minimal feinschmiede-like checkout: core brands + a sibling plugin
    dir + a gitignored corporate fixture, with $CWD inside it."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    _write_brand(repo / "feinschliff" / "brands", "feinschliff")
    _write_brand(repo / "feinschliff-extra" / "brands", "shapes")
    _write_brand(repo / "feinschliff-corp" / "brands", "corp")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: tmp_path / "no-bundled")
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    return repo


def test_cwd_dev_discovers_sibling_plugin_brands(tmp_path, monkeypatch):
    """feinschliff-extra/ + gitignored feinschliff-<corp>/ packs in the
    working checkout must be detected without FEINSCHLIFF_BRAND_PATH."""
    _fake_checkout(tmp_path, monkeypatch)
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    names = {b.name for b in discover_brands()}
    assert {"feinschliff", "shapes", "corp"} <= names


def test_cwd_dev_beats_same_named_plugin_brand(tmp_path, monkeypatch):
    """The checkout the user is standing in outranks a stale installed
    marketplace copy of the same brand."""
    repo = _fake_checkout(tmp_path, monkeypatch)
    plugin_root = tmp_path / "marketplace" / "feinschliff-extra" / "brands"
    _write_brand(plugin_root, "shapes")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [plugin_root])
    shapes = find_brand("shapes")
    assert shapes.root == repo / "feinschliff-extra" / "brands" / "shapes", (
        f"stale plugin copy shadowed the working checkout: {shapes.root}"
    )



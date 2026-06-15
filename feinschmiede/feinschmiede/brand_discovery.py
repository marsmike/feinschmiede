"""Locate brand packs across bundled, plugin-installed, env, and user-local paths."""
from __future__ import annotations

import os
import warnings
from json import JSONDecodeError
from pathlib import Path

from feinschmiede.brand import BrandPack
from feinschmiede.dsl.tokens import load_tokens


def _bundled_brands_root() -> Path:
    """A ``brands/`` dir co-located with the engine package, if one is shipped.

    The shared ``feinschmiede`` engine ships no brand packs of its own, so this
    source is normally absent — brands arrive via installed plugins
    (``_plugin_brands_roots``) and ``FEINSCHLIFF_BRAND_PATH`` (which a consuming
    plugin's launcher sets to its bundled ``brands/``).
    """
    return Path(__file__).resolve().parents[1] / "brands"


def _user_brands_root() -> Path:
    return Path.home() / ".feinschliff" / "brands"


def _plugin_brands_roots() -> list[Path]:
    """`brands/` dirs from installed Claude Code plugins.

    Brand packs are intentionally permissive — any plugin can ship a ``brands/``
    directory (e.g. third-party brand packs, private supplier packs), so no plugin-name
    filter is applied here.

    Modern plugins land under ``~/.claude/plugins/marketplaces/{marketplace}/{plugin}/``;
    sideloaded plugins occasionally land directly under ``~/.claude/plugins/{plugin}/``.
    Both layouts are supported.
    """
    plugins = Path.home() / ".claude" / "plugins"
    if not plugins.is_dir():
        return []
    roots: list[Path] = []
    marketplaces = plugins / "marketplaces"
    if marketplaces.is_dir():
        for marketplace in sorted(marketplaces.iterdir()):
            if not marketplace.is_dir():
                continue
            for plugin in sorted(marketplace.iterdir()):
                brands = plugin / "brands"
                if brands.is_dir():
                    roots.append(brands)
    for entry in sorted(plugins.iterdir()):
        if entry.name == "marketplaces" or not entry.is_dir():
            continue
        brands = entry / "brands"
        if brands.is_dir():
            roots.append(brands)
    return roots


def _env_brands_roots() -> list[Path]:
    raw = os.environ.get("FEINSCHLIFF_BRAND_PATH", "")
    return [Path(p) for p in raw.split(os.pathsep) if p]


def _cwd_dev_brands_roots() -> list[Path]:
    """Walk up from $CWD; if an in-place git checkout of feinschliff exists,
    surface its brands/. Supports the dev workflow where a brand author edits
    `~/work/feinschliff/feinschliff/brands/<brand>/` and runs scripts that
    don't sit inside the package.

    Sibling plugin dirs in the same checkout ship brands too — the public
    `feinschliff-extra/brands/` plus gitignored corporate fixtures
    (`feinschliff-<corp>/brands/`). Without the glob those packs (and any
    brand they `extends:`-derive) are invisible unless FEINSCHLIFF_BRAND_PATH
    is exported, and a stale installed-plugin copy of a same-named brand
    silently wins.

    The walk stops at the first git boundary so we don't accidentally scan
    the whole home directory.
    """
    out: list[Path] = []
    try:
        cwd = Path.cwd().resolve()
    except FileNotFoundError:
        return out
    for ancestor in [cwd, *cwd.parents]:
        candidate = ancestor / "feinschliff" / "brands"
        if candidate.is_dir():
            out.append(candidate)
        for plugin_brands in sorted(ancestor.glob("feinschliff-*/brands")):
            if plugin_brands.is_dir():
                out.append(plugin_brands)
        # Also handle a checkout where the cwd is already inside `feinschliff/`.
        sibling = ancestor / "brands"
        if (ancestor / "pyproject.toml").is_file() and sibling.is_dir():
            out.append(sibling)
        if (ancestor / ".git").exists():
            break
    return out


def _discovery_sources() -> list[tuple[str, Path]]:
    """Source-tagged list used by both discovery and the not-found error.

    `env` and `cwd-dev` outrank `plugin`: an explicit FEINSCHLIFF_BRAND_PATH
    override and the working checkout the user is standing in are both more
    intentional than an ambient installed plugin — a stale marketplace copy
    of a same-named brand must not shadow either.
    """
    items: list[tuple[str, Path]] = [("bundled", _bundled_brands_root())]
    items.extend(("env", p) for p in _env_brands_roots())
    items.extend(("cwd-dev", p) for p in _cwd_dev_brands_roots())
    items.extend(("plugin", p) for p in _plugin_brands_roots())
    items.append(("user", _user_brands_root()))
    return items


# Process-lifetime discovery cache. A full scan runs load_tokens (extends
# walk + schema validation) for EVERY brand (~180 ms with ~17 packs), and
# multi-slide deck builds call find_brand per slide — 120 slides paid ~22 s
# of pure rescans. The key captures every input the scan reads: the source
# roots, each brand dir, and its tokens.json / DESIGN.md mtimes — creating,
# deleting, or editing a brand invalidates it (≈50 stat calls, <1 ms).
_discovery_cache: tuple[tuple, list[BrandPack]] | None = None


def _discovery_cache_key() -> tuple:
    key: list = []
    for _src, root in _discovery_sources():
        if not root.is_dir():
            continue
        key.append(str(root))
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            for marker in (d / "tokens.json", d / "DESIGN.md"):
                try:
                    key.append((str(marker), marker.stat().st_mtime_ns))
                except OSError:
                    pass
            # Include theme tokens files so edits to themes/ invalidate the cache.
            themes_dir = d / "themes"
            if themes_dir.is_dir():
                for theme_dir in sorted(themes_dir.iterdir()):
                    if not theme_dir.is_dir():
                        continue
                    theme_tj = theme_dir / "tokens.json"
                    try:
                        key.append((str(theme_tj), theme_tj.stat().st_mtime_ns))
                    except OSError:
                        pass
    return tuple(key)


def discover_brands() -> list[BrandPack]:
    """Returns all brands found across all discovery sources, deduped by name (first wins).

    A brand is a directory containing either `tokens.json` (the v2 marker)
    or `DESIGN.md` (with token frontmatter). Brands inherit toolkit-level
    layouts and may add brand-specific ones via `layouts/`.

    Sources scanned, in priority order:
      1. bundled — `brands/` next to the installed `lib/`
      2. env — directories listed in `FEINSCHLIFF_BRAND_PATH` (colon-separated)
      3. cwd-dev — `feinschliff/brands/` and sibling `feinschliff-*/brands/`
         reachable by walking up from $CWD
      4. plugin — `~/.claude/plugins/.../brands/`
      5. user — `~/.feinschliff/brands/`

    Results are cached for the life of the process, keyed on the marker-file
    mtimes of every candidate brand dir (see `_discovery_cache_key`).
    """
    global _discovery_cache
    cache_key = _discovery_cache_key()
    if _discovery_cache is not None and _discovery_cache[0] == cache_key:
        return list(_discovery_cache[1])
    seen: dict[str, BrandPack] = {}
    for _src, root in _discovery_sources():
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            tokens = d / "tokens.json"
            design = d / "DESIGN.md"
            if not (tokens.is_file() or design.is_file()):
                continue
            if d.name in seen:
                continue
            image_provider_config: dict | None = None
            # Spec: `BrandPack.image_provider_config` is read directly from
            # the brand's own tokens.json (packs are self-contained). On a
            # *survivable* failure (malformed JSON, schema-validation error)
            # fall back to None AND emit a RuntimeWarning so the operator
            # sees why the field is empty — silent swallow makes a
            # misconfigured brand indistinguishable from one with no provider
            # declared. Genuine bugs / aborts (KeyboardInterrupt, SystemExit,
            # MemoryError, RecursionError) intentionally propagate.
            try:
                resolved = load_tokens(d)
                ip = resolved.raw.get("$image_provider") if isinstance(resolved.raw, dict) else None
                if isinstance(ip, dict) and "kind" in ip:
                    image_provider_config = ip
            except (OSError, ValueError, JSONDecodeError) as exc:
                warnings.warn(
                    f"discover_brands: skipping $image_provider for brand "
                    f"{d.name!r}: {type(exc).__name__}: {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                image_provider_config = None
            # Build a BrandPack. When tokens.json is absent (DESIGN.md-only brands)
            # or malformed, fall back to an empty-tokens pack so discovery
            # doesn't crash — same survivable-failure philosophy as above.
            try:
                if tokens.is_file():
                    pack = BrandPack.load(d)
                else:
                    pack = BrandPack(root=d, tokens={}, tokens_hash="")
            except (OSError, ValueError, JSONDecodeError):
                pack = BrandPack(root=d, tokens={}, tokens_hash="")
            # Inject the extends-resolved image_provider_config (computed above by
            # the load_tokens extends-walk). This is set here rather than in
            # BrandPack.load because the extends-resolution logic lives in
            # brand_discovery and we don't want to duplicate it.
            pack._image_provider_config = image_provider_config
            seen[d.name] = pack
    _discovery_cache = (cache_key, list(seen.values()))
    return list(seen.values())


def find_brand(name: str) -> BrandPack:
    """Return the brand with the given name, or raise ValueError with a
    diagnostic listing every searched path and every brand actually found.

    This is the function `/deck --brand <name>` should call — its error
    message tells the user exactly what to fix.

    Returns a :class:`~feinschmiede.brand.BrandPack` (previously returned the legacy
    ``Brand`` dataclass — all attributes used by callers are present on
    ``BrandPack`` with the same names).
    """
    brands = discover_brands()
    for b in brands:
        if b.name == name:
            return b
    available = sorted(b.name for b in brands)
    searched_lines = []
    for src, root in _discovery_sources():
        marker = "✓" if root.is_dir() else "·"
        searched_lines.append(f"  {marker} [{src}] {root}")
    searched = "\n".join(searched_lines)
    raise ValueError(
        f"brand '{name}' not found.\n"
        f"available brands: {', '.join(available) or '(none)'}\n"
        f"searched paths:\n{searched}\n"
        f"to add a brand path, set FEINSCHLIFF_BRAND_PATH=/abs/path[:/another]"
    )

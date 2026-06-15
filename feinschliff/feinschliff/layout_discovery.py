"""Locate toolkit layout packs across bundled, plugin-installed, env, and user-local paths."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Layout:
    name: str          # stem of the .slide.dsl file, e.g. "title-orange"
    path: Path         # absolute path to the .slide.dsl file


@dataclass
class LayoutSource:
    kind: str          # "bundled" | "plugin" | "env" | "cwd-dev" | "user"
    path: Path         # the layouts/ directory


def _bundled_layouts_root() -> Path:
    """The layouts/ directory shipped inside this plugin (now brand-local)."""
    return Path(__file__).resolve().parents[1] / "brands" / "feinschliff" / "layouts"


def _user_layouts_root() -> Path:
    return Path.home() / ".feinschliff" / "layouts"


def _plugin_layouts_roots() -> list[Path]:
    """`layouts/` dirs from installed Claude Code plugins whose parent
    contains "feinschliff" in the name.

    Layouts are toolkit-specific — only plugins whose name (or marketplace name)
    contains "feinschliff" contribute layouts, to prevent unrelated plugins from
    accidentally shadowing toolkit layouts.

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
                if "feinschliff" not in plugin.name and "feinschliff" not in marketplace.name:
                    continue
                layouts = plugin / "layouts"
                if layouts.is_dir():
                    roots.append(layouts)
    for entry in sorted(plugins.iterdir()):
        if entry.name == "marketplaces" or not entry.is_dir():
            continue
        if "feinschliff" not in entry.name:
            continue
        layouts = entry / "layouts"
        if layouts.is_dir():
            roots.append(layouts)
    return roots


def _env_layouts_roots() -> list[Path]:
    raw = os.environ.get("FEINSCHLIFF_LAYOUT_PATH", "")
    return [Path(p) for p in raw.split(os.pathsep) if p]


def _cwd_dev_layouts_roots() -> list[Path]:
    """Walk up from $CWD; if an in-place git checkout of feinschliff exists,
    surface its layouts/. Supports the dev workflow where a layout author edits
    `~/work/feinschliff/feinschliff/brands/feinschliff/layouts/<layout>/` and
    runs scripts that don't sit inside the package.

    The walk stops at the first git boundary so we don't accidentally scan
    the whole home directory.
    """
    out: list[Path] = []
    try:
        cwd = Path.cwd().resolve()
    except FileNotFoundError:
        return out
    for ancestor in [cwd, *cwd.parents]:
        candidate = ancestor / "feinschliff" / "layouts"
        if candidate.is_dir():
            out.append(candidate)
        # Sibling plugin dirs in the same checkout may ship layouts too.
        for plugin_layouts in sorted(ancestor.glob("feinschliff-*/layouts")):
            if plugin_layouts.is_dir():
                out.append(plugin_layouts)
        # Also handle a checkout where the cwd is already inside `feinschliff/`.
        sibling = ancestor / "layouts"
        if (ancestor / "pyproject.toml").is_file() and sibling.is_dir():
            out.append(sibling)
        if (ancestor / ".git").exists():
            break
    return out


def _discovery_sources() -> list[tuple[str, Path]]:
    """Source-tagged list used by both discovery and the not-found error.

    `env` and `cwd-dev` outrank `plugin`: an explicit FEINSCHLIFF_LAYOUT_PATH
    override and the working checkout are both more intentional than an
    ambient installed plugin — a stale marketplace copy of a same-named
    layout must not shadow either.
    """
    items: list[tuple[str, Path]] = [("bundled", _bundled_layouts_root())]
    items.extend(("env", p) for p in _env_layouts_roots())
    items.extend(("cwd-dev", p) for p in _cwd_dev_layouts_roots())
    items.extend(("plugin", p) for p in _plugin_layouts_roots())
    items.append(("user", _user_layouts_root()))
    return items


def discover_layouts() -> list[LayoutSource]:
    """Returns all layout source directories found across all discovery sources, deduped by path.

    Sources scanned, in priority order:
      1. bundled — `layouts/` next to the installed `lib/`
      2. env — directories listed in `FEINSCHLIFF_LAYOUT_PATH` (colon-separated)
      3. plugin — `~/.claude/plugins/.../layouts/` (feinschliff plugins only)
      4. cwd-dev — `feinschliff/brands/feinschliff/layouts/` or similar, reachable by walking up from $CWD
      5. user — `~/.feinschliff/layouts/`
    """
    seen_paths: set[Path] = set()
    sources: list[LayoutSource] = []
    for src, root in _discovery_sources():
        if not root.is_dir():
            continue
        resolved = root.resolve()
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        sources.append(LayoutSource(kind=src, path=root))
    return sources


def all_layout_dirs() -> list[Path]:
    """Return all existing layout directories in priority order."""
    return [src.path for src in discover_layouts()]


def find_layout(name: str) -> Layout | None:
    """Return the layout with the given name (without .slide.dsl suffix), or None.

    Searches all discovery sources in priority order. The first match wins.
    """
    filename = f"{name}.slide.dsl"
    for src in discover_layouts():
        candidate = src.path / filename
        if candidate.is_file():
            return Layout(name=name, path=candidate)
    return None


_SUFFIX = ".slide.dsl"


def resolve_brand_prefixed(brand_root: Path | None, name: str) -> Path | None:
    """Resolve a ``<brand>-<stem>`` layout name against sibling brand packs.

    Brand packs live at ``<packs_root>/<brand>/layouts/<stem>.slide.dsl``.
    When a plan references ``bsh-slide-25`` from inside the ``bosch`` brand,
    this helper walks to ``bsh``'s sibling ``layouts/`` directory and looks
    up the bare stem there. Returns ``None`` when *brand_root* is missing,
    *name* has no ``-`` separator, the prefix does not match a sibling
    directory, or the resolved file is absent.

    The split is greedy on the **leftmost** ``-`` so brand names without
    a ``-`` work (e.g. ``bsh-slide-25`` → ``bsh`` / ``slide-25``). Brand
    names containing ``-`` (``gs-ramspau-slide-01``) are resolved by
    falling through to the first prefix that names a sibling on disk.
    """
    if brand_root is None or "-" not in name:
        return None
    packs_root = brand_root.parent
    parts = name.split("-")
    # Try increasingly long prefixes so multi-word brand names match.
    for split in range(1, len(parts)):
        prefix = "-".join(parts[:split])
        stem = "-".join(parts[split:])
        candidate = packs_root / prefix / "layouts" / f"{stem}{_SUFFIX}"
        if candidate.is_file():
            return candidate
    return None


# One-shot per (name, winner-path) so a long-running process doesn't
# re-warn every time the picker rebuilds its profile table.
_WARNED_COLLISIONS: set[tuple[str, str]] = set()


def discover_layout_paths() -> dict[str, Path]:
    """Map every discoverable layout name to its ``.slide.dsl`` path.

    Scans all discovery sources in priority order; the first source to
    provide a given name wins (same precedence as :func:`find_layout`).

    Emits a one-line ``layout-discovery: shadowed`` warning to stderr the
    first time a name appears in more than one source — the picker's pool
    silently uses the priority-winner, which is the canonical source of
    "slide1 overriding slide1" surprises across an extension-pack stack.
    Suppress with ``FEINSCHLIFF_QUIET_LAYOUT_SHADOW=1``.

    This is the picker's universe: the layout-affinity profiles are built
    from exactly this set, so a layout on disk can never be unpickable.
    """
    paths: dict[str, Path] = {}
    shadowed_by: dict[str, list[Path]] = {}
    for src in discover_layouts():
        for candidate in sorted(src.path.glob(f"*{_SUFFIX}")):
            name = candidate.name[: -len(_SUFFIX)]
            if name in paths:
                shadowed_by.setdefault(name, []).append(candidate)
            else:
                paths[name] = candidate
    if shadowed_by and not os.environ.get("FEINSCHLIFF_QUIET_LAYOUT_SHADOW"):
        for name, losers in shadowed_by.items():
            winner = paths[name]
            key = (name, str(winner))
            if key in _WARNED_COLLISIONS:
                continue
            _WARNED_COLLISIONS.add(key)
            losers_str = ", ".join(str(p) for p in losers)
            print(
                f"layout-discovery: '{name}' appears in {len(losers) + 1} "
                f"sources; using {winner} (shadowed: {losers_str}). "
                f"Suppress with FEINSCHLIFF_QUIET_LAYOUT_SHADOW=1.",
                file=sys.stderr,
            )
    return paths

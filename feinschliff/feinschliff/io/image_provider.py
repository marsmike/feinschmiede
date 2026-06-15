"""Pluggable image-provider framework.

Build-time picture resolution backed by an interchangeable registry of
providers (Unsplash, internal mirrors, custom adapters). Brand packs
declare their preferred provider in ``tokens.json`` under
``$image_provider``; the picture DSL primitive grows a ``query:`` keyword
which the active provider resolves at emit time.

This module is intentionally tiny — only the ABC, the registry, and the
discovery loop live here. Built-in providers ship in :mod:`lib.providers`
and out-of-tree providers live in plugins under
``~/.claude/plugins/.../feinschliff_providers/``.

Discovery mirrors :mod:`feinschmiede.brand_discovery`: bundled → plugin → env →
cwd-dev → user. Each ``.py`` file under those roots is imported as a
synthetic module so registrations land in :data:`_REGISTRY` via the
``@register_provider`` decorator. Broken plugins are logged and skipped —
one bad provider must not block unrelated builds.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import traceback
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from feinschliff.pipeline_log import log_event

if TYPE_CHECKING:
    from feinschliff.defects import Defect


@dataclass(frozen=True)
class ImageHit:
    """One result row from a :meth:`ImageProvider.search` call.

    ``url`` is either ``http(s)://`` or ``file://`` — the picture-emit
    step materialises both into a local :class:`Path` before handing to
    ``python-pptx``.
    """
    url: str
    license: str          # e.g. "Unsplash License", "internal-brand"
    attribution: str      # human-readable credit line
    width: int | None     # pixels, when known
    height: int | None
    mime: str             # "image/jpeg", "image/svg+xml", ...


class ImageProvider(ABC):
    """Base class for build-time picture providers.

    Subclasses set the class-level ``name`` and implement :meth:`search`.
    They register themselves via the :func:`register_provider` decorator
    so the pipeline can look them up by name at build time.
    """

    name: ClassVar[str]

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        count: int = 1,
        hints: dict | None = None,
    ) -> list[ImageHit]:
        """Return up to ``count`` ranked hits for the query string.

        ``hints`` is reserved for future slot-aware nudges (aspect_ratio,
        dominant_color, slot_role). Implementations may ignore it.
        Returns ``[]`` on no match — never raises for misses.
        """

    def preflight(
        self,
        image_path: Path,
        brand_palette_hex: list[str],
        slot_aspect: float,
        *,
        slide_index: int,
    ) -> list["Defect"]:
        """Run image preflight checks before insertion.

        Default no-op implementation: returns an empty list so providers
        that do not override this method never emit preflight defects.
        Subclasses may override to call :func:`feinschliff.io.image_preflight.preflight_image`
        and return any emitted :class:`~feinschliff.defects.Defect` records.

        Parameters
        ----------
        image_path:
            Local path to the downloaded / resolved image file.
        brand_palette_hex:
            Brand colour tokens as ``#rrggbb`` hex strings.
        slot_aspect:
            Target slot aspect ratio (width / height).
        slide_index:
            Slide index, forwarded into any emitted defect records.

        Returns
        -------
        list[Defect]
            Zero or more WARN-level defects. Never raises.
        """
        return []


# Global registry. Populated by :func:`register_provider` (via the
# decorator) and read by :func:`get_provider`.
_REGISTRY: dict[str, type[ImageProvider]] = {}

# Idempotency flag for :func:`discover_providers`.
_DISCOVERED: bool = False


def register_provider(cls: type[ImageProvider]) -> type[ImageProvider]:
    """Class decorator: register ``cls`` under ``cls.name`` in the global registry.

    Raises :class:`ValueError` if a provider with that name is already
    registered — collisions are programming errors, not silent overrides.
    """
    name = getattr(cls, "name", None)
    if not name:
        raise ValueError(
            f"{cls.__name__} must set a non-empty class-level `name` "
            f"before @register_provider"
        )
    if name in _REGISTRY:
        existing = _REGISTRY[name]
        # Same class re-imported via different module paths (e.g. direct
        # import + the auto-discovery alias `feinschliff_providers._auto.*`)
        # is a no-op, not a collision. Compare by class identity AND by
        # qualname so the test "same class, two paths" recognises itself.
        if existing is cls or existing.__qualname__ == cls.__qualname__:
            return cls
        raise ValueError(
            f"image provider name {name!r} is already registered to "
            f"{existing.__module__}.{existing.__name__}; "
            f"cannot re-register {cls.__module__}.{cls.__name__}"
        )
    _REGISTRY[name] = cls
    return cls


def get_provider(name: str, config: dict | None = None) -> ImageProvider:
    """Look up a registered provider and instantiate it with ``config``.

    Raises :class:`KeyError` with a diagnostic message listing every
    known provider name when the lookup misses, so brand-pack authors
    can fix their ``tokens.json`` typos quickly.
    """
    cls = _REGISTRY.get(name)
    if cls is None:
        available = sorted(_REGISTRY.keys())
        listing = ", ".join(available) if available else "(none registered)"
        raise KeyError(
            f"image provider {name!r} not registered. "
            f"known providers: {listing}. "
            f"call discover_providers() first, or check $image_provider.kind "
            f"in your brand's tokens.json."
        )
    return cls(config)


# ---------------------------------------------------------------------------
# Discovery — mirrors feinschmiede.brand_discovery's directory-scan idiom.
# ---------------------------------------------------------------------------


def _bundled_providers_root() -> Path:
    """The ``providers/`` directory shipped inside this plugin."""
    return Path(__file__).resolve().parent / "providers"


def _user_providers_root() -> Path:
    return Path.home() / ".feinschliff" / "providers"


def _plugin_providers_roots() -> list[Path]:
    """``feinschliff_providers/`` dirs from installed Claude Code plugins.

    Modern plugins land under
    ``~/.claude/plugins/marketplaces/{marketplace}/{plugin}/``; sideloaded
    plugins occasionally land directly under
    ``~/.claude/plugins/{plugin}/``. Both layouts are supported.
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
                providers = plugin / "feinschliff_providers"
                if providers.is_dir():
                    roots.append(providers)
    for entry in sorted(plugins.iterdir()):
        if entry.name == "marketplaces" or not entry.is_dir():
            continue
        providers = entry / "feinschliff_providers"
        if providers.is_dir():
            roots.append(providers)
    return roots


def _env_providers_roots() -> list[Path]:
    raw = os.environ.get("FEINSCHLIFF_PROVIDER_PATH", "")
    return [Path(p) for p in raw.split(os.pathsep) if p]


def _cwd_dev_providers_roots() -> list[Path]:
    """Walk up from ``$CWD``; if an in-place git checkout of feinschliff
    exists, surface its ``feinschliff_providers/`` directory.

    The walk stops at the first git boundary so we don't accidentally
    scan the whole home directory.
    """
    out: list[Path] = []
    try:
        cwd = Path.cwd().resolve()
    except FileNotFoundError:
        return out
    for ancestor in [cwd, *cwd.parents]:
        candidate = ancestor / "feinschliff" / "feinschliff_providers"
        if candidate.is_dir():
            out.append(candidate)
        sibling = ancestor / "feinschliff_providers"
        if (ancestor / "pyproject.toml").is_file() and sibling.is_dir():
            out.append(sibling)
        if (ancestor / ".git").exists():
            break
    return out


def _provider_search_paths() -> list[tuple[str, Path]]:
    """Source-tagged list of provider directories, in discovery order.

    `env` and `cwd-dev` outrank `plugin`: an explicit
    FEINSCHLIFF_PROVIDER_PATH override and the working checkout are both
    more intentional than an ambient installed plugin.
    """
    items: list[tuple[str, Path]] = [("bundled", _bundled_providers_root())]
    items.extend(("env", p) for p in _env_providers_roots())
    items.extend(("cwd-dev", p) for p in _cwd_dev_providers_roots())
    items.extend(("plugin", p) for p in _plugin_providers_roots())
    items.append(("user", _user_providers_root()))
    return items


def _plugin_label_for(root: Path) -> str:
    """Best-effort plugin name for the synthetic module path.

    Most provider roots end in ``feinschliff_providers`` — in that case
    the parent directory name is the plugin name. Otherwise fall back to
    the root's own name so the synthetic module name stays stable.

    A short hash of the absolute parent path is appended so two roots
    that happen to share a directory name (e.g. two different
    ``providers/`` dirs from different sources) don't alias into the
    same key in :data:`sys.modules`. The readable slug stays first so
    debug output remains scannable.
    """
    try:
        parent = root.parent.resolve()
    except OSError:
        parent = root.parent
    parent_hash = hashlib.sha1(str(parent).encode("utf-8")).hexdigest()[:8]
    if root.name == "feinschliff_providers":
        return f"{root.parent.name or 'anon'}_{parent_hash}"
    return f"{root.name or 'anon'}_{parent_hash}"


def discover_providers() -> None:
    """Scan plugin dirs for ``*.py`` and import each one.

    Idempotent — safe to call multiple times; subsequent calls are no-ops
    once the first scan has run. Import errors are logged via
    :func:`lib.pipeline_log.log_event` and skipped; one broken plugin
    must not block unrelated builds.

    The five sources below are scanned in the order listed. Providers
    register by name and **first-write-wins**: once a name is in the
    registry, a later source registering the same name raises
    :class:`ValueError` (swallowed by the broad discovery ``except``)
    and the later definition is ignored. Later sources can therefore
    only **add** new names — bundled providers are canonical, plugins
    extend rather than override.

    Sources, scanned in order:
      1. bundled  — ``lib/providers/``
      2. plugin   — ``~/.claude/plugins/.../feinschliff_providers/``
      3. env      — ``FEINSCHLIFF_PROVIDER_PATH`` (os.pathsep list)
      4. cwd-dev  — walk-up from ``$CWD`` until a ``.git`` boundary
      5. user     — ``~/.feinschliff/providers/``
    """
    global _DISCOVERED
    if _DISCOVERED:
        return
    # Set the flag *before* the scan so a callback that re-enters this
    # function (e.g. a provider module that imports something that calls
    # back in) cannot recurse forever.
    _DISCOVERED = True

    for source, root in _provider_search_paths():
        if not root.is_dir():
            continue
        plugin_label = _plugin_label_for(root)
        for path in sorted(root.iterdir()):
            if not path.is_file() or path.suffix != ".py":
                continue
            if path.name == "__init__.py":
                continue
            module_name = f"feinschliff_providers._auto.{plugin_label}_{path.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"no loader for {path}")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            except Exception as exc:  # noqa: BLE001 — broad on purpose
                # Remove the half-loaded module so a later retry can
                # start clean if the underlying issue is fixed.
                sys.modules.pop(module_name, None)
                # Discovery has no deck context — pass deck_dir=None so
                # the event is recorded in-memory only (returned dict)
                # rather than polluting $CWD with a stray timing.jsonl.
                # The return value is intentionally discarded; the call
                # is retained so a future caller with a real deck_dir
                # gets the structured record for free without another
                # code change.
                log_event(
                    None,
                    "image_provider:discover",
                    "fail",
                    source=source,
                    path=str(path),
                    module=module_name,
                    error=str(exc)[:200],
                    traceback=traceback.format_exc(limit=4),
                )
                # log_event is a no-op when deck_dir is None, so the
                # JSONL record never lands anywhere observable. Emit a
                # RuntimeWarning as well so the operator gets a visible
                # signal — without this, a broken plugin vanishes and
                # later resurfaces as a confusing "unknown provider"
                # KeyError far from the actual cause.
                warnings.warn(
                    (
                        f"image_provider discovery skipped a broken plugin "
                        f"[source={source}] {path} "
                        f"(module={module_name}): {exc!r}"
                    ),
                    RuntimeWarning,
                    stacklevel=2,
                )


__all__ = [
    "ImageHit",
    "ImageProvider",
    "discover_providers",
    "get_provider",
    "register_provider",
]

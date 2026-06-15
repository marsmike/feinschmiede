"""Layout discovery — compatibility stub.

The DSL-era discovery functions have been replaced by the master-template
catalog (layouts.yaml). This module is kept as a thin stub so:

1. ``feinschliff.deck.picker`` can still import ``find_layout`` and
   ``resolve_brand_prefixed`` (tests monkeypatch these).
2. Existing tests that import ``Layout`` still work.

All functions return None / empty in the default stub state. Brand packs
that still ship ``.slide.dsl`` layouts under ``brands/<id>/layouts/`` are
discovered directly in :func:`feinschliff.deck.picker._resolve_layout_path`
by path glob — no central registry needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Layout:
    """A discovered layout entry."""
    name: str
    path: Path


def find_layout(name: str) -> Layout | None:
    """Return a Layout for *name*, or None when not found.

    In the stub: always returns None. Override at runtime via monkeypatch
    in tests, or replace with real discovery when needed.
    """
    return None


def resolve_brand_prefixed(active_brand_dir: Path, name: str) -> Path | None:
    """Resolve a ``<brand>-<stem>`` layout name against sibling brand packs.

    *active_brand_dir* is the active brand's root directory (e.g.
    ``brands/globex``). Sibling brands are looked up under its parent
    (``brands/``), trying increasingly long prefix splits on ``-``.

    Returns the resolved path, or None when no match is found.
    """
    brands_dir = active_brand_dir.parent
    parts = name.split("-")
    for i in range(len(parts) - 1, 0, -1):
        prefix = "-".join(parts[:i])
        stem = "-".join(parts[i:])
        candidate = brands_dir / prefix / "layouts" / f"{stem}.slide.dsl"
        if candidate.is_file():
            return candidate
    return None


def discover_layout_paths() -> dict[str, Path]:
    """Return {name: path} for all discovered toolkit layouts.

    Stub: returns empty dict. The master-template catalog replaces this.
    """
    return {}


def all_layout_dirs() -> list[Path]:
    """Return all registered layout directories.

    Stub: returns empty list.
    """
    return []

"""Shared brand-pack helpers used by render.py, catalog.py, and clone_plan.py."""
from __future__ import annotations

from pathlib import Path


def norm(name: str) -> str:
    """Normalize layout / placeholder names for tolerant lookup.

    Brand packs ship layout names with quirks the source designer typed —
    BSH puts NBSP between words (`Title\\xa0and Picture`), Bosch leaves a
    trailing space (`Title horizontal `). Users typing the clean name
    should still resolve to the layout.
    """
    return name.replace("\xa0", " ").strip()


def master_path(brand_pack: Path) -> Path:
    """Locate the on-disk master template for a brand pack.

    Two shapes are accepted, in order:
      1. `<brand_pack>/master.pptx`        — the feinschliff convention
      2. `<brand_pack>/master/master.pptx` — the abzug convention (BSH/Bosch)
    """
    brand_pack = Path(brand_pack)
    flat = brand_pack / "master.pptx"
    if flat.exists():
        return flat
    return brand_pack / "master" / "master.pptx"


def index_layouts(prs) -> dict:
    """Build a `{normalized_name: layout}` map. Raise on collisions so a brand
    pack with two layouts that normalize to the same name fails loud instead
    of silently dispatching to whichever one wins the dict-overwrite race."""
    index: dict = {}
    for layout in prs.slide_layouts:
        key = norm(layout.name)
        if key in index:
            raise ValueError(
                f"layout name collision after normalization: {key!r} "
                f"(from {index[key].name!r} and {layout.name!r})"
            )
        index[key] = layout
    return index

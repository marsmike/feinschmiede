"""Shared brand-pack helpers used by render.py, catalog.py, and clone_plan.py."""
from __future__ import annotations

from pathlib import Path


def norm(name: str) -> str:
    """Normalize layout / placeholder names for tolerant lookup.

    Brand packs ship layout names with typographic quirks the source
    designer typed — non-breaking space (NBSP) between words, trailing
    whitespace, and the like. Users typing the clean name should still
    resolve to the layout the master actually contains.
    """
    return name.replace("\xa0", " ").strip()


def master_path(brand_pack: Path) -> Path:
    """Locate the on-disk master template for a brand pack.

    Three shapes are accepted, in order:
      1. `<brand_pack>/master.pptx`        — the feinschliff convention.
      2. `<brand_pack>/master/master.pptx` — historical (abzug) convention.
      3. `<brand_pack>/master.pptx.ref`    — a text file holding a path to
         the actual binary. Used by corporate / gallery packs whose master
         file lives outside the repo (e.g. a local asset directory) so the
         binary never needs to be checked in.
    """
    brand_pack = Path(brand_pack)
    for candidate in (brand_pack / "master.pptx", brand_pack / "master" / "master.pptx"):
        if candidate.exists():
            return candidate

    ref = brand_pack / "master.pptx.ref"
    if ref.exists():
        target = Path(ref.read_text().strip()).expanduser()
        if not target.exists():
            raise FileNotFoundError(
                f"master.pptx.ref points to {target}, which does not exist. "
                "Materialize the binary at that path (the pack is expected to "
                "live in a local asset directory, not in this repo)."
            )
        return target

    raise FileNotFoundError(f"no master.pptx (or .ref) found for brand pack {brand_pack}")


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

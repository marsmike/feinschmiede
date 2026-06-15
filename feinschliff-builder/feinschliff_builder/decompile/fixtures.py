"""Derive a content-YAML fixture from a slotified ``.slide.dsl``.

After ``slotify``, every layout's frontmatter declares its slot vocabulary
under ``slots:`` along with a ``default`` literal pulled from the source
PPTX. The renderer's content YAML is just a flat ``{slot: value}`` dict, so
the fixture for a freshly slotified layout is mechanical to produce — the
slot block already contains every key the layout binds and a sensible
literal for each one.

Used by:

- ``feinschliff-builder slotify`` — emits a fixture next to the final DSL,
  so every newly authored brand pack ships a brand-scoped fixture for
  every layout the slot pass touched.
- ``feinschliff-builder brand derive-fixtures`` — backfill subcommand for
  brand packs slotified before this module existed.

The renderer (`feinschliff-builder/scripts/render_brand_atlas.py`) then
picks up the brand-override fixture under
``brands/<brand>/tests/fixtures/layouts/<id>.yaml`` without ever falling
back to the shared toolkit set — keeping each brand's slot vocabulary
self-contained.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from feinschliff.dsl.parser import split_frontmatter


def derive_fixture(dsl_text: str) -> dict[str, Any]:
    """Return ``{slot_name: default_literal}`` for every slot declared in
    *dsl_text*'s frontmatter.

    Returns an empty dict when the DSL has no frontmatter, no ``slots:``
    block, or only slots without a ``default`` entry. Slot keys are emitted
    in the order they appear in the frontmatter so the fixture is stable
    across re-runs.
    """
    fm_text, _ = split_frontmatter(dsl_text)
    if not fm_text:
        return {}
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return {}
    slots = fm.get("slots") or {}
    if not isinstance(slots, dict):
        return {}
    out: dict[str, Any] = {}
    for name, meta in slots.items():
        if not isinstance(meta, dict):
            continue
        if "default" not in meta:
            continue
        out[name] = meta["default"]
    return out


def emit_fixture(dsl_path: Path, fixtures_dir: Path) -> Path | None:
    """Write the derived fixture for *dsl_path* into *fixtures_dir*.

    Returns the written path, or ``None`` when no fixture could be derived
    (DSL has no slot defaults — nothing to bind, nothing to write).
    """
    fixture = derive_fixture(dsl_path.read_text(encoding="utf-8"))
    if not fixture:
        return None
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    stem = dsl_path.name.removesuffix(".slide.dsl")
    out = fixtures_dir / f"{stem}.yaml"
    out.write_text(
        yaml.safe_dump(fixture, sort_keys=False, allow_unicode=True,
                       default_flow_style=False),
        encoding="utf-8",
    )
    return out

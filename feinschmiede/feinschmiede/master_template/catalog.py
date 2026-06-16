"""Brand-pack catalog: layouts.yaml + snippets.yaml + master pptx resolution.

A brand pack ships:
  master.pptx (or master.pptx.ref → absolute path)
  layouts.yaml — { layouts: [ { name, role?, placeholders: [...], hero_image? } ] }
  snippets.yaml (optional) — { snippets: [ { id, source_idx, intent?, anchors? } ] }
  source_deck.pptx.ref (optional) — different deck for cloning; defaults to master
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PlaceholderSchema:
    idx: int
    role: str | None = None
    type: str | None = None
    char_budget: int | None = None
    accepts: tuple[str, ...] = ()


@dataclass(frozen=True)
class LayoutEntry:
    name: str
    role: str | None = None
    placeholders: tuple[PlaceholderSchema, ...] = ()
    hero_image_bbox_emu: tuple[int, int, int, int] | None = None


@dataclass(frozen=True)
class SnippetEntry:
    id: str
    source_idx: int
    intent: str | None = None
    anchors: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Catalog:
    brand_pack: Path
    master_pptx: Path
    source_deck: Path
    layouts: dict[str, LayoutEntry]
    snippets: dict[str, SnippetEntry]
    master_theme: str | None = None  # theme the master.pptx was rendered with


def load_catalog(brand_pack: Path) -> Catalog:
    brand_pack = Path(brand_pack)
    master_pptx = _resolve_ref(brand_pack, "master.pptx")
    source_deck = _resolve_ref(brand_pack, "source_deck.pptx", default=master_pptx)

    layouts_doc = _load_yaml(brand_pack / "layouts.yaml")
    layouts = {e.name: e for e in (_parse_layout(d) for d in layouts_doc.get("layouts", []))}

    snippets_path = brand_pack / "snippets.yaml"
    snippets_doc = _load_yaml(snippets_path) if snippets_path.exists() else {}
    snippets = {e.id: e for e in (_parse_snippet(d) for d in snippets_doc.get("snippets", []))}

    return Catalog(
        brand_pack=brand_pack,
        master_pptx=master_pptx,
        source_deck=source_deck,
        layouts=layouts,
        snippets=snippets,
        master_theme=layouts_doc.get("master_theme") or layouts_doc.get("$master_theme"),
    )


def _resolve_ref(brand_pack: Path, name: str, *, default: Path | None = None) -> Path:
    direct = brand_pack / name
    if direct.exists():
        return direct
    ref = brand_pack / f"{name}.ref"
    if ref.exists():
        target = Path(ref.read_text().strip()).expanduser()
        if not target.is_absolute():
            target = (brand_pack / target).resolve()
        return target
    if default is not None:
        return default
    raise FileNotFoundError(f"{name} (or {name}.ref) not found in {brand_pack}")


def _load_yaml(path: Path) -> dict:
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def _normalize_name(name: str) -> str:
    """Strip ASCII whitespace + NBSP — PowerPoint master layout names
    frequently ship with trailing U+00A0 which str.strip() doesn't catch.
    Mirrored in fill_plan._normalize and clone_plan._normalize."""
    return name.strip().strip(" ").strip()


def _parse_layout(d: dict) -> LayoutEntry:
    hero = d.get("hero_image")
    hero_bbox = tuple(hero["bbox_emu"]) if hero and "bbox_emu" in hero else None
    return LayoutEntry(
        name=_normalize_name(d["name"]),
        role=d.get("role"),
        placeholders=tuple(
            PlaceholderSchema(
                idx=p["idx"],
                role=p.get("role"),
                type=p.get("type"),
                char_budget=p.get("char_budget"),
                accepts=tuple(p.get("accepts", [])),
            )
            for p in d.get("placeholders", [])
        ),
        hero_image_bbox_emu=hero_bbox,
    )


def _parse_snippet(d: dict) -> SnippetEntry:
    return SnippetEntry(
        id=d["id"],
        source_idx=d["source_idx"],
        intent=d.get("intent"),
        anchors=d.get("anchors", {}),
    )

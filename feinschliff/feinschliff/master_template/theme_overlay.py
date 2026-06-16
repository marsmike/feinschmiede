"""Overlay a color theme onto a master.pptx without authoring a new file.

A theme JSON names a subset of the 12 PowerPoint scheme color slots
(`dk1`, `lt1`, `dk2`, `lt2`, `accent1..6`, `hlink`, `folHlink`) and
gives each a hex value. `apply_theme` mutates the in-memory
Presentation's `theme1.xml` `<a:clrScheme>` block so any element bound
to a scheme color renders in the overlaid palette. The master file on
disk is never touched.

Theme JSON shape:

    {
        "$theme_for": "feinschliff",   # informational only
        "scheme": {
            "accent1": "#88C0D0",
            "dk1":     "#2E3440",
            "lt1":     "#ECEFF4",
            "...":     "..."
        }
    }

Keys outside `scheme` are ignored. Slot names outside the 12 standard
slots are ignored. Hex values may be `#RRGGBB` or `RRGGBB`.
"""
from __future__ import annotations

import json
from pathlib import Path

from lxml import etree

_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_SCHEME_SLOTS = {"dk1", "lt1", "dk2", "lt2",
                 "accent1", "accent2", "accent3", "accent4", "accent5", "accent6",
                 "hlink", "folHlink"}


def _theme_parts(prs):
    """Yield every theme part reachable from a slide master.

    Brand packs may carry multiple slide masters (a corporate pack with a
    light + dark master, say). Each carries its own theme rel; an overlay
    must patch them all, otherwise layouts owned by master[1..N] render in
    the original palette while master[0]'s layouts render in the overlaid
    one — a silent visual split.
    """
    rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"
    seen: set[int] = set()
    for master in prs.slide_masters:
        part = master.part.part_related_by(rel_type)
        if id(part) not in seen:
            seen.add(id(part))
            yield part


def _patch_clr(slot_el, hex_value: str) -> None:
    """Replace `slot_el`'s child color element with a fresh `<a:srgbClr>`."""
    for child in list(slot_el):
        slot_el.remove(child)
    srgb = etree.SubElement(slot_el, f"{{{_A_NS}}}srgbClr")
    srgb.set("val", hex_value.lstrip("#").upper())


def apply_theme(prs, theme: Path | dict) -> None:
    """Mutate `prs` in place: patch its scheme colors from `theme`.

    `theme` is either a Path to a JSON file or a dict already loaded.
    """
    spec = json.loads(Path(theme).read_text()) if isinstance(theme, (str, Path)) else theme
    scheme = spec.get("scheme") or {}
    if not scheme:
        return

    for part in _theme_parts(prs):
        root = etree.fromstring(part.blob)
        clr_scheme = root.find(f".//{{{_A_NS}}}clrScheme")
        if clr_scheme is None:
            continue

        for slot_el in clr_scheme:
            slot_name = etree.QName(slot_el).localname
            if slot_name in _SCHEME_SLOTS and slot_name in scheme:
                _patch_clr(slot_el, scheme[slot_name])

        part._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

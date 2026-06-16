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
_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
_MIN_CONTRAST = 3.0  # WCAG ratio below which run text on its fill is illegible
# Order matters for recolor: when two slots share a source hex (e.g. a brand
# that paints accent1 and accent5 the same), the earlier slot wins the mapping.
_SCHEME_SLOT_ORDER = ["dk1", "lt1", "dk2", "lt2",
                      "accent1", "accent2", "accent3", "accent4", "accent5", "accent6",
                      "hlink", "folHlink"]
_SCHEME_SLOTS = set(_SCHEME_SLOT_ORDER)


def _as_scheme(theme: Path | dict) -> dict[str, str]:
    """Load a theme spec to `{slot: RRGGBB}` (uppercase, no `#`), slots only."""
    spec = json.loads(Path(theme).read_text()) if isinstance(theme, (str, Path)) else theme
    scheme = spec.get("scheme") or {}
    return {k: v.lstrip("#").upper() for k, v in scheme.items() if k in _SCHEME_SLOTS}


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


def base_palette(brand_pack: Path) -> Path | None:
    """The palette a brand's slides were authored in — the recolor source.

    Convention: `themes/default/scheme.json` is the identity theme, declaring
    each slot's hex exactly as painted on the slides. Returns None when a pack
    ships no such file (recoloring is then skipped; `clrScheme` patch only)."""
    p = Path(brand_pack) / "themes" / "default" / "scheme.json"
    return p if p.exists() else None


def _recolor_explicit(prs, recolor_from: Path | dict, theme: Path | dict) -> None:
    """Rewrite hardcoded `<a:srgbClr val="...">` hexes across slides, layouts
    and masters by mapping the base palette's slot colors to the theme's.

    Patching `clrScheme` alone is inert when a brand's designer painted shapes
    with explicit hex colors instead of `schemeClr` references — which is the
    common case for decks authored in PowerPoint. `recolor_from` names the
    palette the master was authored in (each slot's hex as it appears on the
    slides); this swaps those exact hexes for the theme's, in one pass so a
    value isn't re-substituted by a later mapping."""
    src, dst = _as_scheme(recolor_from), _as_scheme(theme)
    cmap: dict[str, str] = {}
    for slot in _SCHEME_SLOT_ORDER:
        if slot in src and slot in dst and src[slot] != dst[slot]:
            cmap.setdefault(src[slot], dst[slot])
    if not cmap:
        return
    tag = f"{{{_A_NS}}}srgbClr"
    parts = [*prs.slides, *prs.slide_layouts, *prs.slide_masters]
    for part in parts:
        for clr in part._element.iter(tag):
            val = clr.get("val")
            if val and val.upper() in cmap:
                clr.set("val", cmap[val.upper()])


def _rel_lum(hex6: str) -> float:
    """WCAG relative luminance of an RRGGBB hex."""
    def chan(c: int) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex6[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_rel_lum(a), _rel_lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


_SPPR = f"{{{_P_NS}}}spPr"
_SP = f"{{{_P_NS}}}sp"
_SOLID = f"{{{_A_NS}}}solidFill"
_SRGB = f"{{{_A_NS}}}srgbClr"
_XFRM = f"{{{_A_NS}}}xfrm"
_OFF = f"{{{_A_NS}}}off"
_EXT = f"{{{_A_NS}}}ext"
_RPR_TAGS = {f"{{{_A_NS}}}rPr", f"{{{_A_NS}}}defRPr", f"{{{_A_NS}}}endParaRPr"}


def _shape_fill_hex(sp) -> str:
    """The shape's own solid-fill hex (direct child of spPr, so the line
    color in `<a:ln>` is not mistaken for the fill). '' if none/non-srgb."""
    sppr = sp.find(_SPPR)
    fill = sppr.find(_SOLID) if sppr is not None else None
    clr = fill.find(_SRGB) if fill is not None else None
    return clr.get("val", "").upper() if clr is not None else ""


def _shape_box(sp):
    """`(x, y, cx, cy)` in EMU from the shape's own xfrm, or None if it
    inherits geometry (a placeholder) — those we can't place, so we skip."""
    xfrm = sp.find(f"{_SPPR}/{_XFRM}")
    off = xfrm.find(_OFF) if xfrm is not None else None
    ext = xfrm.find(_EXT) if xfrm is not None else None
    if off is None or ext is None:
        return None
    return (int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy")))


def _run_color_els(sp):
    return [clr for rpr in sp.iter() if rpr.tag in _RPR_TAGS
            for clr in (rpr.find(_SOLID),) if clr is not None
            for clr in (clr.find(_SRGB),) if clr is not None and len(clr.get("val", "")) == 6]


def _fix_contrast(prs, scheme: dict[str, str]) -> None:
    """Restore legibility after recoloring overlapping shapes.

    The recolor maps fills and text by independent slot rules, so a design
    that paints `dk1` text over an `accent1` chip can land light-on-light (or
    dark-on-dark) under a theme where both slots share a polarity. Text and
    its backing block are usually *separate, overlapping* shapes, so this
    walks each slide in z-order: for every text shape it finds the filled
    shape beneath it (its own fill, else the topmost earlier rect whose box
    contains the text's center) and, where a run reads below `_MIN_CONTRAST`
    against that fill, swaps it to whichever foreground (`dk1`/`lt1`) contrasts
    best — the choice the designer would have made."""
    dk, lt = scheme.get("dk1"), scheme.get("lt1")
    if not dk or not lt:
        return
    for part in [*prs.slides, *prs.slide_layouts, *prs.slide_masters]:
        tree = part._element.find(f"{{{_P_NS}}}cSld/{{{_P_NS}}}spTree")
        if tree is None:
            continue
        fills: list[tuple[tuple[int, int, int, int], str]] = []  # (box, hex), z-order
        for sp in tree.findall(_SP):
            box = _shape_box(sp)
            own = _shape_fill_hex(sp)
            runs = _run_color_els(sp)
            if runs:
                bg = own or _bg_under(fills, box)
                if len(bg) == 6:
                    best = dk if _contrast(dk, bg) >= _contrast(lt, bg) else lt
                    for clr in runs:
                        if _contrast(clr.get("val").upper(), bg) < _MIN_CONTRAST:
                            clr.set("val", best)
            if len(own) == 6 and box is not None:
                fills.append((box, own))


def _bg_under(fills, box) -> str:
    """Hex of the topmost (latest z-order) filled rect whose box contains the
    center of `box`; '' if the text floats over no block (i.e. on the paper)."""
    if box is None:
        return ""
    cx, cy = box[0] + box[2] // 2, box[1] + box[3] // 2
    for (fx, fy, fcx, fcy), hex_ in reversed(fills):
        if fx <= cx <= fx + fcx and fy <= cy <= fy + fcy:
            return hex_
    return ""


def _patch_clr(slot_el, hex_value: str) -> None:
    """Replace `slot_el`'s child color element with a fresh `<a:srgbClr>`."""
    for child in list(slot_el):
        slot_el.remove(child)
    srgb = etree.SubElement(slot_el, f"{{{_A_NS}}}srgbClr")
    srgb.set("val", hex_value.lstrip("#").upper())


def apply_theme(prs, theme: Path | dict, *, recolor_from: Path | dict | None = None) -> None:
    """Mutate `prs` in place: repaint it in `theme`'s color scheme.

    Two mechanisms, both needed because real decks mix them:
      * Patch `theme1.xml`'s `clrScheme` so anything bound to a scheme color
        (`schemeClr`) follows the new palette.
      * When `recolor_from` is given (the base palette the master was authored
        in), also swap the explicit `srgbClr` hexes the designer painted
        directly — see `_recolor_explicit`. A follow-up `_fix_contrast` pass
        repairs text that the recolor stranded on a same-polarity fill.
        Without this, decks authored with hardcoded colors ignore the theme
        entirely.

    `theme` / `recolor_from` are each a Path to a JSON file or a loaded dict.
    """
    scheme = _as_scheme(theme)
    if not scheme:
        return

    if recolor_from is not None:
        _recolor_explicit(prs, recolor_from, theme)
        _fix_contrast(prs, scheme)

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

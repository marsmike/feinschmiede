"""Render-time theme overlay: swap srgbClr hex values from the master's
source theme to a target theme, keyed by the role names in `tokens.json`.

Brand pack layout (mirrors the DSL pipeline's convention):
    <brand_pack>/themes/<theme_name>/tokens.json

`tokens.json` carries `{ "color": { <role>: { "$value": "#RRGGBB", ... }, ... } }`.
A swap map is built by intersecting role names across two themes and emitting
the value→value pairs that differ. The cloned slide XML is then walked and
every `<a:srgbClr val="…">` whose value matches the source side is rewritten
to the target side.

Known limitation: a color that's shared by multiple roles (e.g. accent and
chart-series-1 both = gold) gets one swap value, last-write-wins. Brand
authors who care should keep role values distinct.
"""

from __future__ import annotations

import json
from pathlib import Path

from lxml import etree

_A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def load_theme_colors(tokens_path: Path) -> dict[str, str]:
    """Return `{role: "RRGGBB"}` (uppercase, no leading #) from a tokens.json."""
    doc = json.loads(tokens_path.read_text())
    out: dict[str, str] = {}
    for role, spec in (doc.get("color") or {}).items():
        if not isinstance(spec, dict):
            continue
        raw = spec.get("$value")
        if not isinstance(raw, str):
            continue
        hex_val = raw.lstrip("#").upper()
        if len(hex_val) == 6 and all(c in "0123456789ABCDEF" for c in hex_val):
            out[role] = hex_val
    return out


def build_swap(source: dict[str, str], target: dict[str, str]) -> dict[str, str]:
    """Return `{src_hex_upper: tgt_hex_upper}` for roles present in both themes
    where the values differ."""
    swap: dict[str, str] = {}
    for role, src_hex in source.items():
        tgt_hex = target.get(role)
        if tgt_hex and tgt_hex != src_hex:
            swap.setdefault(src_hex, tgt_hex)
    return swap


def recolor_element(element, swap: dict[str, str]) -> int:
    """Walk every `<a:srgbClr val="…">` under `element` and apply `swap`.
    Returns the number of replacements made."""
    if not swap:
        return 0
    count = 0
    for el in element.iter():
        if etree.QName(el).localname != "srgbClr":
            continue
        val = el.get("val")
        if not val:
            continue
        up = val.upper()
        replacement = swap.get(up)
        if replacement and replacement != up:
            el.set("val", replacement)
            count += 1
    return count


def discover_themes(brand_pack: Path) -> dict[str, Path]:
    """Return `{theme_name: tokens.json path}` for every theme dir under
    `<brand_pack>/themes/`. Empty when the brand has no themes/ directory."""
    themes_dir = brand_pack / "themes"
    if not themes_dir.is_dir():
        return {}
    out: dict[str, Path] = {}
    for sub in themes_dir.iterdir():
        tokens = sub / "tokens.json"
        if sub.is_dir() and tokens.exists():
            out[sub.name] = tokens
    return out

"""Theme overlay: srgbClr swap from tokens.json role map."""

from __future__ import annotations

import json
from pathlib import Path

from lxml import etree

from feinschmiede.master_template import (
    build_swap,
    discover_themes,
    load_theme_colors,
    recolor_element,
)


def _write_theme(brand_pack: Path, name: str, colors: dict[str, str]) -> None:
    d = brand_pack / "themes" / name
    d.mkdir(parents=True, exist_ok=True)
    doc = {"color": {role: {"$value": hx, "$description": ""} for role, hx in colors.items()}}
    (d / "tokens.json").write_text(json.dumps(doc))


def test_load_theme_colors_normalizes_to_uppercase_hex(tmp_path):
    _write_theme(tmp_path, "default", {"accent": "#c9a24a", "ink": "#0b1a33"})
    cols = load_theme_colors(tmp_path / "themes/default/tokens.json")
    assert cols == {"accent": "C9A24A", "ink": "0B1A33"}


def test_load_theme_colors_skips_invalid_values(tmp_path):
    _write_theme(tmp_path, "default", {
        "accent": "#C9A24A",
        "broken": "not-a-color",
        "short": "#ABC",
    })
    cols = load_theme_colors(tmp_path / "themes/default/tokens.json")
    assert cols == {"accent": "C9A24A"}


def test_build_swap_returns_value_to_value_per_role(tmp_path):
    src = {"accent": "C9A24A", "ink": "0B1A33", "paper": "FAF8F3"}
    tgt = {"accent": "CC785C", "ink": "141413", "paper": "FAF8F3"}
    swap = build_swap(src, tgt)
    assert swap == {"C9A24A": "CC785C", "0B1A33": "141413"}


def test_build_swap_ignores_roles_only_in_one_theme():
    src = {"accent": "FFFFFF", "extra": "AAAAAA"}
    tgt = {"accent": "000000"}
    assert build_swap(src, tgt) == {"FFFFFF": "000000"}


def test_recolor_element_replaces_matching_srgbclr():
    a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    root = etree.Element(f"{{{a}}}grpSp")
    etree.SubElement(root, f"{{{a}}}srgbClr", val="C9A24A")
    etree.SubElement(root, f"{{{a}}}srgbClr", val="0B1A33")
    etree.SubElement(root, f"{{{a}}}srgbClr", val="FFFFFF")  # not in swap
    count = recolor_element(root, {"C9A24A": "CC785C", "0B1A33": "141413"})
    assert count == 2
    vals = [el.get("val") for el in root.iter(f"{{{a}}}srgbClr")]
    assert vals == ["CC785C", "141413", "FFFFFF"]


def test_recolor_element_handles_lowercase_input():
    a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    root = etree.Element(f"{{{a}}}root")
    etree.SubElement(root, f"{{{a}}}srgbClr", val="c9a24a")
    recolor_element(root, {"C9A24A": "CC785C"})
    assert root[0].get("val") == "CC785C"


def test_discover_themes(tmp_path):
    _write_theme(tmp_path, "default", {"accent": "#C9A24A"})
    _write_theme(tmp_path, "claude", {"accent": "#CC785C"})
    (tmp_path / "themes" / "broken").mkdir()  # no tokens.json — skipped
    found = discover_themes(tmp_path)
    assert set(found) == {"default", "claude"}


def test_discover_themes_no_dir(tmp_path):
    assert discover_themes(tmp_path) == {}

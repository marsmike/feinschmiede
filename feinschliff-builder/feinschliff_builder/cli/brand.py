"""`feinschliff brand …` subcommand router (v2)."""
from __future__ import annotations

import argparse
import json
import sys

from feinschmiede.brand_discovery import discover_brands
from feinschliff.layout_discovery import discover_layout_paths


def register(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="brand_command", required=True)

    p_list = sub.add_parser("list", help="List discovered brand packs")
    p_list.set_defaults(func=cmd_list)

    p_inspect = sub.add_parser("inspect", help="Print v2 inventory for a brand")
    p_inspect.add_argument("name")
    p_inspect.set_defaults(func=cmd_inspect)


def cmd_list(_args) -> int:
    for b in discover_brands():
        markers = []
        if b.tokens_path:
            markers.append("tokens")
        if b.design_path:
            markers.append("design")
        if b.layouts_path:
            markers.append("+layouts")
        if b.compounds_path:
            markers.append("+compounds")
        tag = ",".join(markers) or "?"
        print(f"{b.name}\t{tag}\t{b.root}")
    return 0


def _toolkit_layouts() -> list[str]:
    # Use feinschliff's layout discovery (honours the installed-plugin scan +
    # FEINSCHLIFF_LAYOUT_PATH that the launcher exports) instead of reaching into
    # feinschliff's installed files via __file__ — so brand-inspect works under a
    # real plugin/launcher install, not only a dev checkout.
    return sorted(discover_layout_paths().keys())


def _brand_layouts(brand) -> list[str]:
    if not brand.layouts_path:
        return []
    return sorted(p.stem.replace(".slide", "") for p in brand.layouts_path.glob("*.slide.dsl"))


def _brand_compounds(brand) -> list[str]:
    if not brand.compounds_path:
        return []
    return sorted(p.stem for p in brand.compounds_path.glob("*.dsl"))


def cmd_inspect(args) -> int:
    brand = next((b for b in discover_brands() if b.name == args.name), None)
    if brand is None:
        print(f"brand not found: {args.name}", file=sys.stderr)
        return 1

    print(f"brand: {brand.name}")
    print(f"root:  {brand.root}")

    # Tokens summary.
    if brand.tokens_path:
        try:
            tokens = json.loads(brand.tokens_path.read_text())
            colors = tokens.get("color", {})
            fonts  = tokens.get("font-family", {})
            sizes  = tokens.get("font-size", {})
            print(f"tokens.json: {len(colors)} colors, {len(fonts)} font families, {len(sizes)} sizes")
            asset_sources = tokens.get("asset_sources")
            if asset_sources:
                kinds = [k for k in asset_sources if not k.startswith("$")]
                if kinds:
                    print(f"asset_sources: {', '.join(kinds)}")
        except (OSError, json.JSONDecodeError) as e:
            print(f"tokens.json: unreadable ({e})", file=sys.stderr)
    elif brand.design_path:
        print("DESIGN.md frontmatter only — no separate tokens.json")
    else:
        print("(no tokens.json or DESIGN.md)")

    # Layout inventory.
    inherited = _toolkit_layouts()
    overrides = _brand_layouts(brand)
    inherited_active = [n for n in inherited if n not in overrides]
    brand_only = [n for n in overrides if n not in inherited]
    overridden = [n for n in overrides if n in inherited]
    print(f"layouts: {len(inherited_active) + len(overrides)} "
          f"({len(inherited_active)} inherited, {len(overridden)} overridden, "
          f"{len(brand_only)} brand-only)")
    if overridden:
        print(f"  overrides: {', '.join(overridden)}")
    if brand_only:
        print(f"  brand-only: {', '.join(brand_only)}")

    # Brand compounds.
    bc = _brand_compounds(brand)
    if bc:
        print(f"compounds: {len(bc)} ({', '.join(bc)})")

    return 0

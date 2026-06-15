"""`feinschliff brand …` subcommand router (v2)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from feinschmiede.brand_discovery import discover_brands
from feinschliff.layout_discovery import discover_layout_paths

from feinschliff_builder.decompile.fixtures import emit_fixture


def register(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="brand_command", required=True)

    p_list = sub.add_parser("list", help="List discovered brand packs")
    p_list.set_defaults(func=cmd_list)

    p_inspect = sub.add_parser("inspect", help="Print v2 inventory for a brand")
    p_inspect.add_argument("name")
    p_inspect.set_defaults(func=cmd_inspect)

    p_fixtures = sub.add_parser(
        "derive-fixtures",
        help="Emit a brand-scoped content fixture for every slotified layout "
             "(backfill for packs slotified before fixture emission was wired in)",
    )
    p_fixtures.add_argument("--brand-pack", required=True, type=Path,
                            help="Path to the brand pack directory (e.g. "
                                 "feinschliff-extra/brands/geometric)")
    p_fixtures.add_argument("--force", action="store_true",
                            help="Overwrite existing fixtures")
    p_fixtures.set_defaults(func=cmd_derive_fixtures)


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


def cmd_derive_fixtures(args) -> int:
    """Backfill brand-scoped content fixtures from the slot defaults a prior
    ``slotify`` pass already baked into the layout frontmatter.

    Slotify now emits a fixture per layout as part of its normal output;
    this command exists for brand packs slotified before that wiring was
    added.
    """
    brand_pack: Path = args.brand_pack.resolve()
    layouts_dir = brand_pack / "layouts"
    fixtures_dir = brand_pack / "tests" / "fixtures" / "layouts"
    if not layouts_dir.is_dir():
        print(f"brand derive-fixtures: no layouts/ in {args.brand_pack}",
              file=sys.stderr)
        return 2
    written, skipped_existing, skipped_empty = 0, 0, 0
    for dsl in sorted(layouts_dir.glob("*.slide.dsl")):
        stem = dsl.name.removesuffix(".slide.dsl")
        target = fixtures_dir / f"{stem}.yaml"
        if target.is_file() and not args.force:
            print(f"  skip {stem}: fixture exists (use --force to overwrite)")
            skipped_existing += 1
            continue
        written_path = emit_fixture(dsl, fixtures_dir)
        if written_path is None:
            print(f"  skip {stem}: no slot defaults in frontmatter")
            skipped_empty += 1
            continue
        print(f"  wrote {written_path.relative_to(brand_pack)}")
        written += 1
    print(f"\n{written} fixture(s) written, {skipped_existing} kept, "
          f"{skipped_empty} layout(s) without derivable defaults")
    return 0

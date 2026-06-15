#!/usr/bin/env python3
"""Port curated frontmatter between brand packs after a re-decompile.

Decompile + slotify regenerate the mechanical frontmatter (slots,
element_tree, warnings) but leave the CURATED fields empty. This script
copies them from a reference pack — same pack pre-rebuild, or a previous
template generation — onto the freshly derived layouts:

    description, when_to_use, when_not_to_use, family, family_curated,
    chrome_subject, chrome_note

Layout matching, in order:
  1. an explicit mapping file (`--map curation-map.yaml`: `{to: from}`
     names, e.g. `slide-36: slide-23`);
  2. same file name in both packs.

Convention: keep a `curation-map.yaml` in the pack root whenever the pack
derives from a renamed/reordered template generation (e.g. when a newer
master-template export shifts slide numbers vs the curated version).

Usage:
  uv run python scripts/brand_port_curation.py \\
      --from-pack <reference-pack> --to-pack <fresh-pack> \\
      [--map <to-pack>/curation-map.yaml] [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

PORT_FIELDS = ["description", "when_to_use", "when_not_to_use", "family",
               "family_curated", "chrome_subject", "chrome_note"]


def _split(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if m is None:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def port_curation(from_pack: Path, to_pack: Path,
                  mapping: dict[str, str] | None = None,
                  dry_run: bool = False) -> int:
    """Returns the number of layouts that received curated fields."""
    mapping = mapping or {}
    ported = 0
    for to_path in sorted((to_pack / "layouts").glob("*.slide.dsl")):
        name = to_path.name[: -len(".slide.dsl")]
        src_name = mapping.get(name, name)
        from_path = from_pack / "layouts" / f"{src_name}.slide.dsl"
        if not from_path.is_file():
            continue
        to_fm, to_body = _split(to_path)
        from_fm, _ = _split(from_path)
        changed = False
        for key in PORT_FIELDS:
            value = from_fm.get(key)
            if value not in (None, "") and to_fm.get(key) != value:
                to_fm[key] = value
                changed = True
        if not changed:
            continue
        ported += 1
        if dry_run:
            print(f"  would port {name} <- {src_name}")
            continue
        to_path.write_text(
            "---\n" + yaml.safe_dump(to_fm, allow_unicode=True,
                                     default_flow_style=None, width=120,
                                     sort_keys=False) + "---\n" + to_body,
            encoding="utf-8")
    return ported


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--from-pack", required=True, type=Path)
    ap.add_argument("--to-pack", required=True, type=Path)
    ap.add_argument("--map", type=Path,
                    help="YAML {to-layout: from-layout} name mapping "
                         "(default: <to-pack>/curation-map.yaml when present)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    map_path = args.map or (args.to_pack / "curation-map.yaml")
    mapping: dict[str, str] = {}
    if map_path.is_file():
        raw = yaml.safe_load(map_path.read_text(encoding="utf-8")) or {}
        mapping = {str(k): str(v) for k, v in (raw.get("layouts", raw)).items()}
        print(f"using mapping {map_path} ({len(mapping)} entries)")

    n = port_curation(args.from_pack.resolve(), args.to_pack.resolve(),
                      mapping, dry_run=args.dry_run)
    print(f"{'would port' if args.dry_run else 'ported'} curated fields "
          f"into {n} layout(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

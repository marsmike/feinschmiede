"""Compose one atlas-overview PNG per brand.

Reads `docs/brand-previews/<brand>/<NN>-<id>.png` in index order and
tiles them into a single grid PNG at
`docs/brand-previews/<brand>/_atlas.png`. Used by the brand-gallery
site to give a one-glance view of the full layout set.

Run:
    uv run python scripts/build_brand_atlas_overview.py            # all brands
    uv run python scripts/build_brand_atlas_overview.py feinschliff binance
    uv run python scripts/build_brand_atlas_overview.py --cols 6   # custom grid

Tile size and gutters track the slide aspect (16:9). Background color
follows the brand's `paper` token (or `ink` for dark-first brands) so
the composite reads as part of the brand sheet rather than a generic
contact sheet.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image


REPO = Path(__file__).resolve().parents[2]
PREVIEW_DIR = REPO / "docs" / "brand-previews"
# Brands split across core + extra plugins; resolve by name.
BRAND_ROOTS = {}
for _root in (REPO / "feinschliff" / "brands", REPO / "feinschliff-extra" / "brands"):
    if _root.is_dir():
        for _d in sorted(_root.iterdir()):
            if _d.is_dir() and (_d / "tokens.json").is_file():
                BRAND_ROOTS.setdefault(_d.name, _d)

DARK_FIRST: frozenset[str] = frozenset()  # no dark-first standalone brands remain


def _brand_bg(brand: str) -> tuple[int, int, int]:
    if brand not in BRAND_ROOTS:
        return (255, 255, 255)
    tok = BRAND_ROOTS[brand] / "tokens.json"
    if not tok.is_file():
        return (255, 255, 255)
    data = json.loads(tok.read_text())
    color = data.get("color", {})
    slot = "ink" if brand in DARK_FIRST else "paper"
    hex_ = (color.get(slot) or {}).get("$value")
    if not hex_:
        hex_ = (color.get("paper") or {}).get("$value") or "#ffffff"
    hex_ = hex_.lstrip("#")
    if len(hex_) == 3:
        hex_ = "".join(c * 2 for c in hex_)
    try:
        return tuple(int(hex_[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (255, 255, 255)


def _tile_pngs(brand_dir: Path) -> list[Path]:
    return [p for p in sorted(brand_dir.glob("*.png")) if not p.name.startswith("_")]


def _compose(brand: str, tiles: list[Path], cols: int, tile_w: int, gutter: int) -> Image.Image:
    rows = (len(tiles) + cols - 1) // cols
    tile_h = round(tile_w * 9 / 16)
    width = cols * tile_w + (cols + 1) * gutter
    height = rows * tile_h + (rows + 1) * gutter

    bg = _brand_bg(brand)
    canvas = Image.new("RGB", (width, height), bg)

    for i, png_path in enumerate(tiles):
        with Image.open(png_path) as im:
            im = im.convert("RGB")
            im.thumbnail((tile_w, tile_h), Image.LANCZOS)
            x_off = gutter + (i % cols) * (tile_w + gutter) + (tile_w - im.width) // 2
            y_off = gutter + (i // cols) * (tile_h + gutter) + (tile_h - im.height) // 2
            canvas.paste(im, (x_off, y_off))
    return canvas


def build_one(brand: str, cols: int, tile_w: int, gutter: int) -> tuple[str, str]:
    brand_dir = PREVIEW_DIR / brand
    if not brand_dir.is_dir():
        return brand, f"skip: no preview dir at {brand_dir}"
    tiles = _tile_pngs(brand_dir)
    if not tiles:
        return brand, "skip: no tiles"
    canvas = _compose(brand, tiles, cols=cols, tile_w=tile_w, gutter=gutter)
    out = brand_dir / "_atlas.png"
    canvas.save(out, format="PNG", optimize=True)
    return brand, f"ok ({len(tiles)} tiles, {canvas.width}×{canvas.height})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brands", nargs="*", help="Brand ids (default: all in docs/brand-previews/)")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--tile-w", type=int, default=480, help="Tile width in px")
    ap.add_argument("--gutter", type=int, default=16)
    args = ap.parse_args()

    if not PREVIEW_DIR.is_dir():
        print(f"missing preview dir: {PREVIEW_DIR}", file=sys.stderr)
        return 2

    if args.brands:
        brands = args.brands
    else:
        brands = sorted(b.name for b in PREVIEW_DIR.iterdir() if b.is_dir())

    for brand in brands:
        name, msg = build_one(brand, cols=args.cols, tile_w=args.tile_w, gutter=args.gutter)
        print(f"  {name:>22}  {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

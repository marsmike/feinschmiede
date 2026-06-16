"""Render the brand-gallery atlas.

A brand pack's `master.pptx` *is* the showcase — the brand designer
authored real, designed sample slides into it (the snippets the
ClonePlan path clones from). The gallery shows those actual slides, not
synthetic fills against bare layouts, so each card reflects the brand's
true visual identity. For each in-repo brand pack:

  1. Open the master; for a theme variant, overlay its scheme colors so
     the same designed slides render in that skin.
  2. Save showcase.pptx into the brand's preview directory.
  3. Convert to PDF with soffice.
  4. Rasterize the first `MAX_TILES` PDF pages to PNG with pdftoppm.
  5. Build a single atlas PNG (2-up grid) via Pillow.

Then emit docs/brands/index.html with one card per brand/theme variant.
The whole site is regenerated each run; the script is idempotent.

Run via:

  feinschliff feinschliff/scripts/render_gallery.py [--workers N]

Default `--workers` is max(1, os.cpu_count() // 2) per the CLAUDE.md
half-CPU rule. Each brand is independent, so workers parallelise cleanly.
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from pptx import Presentation
from PIL import Image

from feinschliff import apply_theme, master_path

REPO_ROOT = Path(__file__).resolve().parents[2]
BRANDS_DIR = REPO_ROOT / "feinschliff" / "brands"
DOCS_DIR = REPO_ROOT / "docs"
PREVIEWS_DIR = DOCS_DIR / "brand-previews"
DEFAULT_WORKERS = max(1, (os.cpu_count() or 2) // 2)
# Sample slides per card. The master leads with its most representative
# slides (title / section / hero content), so the first few make the tile.
MAX_TILES = 4


def _showcase_pptx(brand_dir: Path, theme: Path | None, out: Path) -> None:
    """Write the brand's master (its own designed sample slides) to `out`,
    overlaying `theme`'s scheme colors first when a variant is requested."""
    prs = Presentation(str(master_path(brand_dir)))
    if theme is not None:
        apply_theme(prs, theme)
    prs.save(str(out))


def _atlas(pngs: list[Path], out: Path, cols: int = 2) -> None:
    """N-up grid composite of the showcase PNGs."""
    if not pngs:
        return
    tiles = [Image.open(p) for p in pngs]
    tw, th = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    atlas = Image.new("RGB", (tw * cols, th * rows), "white")
    for i, tile in enumerate(tiles):
        atlas.paste(tile, ((i % cols) * tw, (i // cols) * th))
    # Resize to a reasonable thumbnail width (1200px max) for the gallery card.
    if atlas.width > 1200:
        scale = 1200 / atlas.width
        atlas = atlas.resize((1200, int(atlas.height * scale)), Image.LANCZOS)
    atlas.save(out, "PNG", optimize=True)


def _build_one(brand_dir_str: str, theme_path_str: str | None = None,
               label: str | None = None) -> dict:
    brand_dir = Path(brand_dir_str)
    name = label or brand_dir.name
    work = PREVIEWS_DIR / name
    work.mkdir(parents=True, exist_ok=True)
    for stale in work.glob("slide-*.png"):  # idempotent: drop prior run's tiles
        stale.unlink()
    pptx = work / "showcase.pptx"
    theme = Path(theme_path_str) if theme_path_str else None
    _showcase_pptx(brand_dir, theme, pptx)

    profile = work / "_lo-profile"
    subprocess.run(
        ["soffice", f"-env:UserInstallation=file://{profile}",
         "--headless", "--convert-to", "pdf", "--outdir", str(work), str(pptx)],
        check=True, capture_output=True,
    )
    pdf = work / "showcase.pdf"
    if not pdf.exists():
        raise RuntimeError(f"soffice produced no PDF for {name}")
    # -l MAX_TILES: rasterize only the first few slides — the rest of the
    # master may run to dozens of snippet slides we don't tile.
    subprocess.run(
        ["pdftoppm", "-png", "-r", "120", "-l", str(MAX_TILES), str(pdf), str(work / "slide")],
        check=True, capture_output=True,
    )
    pngs = sorted(work.glob("slide-*.png"))[:MAX_TILES]
    atlas_path = work / "_atlas.png"
    _atlas(pngs, atlas_path)
    return {
        "brand": name,
        "base_brand": brand_dir.name,
        "n_slides": len(pngs),
        "atlas": str(atlas_path.relative_to(DOCS_DIR)),
    }


def _theme_variants(brand_dir: Path) -> list[tuple[Path | None, str]]:
    """One entry per (scheme.json, label) — `(None, brand_dir.name)` is the
    no-theme base variant; the rest follow the theme-overlay filename."""
    variants: list[tuple[Path | None, str]] = [(None, brand_dir.name)]
    themes_dir = brand_dir / "themes"
    if themes_dir.is_dir():
        for theme_dir in sorted(themes_dir.iterdir()):
            scheme = theme_dir / "scheme.json"
            if scheme.exists():
                variants.append((scheme, f"{brand_dir.name}-{theme_dir.name}"))
    return variants


def _index_html(brands: list[dict]) -> str:
    cards = []
    for b in sorted(brands, key=lambda x: x["brand"]):
        # Atlas paths are stored relative to docs/, but this index.html lives
        # in docs/brands/ — prefix `../` so the browser resolves them (same
        # as the favicon link below). The card links to the full-res atlas.
        href = f"../{b['atlas']}"
        cards.append(f"""
  <article class="card">
    <a href="{href}"><img src="{href}" alt="{b['brand']}"></a>
    <h3><a href="{href}">{b['brand']}</a></h3>
    <p>First {b['n_slides']} slides of this pack's master.pptx.</p>
  </article>""")
    return f"""<!doctype html>
<meta charset="utf-8">
<title>feinschmiede — brand gallery</title>
<link rel="icon" type="image/svg+xml" href="../feinschmiede-mark.svg">
<style>
  body {{ font-family: ui-sans-serif, system-ui, sans-serif; max-width: 1280px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ margin-bottom: 0.5rem; }}
  .lead {{ color: #555; margin-bottom: 2rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 1.5rem; }}
  .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }}
  .card img {{ width: 100%; height: auto; border-radius: 4px; }}
  .card h3 {{ margin: 0.75rem 0 0.25rem; text-transform: capitalize; }}
  .card h3 a {{ color: inherit; text-decoration: none; }}
  .card h3 a:hover {{ text-decoration: underline; }}
  .card p {{ margin: 0; color: #666; font-size: 0.9rem; }}
</style>
<h1>feinschmiede brand gallery</h1>
<p class="lead">Master-template renderer — each card shows a four-slide showcase rendered through that pack's <code>master.pptx</code>. {len(brands)} packs available.</p>
<section class="grid">{''.join(cards)}
</section>
"""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Render the brand-gallery atlas.")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                    help=f"Parallel brand renders (default: {DEFAULT_WORKERS}, half of CPU count).")
    args = ap.parse_args(argv)

    brands = sorted(b for b in BRANDS_DIR.iterdir() if b.is_dir() and not b.name.startswith("."))
    # A pack whose master resolves through a `master.pptx.ref` pointing
    # outside the repo (gallery / corporate packs) can't render in an
    # environment that lacks that local asset directory — notably CI.
    # Skip such packs up front so they don't count against the exit code;
    # a genuine render failure of a resolvable pack still fails the run.
    renderable: list[Path] = []
    for b in brands:
        try:
            master_path(b)
        except FileNotFoundError:
            print(f"  SKIP {b.name:30} master unavailable in this environment", file=sys.stderr)
            continue
        renderable.append(b)

    # Each brand expands to its base + one tile per theme/<name>/scheme.json
    # variant. feinschliff currently ships 8 themes (default + 7); other packs
    # ship no themes today, so they yield a single tile each.
    jobs: list[tuple[Path, Path | None, str]] = []
    for b in renderable:
        for theme_path, label in _theme_variants(b):
            jobs.append((b, theme_path, label))

    print(f"rendering {len(renderable)} brands -> {len(jobs)} tiles "
          f"with {args.workers} workers", file=sys.stderr)
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.joinpath("brands").mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context("spawn")) as ex:
        futures = {
            ex.submit(_build_one, str(b), str(t) if t else None, label): label
            for b, t, label in jobs
        }
        for fut in as_completed(futures):
            try:
                info = fut.result()
                print(f"  OK {info['brand']:30} {info['n_slides']} slides", file=sys.stderr)
                results.append(info)
            except Exception as e:
                label = futures[fut]
                print(f"  FAIL {label:30} {type(e).__name__}: {e}", file=sys.stderr)

    (DOCS_DIR / "brands" / "index.html").write_text(_index_html(results))
    print(f"wrote {DOCS_DIR / 'brands' / 'index.html'} with {len(results)} cards", file=sys.stderr)
    return 0 if len(results) == len(jobs) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

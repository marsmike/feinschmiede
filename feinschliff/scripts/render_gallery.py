"""Render the brand-gallery atlas.

For each in-repo brand pack:

  1. Compose a small, repeatable storyline (Title -> 3 content slides ->
     End slide) via FillPlan against the pack's master.
  2. Save out.pptx into the brand's preview directory.
  3. Convert to PDF with soffice.
  4. Rasterize each PDF page to PNG with pdftoppm.
  5. Build a single atlas PNG (4-up grid) via Pillow.

Then emit docs/brands/index.html with one card per brand (atlas thumb,
brand name, layout count). The whole site is regenerated each run; the
script is idempotent.

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

from PIL import Image

from feinschliff import FillPlan, render
from feinschliff.master_template.catalog import build_catalog

REPO_ROOT = Path(__file__).resolve().parents[2]
BRANDS_DIR = REPO_ROOT / "feinschliff" / "brands"
DOCS_DIR = REPO_ROOT / "docs"
PREVIEWS_DIR = DOCS_DIR / "brand-previews"
DEFAULT_WORKERS = max(1, (os.cpu_count() or 2) // 2)

# Layout-name candidates per slot, in preference order. Each brand pack
# uses different names; we try several and pick the first that exists.
TITLE_CANDIDATES = [
    "Title Slide", "Title Slide 1", "Title slide", "Title horizontal",
    "Title only", "Title Only", "Title",
]
CHAPTER_CANDIDATES = [
    "Section Header", "Section Title", "Section Break", "Section",
    "Beginning of New Chapter 1", "Chapter horizontal", "Intro", "Agenda", "Summary",
]
CONTENT_CANDIDATES = [
    "Title and 3 Contents", "3 Vertical contents", "Content 3 Column",
    "Title and 2 Contents", "2 Vertical contents", "Content 2 Column",
    "Title and two content", "Two content light blue", "Two content white",
    "Two Content", "Two Content 1", "Title and Content", "Title and content 2",
    "Introduction 2", "1 Content", "Headline only",
]
END_CANDIDATES = [
    "End Slide", "Thank you", "Closing", "Title Slide", "Title horizontal",
    "Title only", "Title Only",
]


def _pick(layouts: list[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in layouts:
            return c
    return None


def _sample_plans(brand_dir: Path) -> list[FillPlan]:
    """Build a 4-slide showcase for a brand pack using layouts that exist."""
    cat = build_catalog(brand_dir)
    layouts = [layout["name"] for layout in cat["layouts"]]
    brand_name = brand_dir.name.replace("-", " ").title()

    plans: list[FillPlan] = []
    title = _pick(layouts, TITLE_CANDIDATES)
    if title:
        plans.append(FillPlan(title, {0: brand_name, 1: "feinschmiede brand pack"}))

    chapter = _pick(layouts, CHAPTER_CANDIDATES)
    if chapter:
        plans.append(FillPlan(chapter, {0: "What's inside", 1: f"{len(layouts)} layouts, {len(cat['snippets'])} snippets"}))

    content = _pick(layouts, CONTENT_CANDIDATES)
    if content:
        plans.append(FillPlan(content, {
            0: "Master-template renderer",
            1: ["Plans, not DSL", "FillPlan / ClonePlan against the master.pptx"],
            2: ["Theme overlay", "Patch theme1.xml clrScheme — one master, N skins"],
            3: ["Brand-pluggable", "Public + private brand packs, transparent .ref pointers"],
        }))

    end = _pick(layouts, END_CANDIDATES)
    if end:
        plans.append(FillPlan(end, {0: f"{brand_name}."}))

    if not plans:
        raise RuntimeError(f"no usable layouts for {brand_dir.name}: {layouts}")
    return plans


def _render_brand(brand_dir: Path, work_dir: Path) -> dict:
    """Render -> soffice -> pdftoppm. Each worker gets its own LibreOffice
    user-installation dir so parallel soffice invocations don't race over
    the global profile lock (which silently drops conversions).
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    pptx = work_dir / "showcase.pptx"
    plans = _sample_plans(brand_dir)
    render(brand_dir, plans, pptx)

    profile = work_dir / "_lo-profile"
    subprocess.run(
        ["soffice", f"-env:UserInstallation=file://{profile}",
         "--headless", "--convert-to", "pdf", "--outdir", str(work_dir), str(pptx)],
        check=True, capture_output=True,
    )
    pdf = work_dir / "showcase.pdf"
    if not pdf.exists():
        raise RuntimeError(f"soffice produced no PDF for {brand_dir.name}")
    subprocess.run(
        ["pdftoppm", "-png", "-r", "120", str(pdf), str(work_dir / "slide")],
        check=True, capture_output=True,
    )
    pngs = sorted(work_dir.glob("slide-*.png"))
    return {"brand": brand_dir.name, "n_slides": len(pngs), "pngs": [str(p) for p in pngs]}


def _atlas(pngs: list[Path], out: Path, cols: int = 2) -> None:
    """4-up (or N-up) grid composite of the showcase PNGs."""
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


def _build_one(brand_dir_str: str) -> dict:
    brand_dir = Path(brand_dir_str)
    work = PREVIEWS_DIR / brand_dir.name
    info = _render_brand(brand_dir, work)
    atlas_path = work / "_atlas.png"
    _atlas([Path(p) for p in info["pngs"]], atlas_path)
    info["atlas"] = str(atlas_path.relative_to(DOCS_DIR))
    return info


def _index_html(brands: list[dict]) -> str:
    cards = []
    for b in sorted(brands, key=lambda x: x["brand"]):
        cards.append(f"""
  <article class="card">
    <img src="{b['atlas']}" alt="{b['brand']}">
    <h3>{b['brand']}</h3>
    <p>{b['n_slides']} slides rendered against this pack's master.pptx.</p>
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
    print(f"rendering {len(brands)} brands with {args.workers} workers", file=sys.stderr)
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.joinpath("brands").mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context("spawn")) as ex:
        futures = {ex.submit(_build_one, str(b)): b.name for b in brands}
        for fut in as_completed(futures):
            try:
                info = fut.result()
                print(f"  OK {info['brand']:20} {info['n_slides']} slides", file=sys.stderr)
                results.append(info)
            except Exception as e:
                name = futures[fut]
                print(f"  FAIL {name:20} {type(e).__name__}: {e}", file=sys.stderr)

    (DOCS_DIR / "brands" / "index.html").write_text(_index_html(results))
    print(f"wrote {DOCS_DIR / 'brands' / 'index.html'} with {len(results)} cards", file=sys.stderr)
    return 0 if len(results) == len(brands) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

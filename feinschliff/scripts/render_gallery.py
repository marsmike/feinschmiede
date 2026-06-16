"""Render the two-level brand gallery.

A brand pack's `master.pptx` *is* the showcase — the brand designer
authored real, designed sample slides into it (the snippets the
ClonePlan path clones from). The gallery shows those actual slides, not
synthetic fills against bare layouts.

Two levels, so the reader can pick a brand pack *and* a color scheme and
then see every slide:

  Level 1  docs/brands/index.html — one card per brand pack (feinschliff
           first), color schemes deep-linking into the brand page.
  Level 2  docs/brand-previews/<brand>/index.html — every slide of that
           master, with a color-scheme selector that swaps all images in
           place via JS. Images live per scheme at <brand>/<scheme>/.

Per (brand, scheme): open the master, overlay the scheme's colors for a
theme variant, soffice -> PDF, pdftoppm -> one PNG per slide, Pillow ->
atlas thumbnail for the level-1 card. The whole site is regenerated each
run; the script is idempotent.

Run via:

  feinschliff feinschliff/scripts/render_gallery.py [--workers N]

Default `--workers` is max(1, os.cpu_count() // 2) per the CLAUDE.md
half-CPU rule. Each brand is independent, so workers parallelise cleanly.
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from pptx import Presentation
from PIL import Image

from feinschliff import apply_theme, master_path
from feinschliff.master_template.theme_overlay import base_palette

REPO_ROOT = Path(__file__).resolve().parents[2]
BRANDS_DIR = REPO_ROOT / "feinschliff" / "brands"
DOCS_DIR = REPO_ROOT / "docs"
PREVIEWS_DIR = DOCS_DIR / "brand-previews"
DEFAULT_WORKERS = max(1, (os.cpu_count() or 2) // 2)
# Sample slides per card. The master leads with its most representative
# slides (title / section / hero content), so the first few make the tile.
MAX_TILES = 4      # slides composited into a card's atlas thumbnail
DETAIL_DPI = 110   # per-slide rasterization for the detail page
# Per-deploy cache-bust appended to slide <img> URLs. Slide filenames are
# stable across deploys (slide-01.png ...), so without this a returning
# visitor keeps seeing the browser-cached copy from before a re-render.
# GitHub Actions sets GITHUB_SHA; locally it's empty (no query appended).
VERSION = os.environ.get("GITHUB_SHA", "")[:8]
FIRST_BRAND = "feinschliff"  # pinned to the top of the overview; rest alphabetical


def _slug(name: str) -> str:
    """Filesystem- and URL-safe form of a scheme name (`as authored` -> `as-authored`)."""
    return name.replace(" ", "-")


def _showcase_pptx(brand_dir: Path, theme: Path | None, out: Path) -> None:
    """Write the brand's master (its own designed sample slides) to `out`,
    overlaying `theme`'s scheme colors first when a variant is requested."""
    prs = Presentation(str(master_path(brand_dir)))
    if theme is not None:
        apply_theme(prs, theme, recolor_from=base_palette(brand_dir))
    prs.save(str(out))


def _atlas(pngs: list[Path], out: Path, cols: int = 2) -> None:
    """N-up grid composite of the first few showcase PNGs (the card thumbnail)."""
    if not pngs:
        return
    tiles = [Image.open(p) for p in pngs[:MAX_TILES]]
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


def _scheme_variants(brand_dir: Path) -> list[tuple[Path | None, str]]:
    """One `(theme_or_None, scheme_name)` per selectable color scheme.

    `(None, "as authored")` is the master's own palette; each
    `themes/<name>/scheme.json` adds one overlaid scheme."""
    variants: list[tuple[Path | None, str]] = [(None, "as authored")]
    themes_dir = brand_dir / "themes"
    if themes_dir.is_dir():
        for theme_dir in sorted(themes_dir.iterdir()):
            scheme = theme_dir / "scheme.json"
            if scheme.exists():
                variants.append((scheme, theme_dir.name))
    return variants


def _build_one(brand_str: str, theme_path_str: str | None, scheme: str) -> dict:
    """Render every slide of one (brand, scheme) into its own preview dir.

    Returns the metadata main() needs to wire up both gallery levels: the
    full slide list (level 2 detail page) and the atlas thumbnail (level 1
    card). Detail/index HTML is written by main(), which alone knows the
    full sibling-scheme set."""
    brand_dir = Path(brand_str)
    brand = brand_dir.name
    work = PREVIEWS_DIR / brand / _slug(scheme)
    work.mkdir(parents=True, exist_ok=True)

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
        raise RuntimeError(f"soffice produced no PDF for {brand}/{scheme}")
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(DETAIL_DPI), str(pdf), str(work / "slide")],
        check=True, capture_output=True,
    )
    pngs = sorted(work.glob("slide-*.png"))
    _atlas(pngs, work / "_atlas.png")
    # Drop heavy intermediates — the Pages artifact only needs PNGs + HTML.
    # (The master.pptx is ~8 MB; one copy per scheme would bloat the upload.)
    pptx.unlink(missing_ok=True)
    pdf.unlink(missing_ok=True)
    shutil.rmtree(profile, ignore_errors=True)
    rel = f"{brand}/{_slug(scheme)}"
    return {
        "brand": brand,
        "scheme": scheme,
        "slug": _slug(scheme),
        "dir": rel,                                  # under brand-previews/
        "n_slides": len(pngs),
        "slides": [p.name for p in pngs],            # same dir as the detail page
        "atlas": f"brand-previews/{rel}/_atlas.png",  # relative to docs/
    }


# ---- HTML ----------------------------------------------------------------

_STYLE = """
  body { font-family: ui-sans-serif, system-ui, sans-serif; max-width: 1280px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }
  a { color: #0b6; }
  h1 { margin-bottom: 0.25rem; }
  .lead { color: #555; margin: 0 0 2rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 1.5rem; }
  .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }
  .card img { width: 100%; height: auto; border-radius: 4px; display: block; }
  .card h3 { margin: 0.75rem 0 0.5rem; text-transform: capitalize; }
  .card h3 a { color: inherit; text-decoration: none; }
  .card h3 a:hover { text-decoration: underline; }
  .schemes { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }
  .schemes a { display: inline-block; padding: 0.2rem 0.6rem; border: 1px solid #ccd; border-radius: 999px;
               cursor: pointer; font-size: 0.82rem; text-decoration: none; text-transform: capitalize; }
  .schemes a.current { background: #0b6; border-color: #0b6; color: #fff; }
  .slides { display: grid; grid-template-columns: repeat(auto-fill, minmax(440px, 1fr)); gap: 1.25rem; margin-top: 1.5rem; }
  figure { margin: 0; border: 1px solid #e3e3e3; border-radius: 6px; overflow: hidden; }
  figure img { width: 100%; height: auto; display: block; }
  figcaption { padding: 0.4rem 0.7rem; color: #777; font-size: 0.8rem; background: #fafafa; }
  .back { display: inline-block; margin-bottom: 1rem; }
"""


def _ordered_brands(groups: dict[str, list[dict]]) -> list[str]:
    """FIRST_BRAND pinned to the top of the overview, the rest alphabetical."""
    rest = sorted(b for b in groups if b != FIRST_BRAND)
    return ([FIRST_BRAND] if FIRST_BRAND in groups else []) + rest


def _brand_detail_html(brand: str, variants: list[dict]) -> str:
    """One page per brand at brand-previews/<brand>/index.html: every slide,
    plus a color-scheme selector that swaps all images in place via JS (no page
    reload). Images live in per-scheme subdirs (<slug>/slide-NN.png)."""
    primary = variants[0]                       # "as authored"
    vq = f"?v={VERSION}" if VERSION else ""
    buttons = "".join(
        f'<a data-slug="{v["slug"]}" class="{"current" if v is primary else ""}" '
        f'href="#{v["slug"]}" onclick="pickScheme(\'{v["slug"]}\');return false;">{v["scheme"]}</a>'
        for v in variants
    )
    figures = "".join(
        f'\n  <figure><img loading="lazy" data-file="{fn}" src="{primary["slug"]}/{fn}{vq}"'
        f' alt="slide {i}"><figcaption>Slide {i}</figcaption></figure>'
        for i, fn in enumerate(primary["slides"], 1)
    )
    return f"""<!doctype html>
<meta charset="utf-8">
<title>{brand} — feinschmiede brand gallery</title>
<link rel="icon" type="image/svg+xml" href="../../feinschmiede-mark.svg">
<style>{_STYLE}</style>
<a class="back" href="../../brands/">← all brand packs</a>
<h1 style="text-transform: capitalize">{brand}</h1>
<p class="lead">Color scheme — pick one to recolor every slide instantly:</p>
<nav class="schemes" id="selector">{buttons}</nav>
<section class="slides" id="slides">{figures}
</section>
<script>
  var VQ = "{vq}";
  function pickScheme(slug) {{
    document.querySelectorAll('#slides img').forEach(function (img) {{
      img.src = slug + '/' + img.dataset.file + VQ;
    }});
    document.querySelectorAll('#selector a').forEach(function (a) {{
      a.classList.toggle('current', a.dataset.slug === slug);
    }});
    if (history.replaceState) history.replaceState(null, '', '#' + slug);
  }}
  (function () {{
    var h = decodeURIComponent(location.hash.slice(1));
    if (h && document.querySelector('#selector a[data-slug="' + h + '"]')) pickScheme(h);
  }})();
</script>
"""


def _index_html(groups: dict[str, list[dict]]) -> str:
    """The overview — one card per brand pack, color schemes deep-linking into
    that brand's page (#<scheme> preselects it)."""
    cards = []
    for brand in _ordered_brands(groups):
        variants = groups[brand]
        primary = variants[0]
        detail = f"../brand-previews/{brand}/"
        atlas = f"../{primary['atlas']}"
        chips = "".join(
            f'<a href="{detail}#{v["slug"]}">{v["scheme"]}</a>' for v in variants
        )
        n_schemes = len(variants)
        schemes_label = "1 color scheme" if n_schemes == 1 else f"{n_schemes} color schemes"
        cards.append(f"""
  <article class="card">
    <a href="{detail}"><img src="{atlas}" alt="{brand}"></a>
    <h3><a href="{detail}">{brand}</a></h3>
    <p>{primary['n_slides']} slides · {schemes_label}</p>
    <nav class="schemes">{chips}</nav>
  </article>""")
    n_variants = sum(len(v) for v in groups.values())
    return f"""<!doctype html>
<meta charset="utf-8">
<title>feinschmiede — brand gallery</title>
<link rel="icon" type="image/svg+xml" href="../feinschmiede-mark.svg">
<style>{_STYLE}</style>
<h1>feinschmiede brand gallery</h1>
<p class="lead">Pick a brand pack and a color scheme to browse every slide of its <code>master.pptx</code>. {len(groups)} packs · {n_variants} scheme variants.</p>
<section class="grid">{''.join(cards)}
</section>
"""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Render the brand gallery (index + per-scheme detail pages).")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                    help=f"Parallel renders (default: {DEFAULT_WORKERS}, half of CPU count).")
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

    # Each brand expands to one job per selectable color scheme (base
    # "as authored" + one per themes/<name>/scheme.json).
    jobs: list[tuple[Path, Path | None, str]] = []
    for b in renderable:
        for theme_path, scheme in _scheme_variants(b):
            jobs.append((b, theme_path, scheme))

    print(f"rendering {len(renderable)} brands -> {len(jobs)} scheme variants "
          f"with {args.workers} workers", file=sys.stderr)
    # Wipe stale variant dirs (renamed schemes leave orphans) before workers spawn.
    shutil.rmtree(PREVIEWS_DIR, ignore_errors=True)
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.joinpath("brands").mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context("spawn")) as ex:
        futures = {
            ex.submit(_build_one, str(b), str(t) if t else None, scheme): f"{b.name}/{scheme}"
            for b, t, scheme in jobs
        }
        for fut in as_completed(futures):
            try:
                info = fut.result()
                print(f"  OK {info['brand']+'/'+info['scheme']:34} {info['n_slides']} slides", file=sys.stderr)
                results.append(info)
            except Exception as e:
                print(f"  FAIL {futures[fut]:34} {type(e).__name__}: {e}", file=sys.stderr)

    # Group variants by brand, "as authored" first then the rest, and write
    # one in-place-selector page per brand at brand-previews/<brand>/index.html.
    groups: dict[str, list[dict]] = {}
    for info in results:
        groups.setdefault(info["brand"], []).append(info)
    for brand, variants in groups.items():
        variants.sort(key=lambda v: (v["scheme"] != "as authored", v["scheme"]))
        (PREVIEWS_DIR / brand / "index.html").write_text(_brand_detail_html(brand, variants))

    (DOCS_DIR / "brands" / "index.html").write_text(_index_html(groups))
    print(f"wrote gallery: {len(groups)} packs, {len(results)} scheme variants", file=sys.stderr)
    return 0 if len(results) == len(jobs) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

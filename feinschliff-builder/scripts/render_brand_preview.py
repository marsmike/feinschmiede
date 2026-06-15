"""Render a brand's full layout sheet as PDF + PPTX (v2 path).

Walks the shared `layouts/*.slide.dsl` catalog in the README taxonomy
order (covers → sections → editorial → data → strategic → text →
diagrams → end), builds each single-slide layout against the brand via
`feinschliff build` using `tests/fixtures/layouts/<layout>.yaml` for
content, converts each .pptx to PDF via `soffice --headless
--convert-to pdf` (isolated UserInstallation profile per invocation to
dodge sequential-reuse failures), then stitches per-layout PDFs
together with `pdfunite`.

Slide numbering (`footer_right`) is rewritten per-render to
`Slide N / TOTAL` reflecting actual position in the sheet — the
fixtures' hardcoded values (often stale or decorative) are overridden
via overlay YAMLs in `.debug/examples/<brand>/template-build/content/`.

A companion multi-slide PPTX is also produced via `feinschliff deck
build` over a single auto-generated plan — same content, editable in
PowerPoint / Keynote / LibreOffice.

Output:
  examples/<brand>/<Brand-Name>-Template.pdf
  examples/<brand>/<Brand-Name>-Template.pptx

Layouts without a matching `tests/fixtures/layouts/<id>.yaml` are skipped with a
warning rather than aborting — keeps the script resilient as new
layouts land before their content fixtures. Layouts on disk but not in
TAXONOMY_ORDER (or vice versa) abort the run — silent drift would
produce a half-correct template.

Usage:
    uv run python scripts/render_brand_preview.py <brand> [<brand> ...]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from feinschliff.io.soffice import SOFFICE, pptx_to_pdf

REPO_ROOT = Path(__file__).resolve().parent.parent
# Toolkit layouts moved out of feinschliff-builder when the packages were
# split: shared `.slide.dsl` files now live in sibling `feinschliff/layouts`,
# and the per-layout content fixtures stayed under feinschliff/tests.
SHARED_LAYOUTS = REPO_ROOT.parent / "feinschliff" / "brands" / "feinschliff" / "layouts"
SHARED_CONTENT = REPO_ROOT.parent / "feinschliff" / "tests" / "fixtures" / "layouts"

PDFUNITE = shutil.which("pdfunite") or "/opt/homebrew/bin/pdfunite"
FEINSCHLIFF_CLI = "feinschliff"  # resolved via `uv run`, see _build_pptx

# Canonical taxonomy: README inventory + the two diagram -full variants
# slotted next to their siblings under Diagrams.
TAXONOMY_ORDER = [
    # Covers (3)
    "title-orange", "title-ink", "full-bleed-cover",
    # Section openers (3 — incl. new editorial)
    "chapter-orange", "chapter-ink", "full-bleed-editorial",
    # Editorial (4)
    "executive-summary", "action-title", "key-takeaways", "quote",
    # Data (15 — kpi-photo + chart-photo added next to siblings)
    "kpi-grid", "kpi-photo",
    "bar-chart", "line-chart", "stacked-bar", "chart-photo", "waterfall",
    "2x2-matrix", "venn", "pyramid", "funnel", "scorecard",
    "process-flow", "gantt", "table", "v-model",
    # Strategic (6)
    "recommendation", "next-steps", "roadmap", "timeline",
    "risk-matrix", "risk-register",
    # Text layouts (12 — agenda-photo + photo-grid + photo-strip-four added)
    "horizontal-bullets", "vertical-bullets", "two-column-cards",
    "three-column", "four-column-cards",
    "photo-grid", "photo-strip-four",
    "text-picture",
    "agenda", "agenda-photo", "components-showcase", "graphical",
    # Diagrams (4 — 2 base + 2 full-bleed)
    "excalidraw-diagram", "excalidraw-diagram-full",
    "svg-infographic", "svg-infographic-full",
    # Closers (2 — gold-ground + image variant)
    "end", "end-image",
]


def _title_case(brand: str) -> str:
    return "-".join(part.capitalize() for part in brand.split("-"))


def _resolve_layouts_in_order() -> list[Path]:
    """Return layout file paths in TAXONOMY_ORDER. Aborts on drift."""
    on_disk = {p.name.replace(".slide.dsl", ""): p
               for p in SHARED_LAYOUTS.glob("*.slide.dsl")}
    missing = [lid for lid in TAXONOMY_ORDER if lid not in on_disk]
    extras = sorted(set(on_disk) - set(TAXONOMY_ORDER))
    if missing or extras:
        parts = []
        if missing:
            parts.append(f"in TAXONOMY_ORDER but missing on disk: {missing}")
        if extras:
            parts.append(f"on disk but missing from TAXONOMY_ORDER: {extras}")
        raise SystemExit("layout taxonomy drift — " + " / ".join(parts))
    return [on_disk[lid] for lid in TAXONOMY_ORDER]


def _write_overlay(yaml_src: Path, idx: int, total: int,
                   overlay_dir: Path) -> Path:
    """Copy fixture YAML with `footer_right` rewritten to reflect the
    slide's position in the rendered sheet."""
    raw = yaml.safe_load(yaml_src.read_text()) or {}
    raw["footer_right"] = f"Slide {idx} / {total}"
    dst = overlay_dir / yaml_src.name
    dst.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True))
    return dst


def _build_pptx(layout: Path, content: Path, brand: str, out: Path) -> None:
    """Run `feinschliff build` to produce a single-slide .pptx."""
    subprocess.run(
        [
            FEINSCHLIFF_CLI, "build",
            str(layout),
            "--brand", brand,
            "--content", str(content),
            "-o", str(out),
            "--skip-content-lint",  # showcase render; content quality not gated
            "--allow-missing-assets",  # image slots may be empty in fixtures
            "--allow-diagram-warnings",  # the multi-slide path already passes
                                         # this; deep diagrams (excalidraw-
                                         # diagram-full) trip arrow-crossing
                                         # warnings that are fatal by default.
        ],
        check=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def _build_multislide_pptx(brand: str, slides: list[tuple[Path, Path]],
                           plan_path: Path, out: Path) -> None:
    """Author a single deck plan over the overlay YAMLs, then run
    `feinschliff deck build` for an editable multi-slide PPTX.

    `slides` is a list of (layout_path, overlay_yaml_path) tuples in
    render order. `plan_path` is where the plan YAML is written — its
    parent directory anchors relative `content_file` lookups."""
    plan_dir = plan_path.parent
    plan = {
        "brand": brand,
        "slides": [
            {
                # Use the absolute layout path: SHARED_LAYOUTS now lives in
                # a sibling package (feinschliff/layouts), so relative_to
                # REPO_ROOT fails. The deck builder resolves any abs path.
                "layout": str(layout),
                "content_file": str(overlay.relative_to(plan_dir)),
            }
            for layout, overlay in slides
        ],
    }
    plan_path.write_text(yaml.safe_dump(plan, sort_keys=False))
    subprocess.run(
        [
            FEINSCHLIFF_CLI, "deck", "build",
            str(plan_path),
            "-o", str(out),
            "--allow-missing-assets",
            "--skip-content-lint",
            "--allow-diagram-warnings",
        ],
        check=True,
        cwd=REPO_ROOT,
    )


def render_brand(brand: str) -> tuple[Path, Path]:
    """Build, convert, and stitch the brand's full layout sheet — emit
    PDF (per-layout PDFs stitched with pdfunite) and PPTX (multi-slide
    via `feinschliff deck build`)."""
    examples_dir = REPO_ROOT / "examples" / brand
    examples_dir.mkdir(parents=True, exist_ok=True)
    final_pdf = examples_dir / f"{_title_case(brand)}-Template.pdf"
    final_pptx = examples_dir / f"{_title_case(brand)}-Template.pptx"

    layout_files = _resolve_layouts_in_order()

    # First pass: filter to layouts that have fixtures, so the denominator
    # in `Slide N / TOTAL` matches what actually renders.
    renderable: list[tuple[str, Path, Path]] = []
    skipped: list[str] = []
    for layout in layout_files:
        lid = layout.name.replace(".slide.dsl", "")
        yaml_path = SHARED_CONTENT / f"{lid}.yaml"
        if yaml_path.is_file():
            renderable.append((lid, layout, yaml_path))
        else:
            skipped.append(lid)

    if not renderable:
        raise SystemExit(f"no fixtures matched for {brand} — check tests/fixtures/layouts/")

    total = len(renderable)
    work_dir = REPO_ROOT / ".debug" / "examples" / brand / "template-build"
    overlay_dir = work_dir / "content"
    overlay_dir.mkdir(parents=True, exist_ok=True)

    # Second pass: write overlays with corrected slide numbers, render.
    per_layout_pdfs: list[Path] = []
    slide_specs: list[tuple[Path, Path]] = []  # (layout, overlay) for deck build

    with tempfile.TemporaryDirectory(prefix=f"render-{brand}-") as tmp:
        tmp_dir = Path(tmp)
        for idx, (lid, layout, yaml_path) in enumerate(renderable, 1):
            overlay = _write_overlay(yaml_path, idx, total, overlay_dir)
            print(f"  [{idx:02d}/{total}] {lid}", flush=True)
            pptx = tmp_dir / f"{lid}.pptx"
            _build_pptx(layout, overlay, brand, pptx)
            per_layout_pdfs.append(pptx_to_pdf(pptx, tmp_dir))
            slide_specs.append((layout, overlay))

        for lid in skipped:
            print(f"  -- SKIP {lid} (no tests/fixtures/layouts/{lid}.yaml)", flush=True)

        subprocess.run(
            [PDFUNITE, *map(str, per_layout_pdfs), str(final_pdf)],
            check=True,
        )

    plan_path = work_dir / "plan.yaml"
    _build_multislide_pptx(brand, slide_specs, plan_path, final_pptx)

    pdf_kb = final_pdf.stat().st_size / 1024
    pptx_kb = final_pptx.stat().st_size / 1024
    print(f"  → {final_pdf.relative_to(REPO_ROOT)} "
          f"({pdf_kb:.0f} KB, {len(per_layout_pdfs)} pages"
          f"{', skipped: ' + ', '.join(skipped) if skipped else ''})")
    print(f"  → {final_pptx.relative_to(REPO_ROOT)} "
          f"({pptx_kb:.0f} KB, {len(slide_specs)} slides)")
    return final_pdf, final_pptx


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brands", nargs="+",
                    help="brand name(s), e.g. feinschliff solarized-dark")
    args = ap.parse_args()

    if not Path(SOFFICE).is_file():
        sys.exit(f"soffice not found at {SOFFICE}")
    if not shutil.which(PDFUNITE):
        sys.exit(f"pdfunite not found at {PDFUNITE} (brew install poppler)")

    for brand in args.brands:
        print(f"rendering {brand}…")
        render_brand(brand)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

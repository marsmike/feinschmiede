#!/usr/bin/env python3
"""End-to-end source → render → diff orchestrator for brand-pack verification.

Any brand pack with a `verify-map.yaml` can run a single command to:

  1. **Export source PNGs** — converts the source deck (.pptx) to a single
     PDF via LibreOffice, then rasters every page referenced in
     `verify-map.yaml` to a 1920×1080 PNG.
  2. **Render derived layouts** — for each layout in `verify-map.yaml`,
     runs `feinschliff build` on `<brand>/layouts/<layout>.slide.dsl` →
     `.pptx` → `.pdf` → PNG. Slot defaults take over so the layout's own
     placeholder text/illustration appears in the render.
  3. **Diff** — calls the shared scorer
     (`feinschliff_builder.verify.visual_diff.run_visual_diff`) in-process
     to write per-layout 3-panel overlays, ghost masks, `report.json`, and
     an append-only `score-trace.jsonl` for plateau detection.

Everything caches under `<output-dir>/` keyed by file mtime, so re-runs
after a single DSL edit only rebuild the affected layout.

Drop-in usage:

  uv run python scripts/brand_verify_loop.py \\
      --brand-pack brands/<brand> \\
      --source-pptx path/to/source-deck.pptx

  uv run python scripts/brand_verify_loop.py \\
      --brand-pack brands/<brand> \\
      --source-pptx path/to/source-deck.pptx \\
      --only quote table cover-orange

  uv run python scripts/brand_verify_loop.py \\
      --brand-pack brands/<brand> \\
      --source-pptx path/to/source-deck.pptx \\
      --output-dir out/<brand>/verify-loop \\
      --skip-source-export

The pipeline is brand-agnostic; it only assumes the brand pack has a
`verify-map.yaml` mapping `<layout-name>: <source-slide-number>` and that
each layout exists at `<brand>/layouts/<layout-name>.slide.dsl`.

Step 3 of the brand-bootstrap pipeline — score the scaffold + drive
`/feinschliff-builder:improve-brand` if anything is above threshold.
→ Canonical pipeline: see `feinschliff-builder/README.md`.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO))
from feinschliff_builder.verify.verify_map import load_verify_map
from feinschliff_builder.verify.visual_diff import run_visual_diff

# Canonical LibreOffice/pdftoppm path: isolated `UserInstallation` profiles
# per conversion, so a verify-loop run concurrent with e.g.
# `render_brand_atlas --workers 8` can't collide on the shared soffice
# profile lock and silently produce no output.
from feinschliff.io.soffice import pdf_to_pngs, pptx_to_pdf


def _run(cmd: list[str], **kw) -> None:
    subprocess.run(cmd, check=True, **kw)


def _newer(target: Path, *srcs: Path) -> bool:
    if not target.exists():
        return True
    t = target.stat().st_mtime
    return any(s.exists() and s.stat().st_mtime > t for s in srcs)


def export_source_pngs(source_pptx: Path, source_pdf: Path,
                       source_png_dir: Path, slide_nos: list[int]) -> list[str]:
    """Render the source deck once → split into per-slide PNGs at 1920×1080.

    Returns a list of per-slide failure strings. A bad slide number (e.g.
    out of the deck's page range) drops just that slide rather than aborting
    the whole pipeline — mirroring the render loop. A failure of the
    soffice PDF conversion itself is fatal (nothing can be scored).
    """
    source_png_dir.mkdir(parents=True, exist_ok=True)
    if _newer(source_pdf, source_pptx):
        source_pdf.parent.mkdir(parents=True, exist_ok=True)
        print(f"[source] {source_pptx.name} → {source_pdf.name}")
        # Fatal: without the source PDF there is nothing to compare against
        # (pptx_to_pdf raises RuntimeError, which propagates).
        produced_pdf = pptx_to_pdf(source_pptx, source_pdf.parent)
        if produced_pdf != source_pdf:
            produced_pdf.rename(source_pdf)
    failures: list[str] = []
    for n in slide_nos:
        out_png = source_png_dir / f"slide-{n:02d}.png"
        if not _newer(out_png, source_pdf):
            continue
        try:
            produced = pdf_to_pngs(source_pdf, source_png_dir, slide_index=n,
                                   scale_to=(1920, 1080), prefix=f"_p{n}")
        except RuntimeError as e:
            out_png.unlink(missing_ok=True)
            failures.append(f"source slide {n}: {str(e)[-160:]}")
            continue
        produced[0].rename(out_png)
        print(f"[source] slide {n:02d} → {out_png.name}")
    return failures


def render_derived_pngs(brand_pack: Path, brand_name: str, work_root: Path,
                        render_png_dir: Path, layouts: list[str]) -> list[str]:
    """Build each layout's .slide.dsl → PPTX → PDF → PNG. Returns failures."""
    render_png_dir.mkdir(parents=True, exist_ok=True)
    layouts_dir = brand_pack / "layouts"
    # Make the brand pack's enclosing root discoverable for the build
    # subprocess. `feinschliff build --brand <name>` resolves the pack via
    # brand_discovery, which honours FEINSCHLIFF_BRAND_PATH (colon-separated
    # list of brand-root directories — each path is iterated for brand
    # subdirs, so it must point at the dir CONTAINING the pack, not its
    # grandparent). For out-of-tree packs this is the only way
    # --brand-pack is honoured end-to-end.
    enclosing = brand_pack.parent
    existing = os.environ.get("FEINSCHLIFF_BRAND_PATH", "")
    brand_env_path = (
        f"{enclosing}{os.pathsep}{existing}" if existing else str(enclosing)
    )
    build_env = {**os.environ, "FEINSCHLIFF_BRAND_PATH": brand_env_path}
    # A layout render depends on more than its own .slide.dsl: the brand's
    # tokens.json (theme colors/fonts) and DESIGN.md (token frontmatter +
    # extends) feed every build. Editing those without touching the layout
    # must still invalidate the cached PNG, else the diff scores a stale
    # render. (Parent tokens in an extends: chain change rarely; the brand's
    # own tokens/DESIGN cover the common case.)
    brand_inputs = [p for p in (brand_pack / "tokens.json",
                                brand_pack / "DESIGN.md") if p.is_file()]
    failures: list[str] = []
    for layout in layouts:
        dsl = layouts_dir / f"{layout}.slide.dsl"
        out_png = render_png_dir / f"{layout}.png"
        # A layout that fails to (re)render must NOT leave a stale PNG from a
        # prior run on disk — the diff step would otherwise score the old
        # render as if it were current. Drop it on every failure path below.
        if not dsl.is_file():
            out_png.unlink(missing_ok=True)
            failures.append(f"{layout}: missing {dsl}")
            continue
        if not _newer(out_png, dsl, *brand_inputs):
            continue
        work = work_root / layout
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        pptx = work / f"{layout}.pptx"
        try:
            _run(["uv", "run", "feinschliff", "build",
                  "--brand", brand_name, "-o", str(pptx),
                  "--allow-missing-assets", "--skip-content-lint",
                  "--allow-diagram-warnings", str(dsl)],
                 cwd=REPO, capture_output=True, env=build_env)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            out_png.unlink(missing_ok=True)
            failures.append(f"{layout}: build failed — {stderr[-200:]}")
            continue
        try:
            pdf = pptx_to_pdf(pptx, work)
        except RuntimeError as e:
            out_png.unlink(missing_ok=True)
            failures.append(f"{layout}: {str(e)[-200:]}")
            continue
        try:
            produced = pdf_to_pngs(pdf, work, scale_to=(1920, 1080),
                                   prefix="_p")
        except RuntimeError as e:
            out_png.unlink(missing_ok=True)
            failures.append(f"{layout}: {str(e)[-200:]}")
            continue
        produced[0].rename(out_png)
        print(f"[render] {layout} → {out_png.name}")
    return failures


def run_diff(brand_pack: Path, source_png_dir: Path,
             render_png_dir: Path, diff_dir: Path,
             only: list[str] | None = None,
             loupe: bool = False) -> int:
    """Run the scorer; return its exit code (non-zero = some layout unscored).

    The scorer deliberately returns a code instead of raising: it writes
    report.json even on a partial run and signals partial-ness via a
    non-zero code, which the caller surfaces — an exception here would
    discard that signal.
    """
    diff_dir.mkdir(parents=True, exist_ok=True)
    return run_visual_diff(brand_pack, source_png_dir, render_png_dir,
                           diff_dir, only=only, loupe=loupe)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand-pack", required=True, type=Path,
                    help="Brand pack root (must contain verify-map.yaml + layouts/)")
    ap.add_argument("--source-pptx", required=True, type=Path,
                    help="Source PPTX deck to compare against")
    ap.add_argument("--output-dir", type=Path,
                    help="Where to write source-png/, render-png/, diff/. "
                         "Defaults to out/<brand>/verify-loop")
    ap.add_argument("--only", nargs="*",
                    help="Restrict to a subset of layouts (by name)")
    ap.add_argument("--skip-source-export", action="store_true",
                    help="Reuse cached source PNGs as-is")
    ap.add_argument("--skip-render", action="store_true",
                    help="Reuse cached render PNGs as-is")
    ap.add_argument("--snapshot-baseline", action="store_true",
                    help="Copy the post-render PNGs into render-png.before/ "
                         "before scoring. Use on the first run of an "
                         "improve-brand loop so brand_before_after_pdf.py "
                         "can compose source ↔ baseline ↔ final overlays.")
    ap.add_argument("--loupe", action="store_true",
                    help="Also emit a loupe PDF (per-layout top-N "
                         "connected-component diff hotspots, each cropped + "
                         "scaled). Use when the redline shows residual "
                         "mismatches too small to diagnose at slide scale.")
    args = ap.parse_args()

    brand_pack: Path = args.brand_pack.resolve()
    if not brand_pack.is_dir():
        sys.exit(f"brand pack not found: {brand_pack}")
    try:
        _vm = load_verify_map(brand_pack)
    except FileNotFoundError:
        sys.exit(f"missing verify-map.yaml in {brand_pack}")
    except ValueError as exc:
        sys.exit(str(exc))
    source_pptx: Path = args.source_pptx.resolve()
    if not source_pptx.is_file():
        sys.exit(f"source pptx not found: {source_pptx}")

    brand_name = brand_pack.name
    out_root: Path = (args.output_dir or REPO / "out" / brand_name / "verify-loop").resolve()
    source_pdf = out_root / "source.pdf"
    source_png_dir = out_root / "source-png"
    render_png_dir = out_root / "render-png"
    diff_dir = out_root / "diff"
    work_root = out_root / "work"

    mapping: dict[str, int] = dict(_vm.layouts)
    # `is not None` (not truthiness): `--only` with zero names yields [], which
    # must error as "no layouts matched", NOT silently fall through to all.
    if args.only is not None:
        wanted = set(args.only)
        mapping = {k: v for k, v in mapping.items() if k in wanted}
        if not mapping:
            sys.exit(f"--only matched no layouts (have: "
                     f"{sorted(_vm.layouts)})")

    failures: list[str] = []
    if not args.skip_source_export:
        failures += export_source_pngs(source_pptx, source_pdf, source_png_dir,
                                       sorted(set(mapping.values())))
    if not args.skip_render:
        failures += render_derived_pngs(brand_pack, brand_name, work_root,
                                        render_png_dir, list(mapping))

    if args.snapshot_baseline:
        baseline_dir = out_root / "render-png.before"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        for layout in mapping:
            src = render_png_dir / f"{layout}.png"
            if src.is_file():
                shutil.copy2(src, baseline_dir / src.name)
        print(f"[baseline] snapshotted {len(mapping)} renders → "
              f"{baseline_dir.name}/")

    # Diff ONLY layouts that have BOTH a fresh render PNG and a source PNG. A
    # layout missing either had its stale PNG removed above, so it is excluded
    # rather than silently scored against a stale/missing render. This is the
    # key correctness invariant: report.json never presents stale or missing
    # renders as current results.
    renderable = [lyt for lyt in mapping
                  if (render_png_dir / f"{lyt}.png").is_file()
                  and (source_png_dir / f"slide-{mapping[lyt]:02d}.png").is_file()]
    excluded = [lyt for lyt in mapping if lyt not in set(renderable)]

    if failures:
        diff_dir.mkdir(parents=True, exist_ok=True)
        (diff_dir / "render-failures.txt").write_text(
            "\n".join(failures) + "\n"
        )
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)

    if not renderable:
        print("\nNo layouts rendered successfully — nothing to diff. "
              "report.json NOT updated.", file=sys.stderr)
        return 1

    diff_rc = run_diff(brand_pack, source_png_dir, render_png_dir, diff_dir,
                       only=renderable, loupe=args.loupe)
    print(f"\n→ overlays: {diff_dir}")

    # The scorer MERGES into report.json (so a subset run keeps un-run
    # layouts). That merge would otherwise let a layout that failed THIS run
    # retain its previous score. Strip excluded layouts so report.json never
    # presents a stale score for something that just failed.
    report_path = diff_dir / "report.json"
    if excluded and report_path.is_file():
        try:
            rep = json.loads(report_path.read_text())
            removed = [lyt for lyt in excluded if rep.pop(lyt, None) is not None]
            if removed:
                report_path.write_text(json.dumps(rep, indent=2))
        except (json.JSONDecodeError, OSError) as e:
            print(f"warning: could not prune excluded layouts from "
                  f"report.json: {e}", file=sys.stderr)

    if failures or excluded or diff_rc != 0:
        n_bad = len(set(excluded) | {f.split(':')[0] for f in failures})
        print(f"\n⚠ {n_bad} layout(s) failed to render/score and were EXCLUDED "
              f"from report.json (see {diff_dir / 'render-failures.txt'}). The "
              f"{len(renderable)} that rendered were scored normally.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

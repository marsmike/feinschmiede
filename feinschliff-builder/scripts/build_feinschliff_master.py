"""Build the feinschliff house brand master.pptx.

Walks every layout under `feinschliff/brands/feinschliff/layouts/`, runs
`feinschliff build` with the matching content fixture, then merges every
rendered .pptx into a single master deck via deep XML clone — the same
mechanism feinschmiede.master_template.ClonePlan uses at render time.

Output:
    feinschliff/brands/feinschliff/master.pptx
    feinschliff/brands/feinschliff/snippets.yaml (one entry per layout)

This is a one-time build script. After PR4 ships, the feinschliff house
brand routes through feinschliff.master_template, not the DSL pipeline,
and the DSL/ module is deleted.

Run:
    uv run python feinschliff-builder/scripts/build_feinschliff_master.py
    uv run python feinschliff-builder/scripts/build_feinschliff_master.py --workers 8
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import copy
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from lxml import etree
from pptx import Presentation

REPO_ROOT = Path(__file__).resolve().parents[2]
BRAND_DIR = REPO_ROOT / "feinschliff/brands/feinschliff"
LAYOUTS_DIR = BRAND_DIR / "layouts"
FIXTURES_DIR = REPO_ROOT / "tests/feinschliff/fixtures/layouts"
MASTER_PPTX = BRAND_DIR / "master.pptx"
SNIPPETS_YAML = BRAND_DIR / "snippets.yaml"
LAYOUTS_YAML = BRAND_DIR / "layouts.yaml"

_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS = {"a": _A}


def _layout_ids() -> list[str]:
    return sorted(p.stem.replace(".slide", "") for p in LAYOUTS_DIR.glob("*.slide.dsl"))


def _build_one(layout_id: str) -> Path | None:
    layout_path = LAYOUTS_DIR / f"{layout_id}.slide.dsl"
    content_path = FIXTURES_DIR / f"{layout_id}.yaml"
    if not content_path.exists():
        print(f"  SKIP {layout_id}: no fixture at {content_path}", file=sys.stderr)
        return None
    tmp = Path(tempfile.mkdtemp(prefix=f"master-{layout_id}-"))
    pptx = tmp / f"{layout_id}.pptx"
    cmd = [
        "uv", "run", "feinschliff", "build",
        str(layout_path),
        "--brand", "feinschliff",
        "--content", str(content_path),
        "-o", str(pptx),
        "--skip-content-lint",
        "--allow-missing-assets",
        "--allow-diagram-warnings",
    ]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"  FAIL {layout_id}\n{res.stderr[-400:]}", file=sys.stderr)
        return None
    return pptx


def _merge_into_master(per_layout_pptx: list[tuple[str, Path]]) -> list[dict]:
    """Open the first .pptx as the master, clone every other deck's slide(s)
    into it as snippets. Returns the snippets index for snippets.yaml."""
    first_id, first_pptx = per_layout_pptx[0]
    prs = Presentation(str(first_pptx))
    snippets = []
    for i, slide in enumerate(prs.slides):
        snippets.append({"id": first_id, "source_idx": i, "intent": f"feinschliff/{first_id}"})

    dest_layout = prs.slide_layouts[0]
    for layout_id, pptx_path in per_layout_pptx[1:]:
        src = Presentation(str(pptx_path))
        for src_slide in src.slides:
            new_slide = prs.slides.add_slide(dest_layout)
            for shape in list(new_slide.shapes):
                shape._element.getparent().remove(shape._element)
            for child in list(src_slide.shapes._spTree):
                if etree.QName(child).localname in ("nvGrpSpPr", "grpSpPr"):
                    continue
                new_slide.shapes._spTree.append(copy.deepcopy(child))
            # Skip cross-deck image rels: each source pptx has its own image1.png
            # binary; copying the rel by reference would collide on the master's
            # /ppt/media/ namespace. Fixture images are re-bound at render time
            # via PictureRef. Image-heavy snippets still ship their text +
            # shape geometry — operators replace the missing-image placeholder.
            snippets.append({
                "id": layout_id,
                "source_idx": len(snippets),
                "intent": f"feinschliff/{layout_id}",
            })
    prs.save(str(MASTER_PPTX))
    return snippets


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    p.add_argument("--only", nargs="*", help="Restrict to specific layout ids")
    args = p.parse_args()

    ids = _layout_ids()
    if args.only:
        ids = [i for i in ids if i in args.only]
    print(f"building {len(ids)} layouts with --workers {args.workers}…")

    results: dict[str, Path] = {}
    with futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_build_one, lid): lid for lid in ids}
        for fut in futures.as_completed(futs):
            lid = futs[fut]
            pptx = fut.result()
            if pptx is not None:
                results[lid] = pptx
                print(f"  built {lid}")

    if not results:
        print("no layouts built; aborting", file=sys.stderr)
        return 1

    per_layout = [(lid, results[lid]) for lid in ids if lid in results]
    snippets = _merge_into_master(per_layout)
    SNIPPETS_YAML.write_text(yaml.safe_dump({"snippets": snippets}, sort_keys=False))
    LAYOUTS_YAML.write_text("# Feinschliff house brand is snippet-only — every layout is a\n"
                            "# ClonePlan against snippets.yaml. No FillPlan entries.\nlayouts: []\n")

    print(f"\nwrote {MASTER_PPTX} ({MASTER_PPTX.stat().st_size / 1024:.1f} KB, {len(snippets)} slides)")
    print(f"wrote {SNIPPETS_YAML} ({len(snippets)} snippets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

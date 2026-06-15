"""Render every brand × every snippet/layout as a PNG — the gallery atlas.

Walks every master-template brand pack and renders one PNG per
snippet (and per layout, where the layout is fillable as-is). Uses
`feinschmiede.master_template` — no DSL.

Output:
    docs/brand-previews/<brand>/<NN>-<id>.png

NN is the 1-based index of the snippet/layout within the brand's
catalog; it gives stable, sortable filenames that play nicely with
both the gallery grid and Cloudflare R2 listings.

Brand packs scanned:
- `feinschliff/brands/<brand>/`
- `feinschliff-extra/brands/<brand>/`

Each must ship `master.pptx{,.ref}` + `layouts.yaml` + `snippets.yaml`
to be rendered. Brands without `snippets.yaml` are skipped with a
warning.

Run:
    uv run python feinschliff-builder/scripts/render_brand_atlas.py
    uv run python feinschliff-builder/scripts/render_brand_atlas.py feinschliff
    uv run python feinschliff-builder/scripts/render_brand_atlas.py --workers 8
    uv run python feinschliff-builder/scripts/render_brand_atlas.py --force
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml
from feinschmiede.master_template import ClonePlan, render

REPO_ROOT = Path(__file__).resolve().parents[2]


def _discover_packs() -> list[tuple[str, Path]]:
    """Walk the in-repo brand roots and return master-template packs."""
    found: list[tuple[str, Path]] = []
    for root in [REPO_ROOT / "feinschliff/brands",
                 REPO_ROOT / "feinschliff-extra/brands"]:
        if not root.is_dir():
            continue
        for sub in sorted(root.iterdir()):
            if sub.is_dir() and (sub / "snippets.yaml").exists():
                found.append((sub.name, sub))
    return found


_BRAND_ROOTS = _discover_packs()


@dataclass(frozen=True)
class AtlasJob:
    brand: str
    brand_pack: Path
    index: int        # 1-based position within the brand
    snippet_id: str   # also used as filename slug


def _discover_jobs(only: list[str] | None) -> list[AtlasJob]:
    jobs: list[AtlasJob] = []
    for brand, pack in _BRAND_ROOTS:
        if only and brand not in only:
            continue
        if not pack.exists():
            print(f"SKIP {brand}: pack dir missing ({pack})", file=sys.stderr)
            continue
        snippets_yaml = pack / "snippets.yaml"
        if not snippets_yaml.exists():
            print(f"SKIP {brand}: no snippets.yaml in {pack}", file=sys.stderr)
            continue
        snippets = (yaml.safe_load(snippets_yaml.read_text()) or {}).get("snippets") or []
        for i, snip in enumerate(snippets, start=1):
            sid = snip.get("id")
            if sid:
                jobs.append(AtlasJob(brand=brand, brand_pack=pack, index=i, snippet_id=sid))
    return jobs


def _is_fresh(out_png: Path, brand_pack: Path) -> bool:
    if not out_png.exists():
        return False
    inputs = [
        brand_pack / "master.pptx",
        brand_pack / "master.pptx.ref",
        brand_pack / "snippets.yaml",
        brand_pack / "layouts.yaml",
    ]
    newest = max((p.stat().st_mtime for p in inputs if p.exists()), default=0)
    return out_png.stat().st_mtime >= newest


def _render_pptx(job: AtlasJob, out_pptx: Path) -> None:
    plan = ClonePlan(snippet_id=job.snippet_id)
    render(job.brand_pack, [plan], out_pptx)


def _pptx_to_png(pptx: Path, out_png: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="atlas-pdf-") as work:
        work_dir = Path(work)
        # soffice serializes instances sharing a profile; give each worker its
        # own profile dir so concurrent renders don't clobber each other.
        profile = work_dir / "soffice-profile"
        res = subprocess.run(
            ["soffice", f"-env:UserInstallation=file://{profile}",
             "--headless", "--convert-to", "pdf", str(pptx),
             "--outdir", str(work_dir)],
            capture_output=True, text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"soffice pdf failed: {res.stderr[-400:]}")
        pdf = work_dir / (pptx.stem + ".pdf")
        if not pdf.exists():
            raise RuntimeError(f"soffice produced no PDF for {pptx}")
        res = subprocess.run(
            ["pdftoppm", "-r", "80", "-f", "1", "-l", "1", "-png", str(pdf), str(work_dir / "page")],
            capture_output=True, text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"pdftoppm failed: {res.stderr[-400:]}")
        pngs = sorted(work_dir.glob("page-*.png"))
        if not pngs:
            raise RuntimeError(f"pdftoppm produced no PNG for {pdf}")
        out_png.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(pngs[0], out_png)


def _render_one(job: AtlasJob, force: bool) -> tuple[AtlasJob, str, str]:
    """Render one slot. Returns (job, verdict, msg). verdict in {ok, cached, fail}."""
    docs = REPO_ROOT / "docs/brand-previews" / job.brand
    out_png = docs / f"{job.index:02d}-{job.snippet_id}.png"
    if not force and _is_fresh(out_png, job.brand_pack):
        return job, "cached", str(out_png)
    tmp = Path(tempfile.mkdtemp(prefix=f"atlas-{job.brand}-{job.snippet_id}-"))
    try:
        pptx = tmp / "slide.pptx"
        _render_pptx(job, pptx)
        _pptx_to_png(pptx, out_png)
        return job, "ok", str(out_png)
    except Exception as exc:
        return job, "fail", f"{type(exc).__name__}: {exc}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("brands", nargs="*", help="Restrict to these brand ids (default: all)")
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    p.add_argument("--force", action="store_true", help="Rerender even cached PNGs")
    args = p.parse_args()

    jobs = _discover_jobs(only=args.brands or None)
    if not jobs:
        print("no jobs discovered (check --brands and pack contents)", file=sys.stderr)
        return 1
    print(f"rendering {len(jobs)} slot(s) with --workers {args.workers}…")

    ok = cached = failed = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for fut in cf.as_completed(ex.submit(_render_one, j, args.force) for j in jobs):
            job, verdict, msg = fut.result()
            if verdict == "ok":
                ok += 1
                print(f"  ok      {job.brand}/{job.snippet_id}")
            elif verdict == "cached":
                cached += 1
            else:
                failed += 1
                print(f"  FAIL    {job.brand}/{job.snippet_id}: {msg}", file=sys.stderr)
    print(f"\nrendered: {ok} fresh, {cached} cached, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

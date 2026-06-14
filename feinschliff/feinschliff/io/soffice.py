"""Shared LibreOffice pptx → pdf / png helpers for the render scripts.

Centralises the `soffice --headless --convert-to pdf` invocation with
isolated `UserInstallation` profiles — parallel callers would otherwise
collide on the shared profile lock and silently produce no output — plus
the `pdftoppm` rasterise step most callers do next.

Several render scripts (dsl_golden_compare, render_brand_atlas,
render_brand_preview) used to each carry their own copy of this dance;
this module is the single canonical version.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


SOFFICE = shutil.which("soffice") or "/opt/homebrew/bin/soffice"
PDFTOPPM = shutil.which("pdftoppm") or "/opt/homebrew/bin/pdftoppm"


def pptx_to_pdf(pptx_path: Path, out_dir: Path) -> Path:
    """Convert .pptx → .pdf via soffice; return the PDF path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="soffice-profile-") as profile:
        try:
            subprocess.run(
                [SOFFICE, f"-env:UserInstallation=file://{profile}",
                 "--headless", "--convert-to", "pdf",
                 "--outdir", str(out_dir), str(pptx_path)],
                check=True, capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            stderr_text = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            raise RuntimeError(f"soffice failed: {stderr_text[:500]}") from e
    pdf = out_dir / pptx_path.with_suffix(".pdf").name
    if not pdf.is_file():
        raise RuntimeError(f"soffice produced no PDF for {pptx_path}")
    return pdf


def pdf_to_pngs(pdf_path: Path, out_dir: Path,
                *, slide_index: int | None = None, dpi: int = 96,
                scale_to: tuple[int, int] | None = None,
                prefix: str = "page") -> list[Path]:
    """Rasterise a PDF → PNGs via pdftoppm; return the sorted PNG paths.

    `slide_index` is 1-based; when None, every page is rasterised. Pages
    render at `-r dpi` by default; pass `scale_to=(width, height)` to emit
    `-scale-to-x/-scale-to-y` instead — a fixed pixel size regardless of
    page geometry (the brand verify loop diffs at exactly 1920×1080).
    `prefix` controls the pdftoppm output stem (`<prefix>-N.png`).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if scale_to is not None:
        width, height = scale_to
        cmd = [PDFTOPPM, "-scale-to-x", str(width),
               "-scale-to-y", str(height), "-png"]
    else:
        cmd = [PDFTOPPM, "-r", str(dpi), "-png"]
    if slide_index is not None:
        cmd += ["-f", str(slide_index), "-l", str(slide_index)]
    cmd += [str(pdf_path), str(out_dir / prefix)]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr_text = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        raise RuntimeError(f"pdftoppm failed: {stderr_text[:500]}") from e
    pngs = sorted(out_dir.glob(f"{prefix}-*.png"))
    if not pngs:
        raise RuntimeError(f"pdftoppm produced no PNG for {pdf_path}")
    return pngs


def pptx_to_png(pptx_path: Path, out_dir: Path,
                *, slide_index: int | None = None, dpi: int = 96,
                scale_to: tuple[int, int] | None = None,
                prefix: str = "page") -> Path:
    """Convert .pptx → PNG; return the first matching PNG path.

    `slide_index` is 1-based; when None, every slide is rasterised and
    the first PNG is returned (the legacy "page-1.png" behaviour). The
    PDF intermediate lands next to the PNGs inside `out_dir`. `prefix`
    controls the pdftoppm output stem — set it per-call when multiple
    pptxs share an `out_dir` and you need stable, distinct PNG names.
    `scale_to=(width, height)` swaps the `-r dpi` flag for
    `-scale-to-x/-scale-to-y` (see `pdf_to_pngs`).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = pptx_to_pdf(pptx_path, out_dir)
    return pdf_to_pngs(pdf, out_dir, slide_index=slide_index, dpi=dpi,
                       scale_to=scale_to, prefix=prefix)[0]

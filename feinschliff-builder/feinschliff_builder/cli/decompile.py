"""`feinschliff-builder decompile …` — bulk-decompile every layout in a
brand's `verify-map.yaml` from a source PPTX.

Reads `<brand>/verify-map.yaml`, then for each `<layout-name>: <slide-no>`
pair calls the hybrid PPTX+SVG decompiler
(`feinschliff_builder.decompile.pptx_svg_decompile.derive`) and writes
`<brand>/layouts/<layout-name>.slide.dsl`. Existing layout files are
snapshotted into `<brand>/layouts.bak/` before being overwritten.

Step 1 of brand bootstrap. Follow up with `slotify` to add the picker
frontmatter and `deck-map.yaml`.

→ Canonical pipeline: see `feinschliff-builder/README.md`.
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import io
import json
import os
import re
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from pptx import Presentation as _Pres

from feinschliff_builder.decompile.cleanup import cleanup_dsl, native_pic_rects, unslotified_text_report
from feinschliff_builder.decompile.pptx_svg_decompile import derive, master_theme_blob
from feinschliff_builder.decompile.slotify import clip_text_to_images, slotify_dsl, slotify_native_text
from feinschliff_builder.verify.verify_map import load_verify_map


def _cleanup_and_slotify_loop(dsl: str, *, asset_root, layout_name: str,
                              width_emu: float = 0.0, canvas_w: float = 1920.0,
                              max_rounds: int = 4) -> tuple[str, list[str]]:
    """Per-slide decompile loop: cleanup -> slotify (text lines + native
    payloads) -> re-check, until the unslotified-text report stops shrinking.

    Every pass is idempotent, so the loop normally converges in one round;
    the cap is a safety net. Returns ``(dsl, leftover report)`` — leftovers
    are texts that CANNOT be slotified (chart/SmartArt part labels, labels
    with braces), surfaced as warnings for the operator.
    """
    dsl, stats = cleanup_dsl(dsl, asset_root, width_emu=width_emu,
                             canvas_w=canvas_w)
    noise = {k: v for k, v in stats.items() if v}
    if noise:
        print(f"    cleanup {layout_name}: " +
              ", ".join(f"{k}={v}" for k, v in noise.items()))
    prev = None
    for _ in range(max_rounds):
        dsl, _slots = slotify_dsl(dsl)
        dsl, clips = clip_text_to_images(
            dsl, extra_images=native_pic_rects(
                dsl, asset_root, width_emu=width_emu, canvas_w=canvas_w))
        for line in clips:
            print(f"    clip {layout_name}: {line}")
        dsl, native_slots, logs = slotify_native_text(dsl, asset_root)
        for line in logs:
            print(f"    native-slotify {layout_name}: {line}")
        report = unslotified_text_report(dsl, asset_root)
        if prev is not None and len(report) >= len(prev):
            break
        prev = report
    return dsl, prev or []


def _derive_one(layout_name: str, slide_no: int, *, source_pptx: Path,
                canvas_w: int, canvas_h: int, tokens_path: Path | None,
                brand_pack: Path, brand_name: str, carry_images: bool,
                raw: bool, src_w_emu: int) -> tuple[str, int, list[str]]:
    """Derive + clean + slotify ONE slide and write its layout file.

    Module-level (picklable) so a ProcessPoolExecutor can fan slides out
    across workers — every slide is independent: it reads the shared source
    PPTX, writes only its own `layouts/<name>.slide.dsl` and per-layout
    asset dirs, and sha-named native sidecars are written atomically.
    Returns (layout_name, bytes_written, log lines) for ordered printing
    in the parent.
    """
    log = io.StringIO()
    image_extract_dir = image_extract_rel = None
    if carry_images:
        image_extract_dir = brand_pack / "assets" / "decompile" / layout_name
        image_extract_rel = f"decompile/{layout_name}"
    with contextlib.redirect_stdout(log):
        dsl = derive(
            source_pptx,
            slide_idx=slide_no,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            tokens_path=tokens_path,
            layout_name=layout_name,
            theme_name=brand_name,
            image_extract_dir=image_extract_dir,
            image_extract_rel=image_extract_rel,
            native_extract_dir=brand_pack / "assets" / "native",
            native_extract_rel="native",
        )
        if not raw:
            dsl, leftovers = _cleanup_and_slotify_loop(
                dsl, asset_root=brand_pack / "assets",
                layout_name=layout_name,
                width_emu=float(src_w_emu), canvas_w=canvas_w)
            for msg in leftovers:
                print(f"    ⚠ {layout_name}: unslotified {msg}")
    target = brand_pack / "layouts" / f"{layout_name}.slide.dsl"
    target.write_text(dsl, encoding="utf-8")
    return layout_name, target.stat().st_size, log.getvalue().splitlines()


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--brand-pack", required=True, type=Path,
                        help="Brand pack root (must contain verify-map.yaml and tokens.json)")
    parser.add_argument("--source-pptx", required=True, type=Path,
                        help="Source PPTX deck to decompile")
    parser.add_argument("--workers", type=int, default=16,
                        help="Parallel derive workers (default 16; 0 = auto: "
                             "min(8, cpu/2); 1 = sequential)")
    parser.add_argument("--canvas", default="1920x1080",
                        help="Target DSL canvas size (default: 1920x1080)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the layouts that would be derived, don't write")
    parser.add_argument("--only", nargs="*",
                        help="Restrict to a subset of layout names")
    parser.add_argument("--raw", action="store_true",
                        help="Skip the per-slide cleanup + slotify loop and emit the "
                             "decompiler's raw first pass (for fidelity debugging). "
                             "Default: each slide is cleaned (dup text lines, prompt "
                             "copies, helper captions, stacked native pics), slotified "
                             "(text lines AND native payload text runs), and checked "
                             "until no bindable placeholder text is left unslotified.")
    parser.add_argument("--carry-images", action="store_true",
                        help="Pipeline-optimization mode: extract every <p:pic> "
                             "binary from the source slide into "
                             "<brand-pack>/assets/decompile/<layout>/imageN.<ext> "
                             "and emit DSL `default:` paths pointing at those, so "
                             "the verify loop renders the real picture (not a "
                             "placeholder) and struct_diff_ratio reflects shape/"
                             "text mismatch only, not picture-region noise.")
    parser.add_argument("--no-annotate", action="store_true",
                        help="Skip the annotated documentation PDF that "
                             "decompile emits by default at "
                             "<brand-pack>/<brand>-annotated.pdf. The PDF "
                             "has one page-set per layout (render + slot "
                             "coverage + frontmatter detail) and is what a "
                             "brand-pack reviewer opens to inspect the "
                             "fresh decompile.")
    parser.add_argument("--annotate-out", type=Path, default=None,
                        help="Override the annotated PDF path (default: "
                             "<brand-pack>/<brand>-annotated.pdf).")
    parser.set_defaults(func=cmd_decompile)


def cmd_decompile(args) -> int:
    brand_pack: Path = args.brand_pack.resolve()
    if not brand_pack.is_dir():
        print(f"decompile: brand pack not found: {brand_pack}", file=sys.stderr)
        return 2
    try:
        _vm = load_verify_map(brand_pack)
    except FileNotFoundError:
        print(f"decompile: missing verify-map.yaml in {brand_pack}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"decompile: {exc}", file=sys.stderr)
        return 2
    source_pptx: Path = args.source_pptx.resolve()
    if not source_pptx.is_file():
        print(f"decompile: source pptx not found: {source_pptx}", file=sys.stderr)
        return 2

    tokens_path = brand_pack / "tokens.json"
    brand_name = brand_pack.name
    canvas_w, canvas_h = (int(x) for x in args.canvas.split("x"))

    mapping = dict(_vm.layouts)
    requested = set(args.only) if args.only else None

    # Capture the source PPTX's physical slide size and record it in the
    # brand pack's tokens.json. The emitter (lib/dsl/pptx_emit.py) honours
    # `slide.width_emu` / `slide.height_emu` and scales EMU_PER_PX +
    # PX_TO_PT off them, so font sizes and shape positions render at the
    # SAME physical scale as the source — without this, an emit at the
    # toolkit default 13.33" wide renders a 42pt source title at ~28pt
    # because the px↔pt conversion bakes in a different DPI.
    src_pres = _Pres(str(source_pptx))
    src_w_emu = int(src_pres.slide_width)
    src_h_emu = int(src_pres.slide_height)
    if tokens_path.is_file():
        try:
            tokens_data = json.loads(tokens_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"decompile: unparseable tokens.json in {brand_pack}: {exc} "
                  "— fix or remove it first", file=sys.stderr)
            return 2
    else:
        tokens_data = {}
    slide_block = tokens_data.setdefault("slide", {"$type": "dimension"})
    slide_block["width_emu"] = {"$value": str(src_w_emu),
                                "$description": "Source PPTX slide width in EMU — drives emitter scaling."}
    slide_block["height_emu"] = {"$value": str(src_h_emu),
                                 "$description": "Source PPTX slide height in EMU — drives emitter scaling."}

    # Detect the source theme's fonts (majorFont = display/title, minorFont =
    # body) AND its colour scheme, and seed both into tokens.json. The theme
    # part is resolved from the master relationship (decks number themes
    # per-master — a hardcoded `theme1.xml` silently misses decks whose master
    # uses `theme11.xml`, skipping font + colour capture entirely). Capturing
    # the palette here is what lets schemeClr fills (e.g. the bg panel) and
    # strokes reverse-map to tokens instead of being dropped. Existing tokens
    # are never overwritten — the author's semantic names win.
    theme_blob = master_theme_blob(src_pres)
    if theme_blob:
        theme_xml = theme_blob.decode("utf-8", "replace")
        majors = re.findall(r'<a:majorFont>.*?<a:latin[^/]+typeface="([^"]+)"', theme_xml, re.DOTALL)
        minors = re.findall(r'<a:minorFont>.*?<a:latin[^/]+typeface="([^"]+)"', theme_xml, re.DOTALL)
        display_font = majors[0] if majors else None
        body_font = minors[0] if minors else None
        if display_font or body_font:
            ff_block = tokens_data.setdefault("font-family", {"$type": "fontFamily"})
            if display_font:
                ff_block["display"] = {"$value": [display_font, "Helvetica Neue", "Arial", "sans-serif"],
                                       "$description": f"Source theme majorFont: {display_font}"}
            if body_font:
                ff_block["body"] = {"$value": [body_font, "Helvetica Neue", "Arial", "sans-serif"],
                                    "$description": f"Source theme minorFont: {body_font}"}
            print(f"  source fonts: display={display_font!r} body={body_font!r} → tokens.json font-family")

        # Theme colour scheme → seed missing colour tokens. `theme-*` keys make
        # every schemeClr the decompiler meets reverse-mappable; ink/black/
        # paper/white get safe defaults for a fresh pack. setdefault semantics:
        # an author palette is never clobbered.
        scheme: dict[str, str] = {}
        for m in re.finditer(r'<a:(dk1|lt1|dk2|lt2|accent[1-6]|hlink|folHlink)>(.*?)</a:\1>',
                             theme_xml, re.DOTALL):
            hm = (re.search(r'srgbClr val="([0-9A-Fa-f]{6})"', m.group(2))
                  or re.search(r'lastClr="([0-9A-Fa-f]{6})"', m.group(2)))
            if hm:
                scheme[m.group(1)] = "#" + hm.group(1).upper()
        if scheme:
            color_block = tokens_data.setdefault("color", {"$type": "color"})

            def _seed(name: str, hexval: str | None, desc: str | None = None) -> bool:
                if hexval and name not in color_block:
                    entry = {"$value": hexval}
                    if desc:
                        entry["$description"] = desc
                    color_block[name] = entry
                    return True
                return False

            seeded = 0
            for k, v in scheme.items():
                seeded += _seed(f"theme-{k}", v, f"Source theme {k}.")
            seeded += _seed("ink", scheme.get("dk1"), "Body/title ink — source theme dk1.")
            seeded += _seed("black", scheme.get("dk1"), "Display / deepest — source theme dk1.")
            seeded += _seed("paper", scheme.get("lt1"), "Canvas on light — source theme lt1.")
            seeded += _seed("white", scheme.get("lt1"))
            if seeded:
                print(f"  source palette: {len(scheme)} theme colours → tokens.json color "
                      f"({seeded} keys seeded; existing tokens kept)")

    if args.dry_run:
        print(f"  would record slide size {src_w_emu} × {src_h_emu} EMU → {tokens_path}")
    else:
        if tokens_path.is_file():
            shutil.copy2(tokens_path, tokens_path.with_name("tokens.json.bak"))
        tokens_path.write_text(json.dumps(tokens_data, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print(f"  source slide size: {src_w_emu/914400:.2f}in × {src_h_emu/914400:.2f}in "
              f"({src_w_emu} × {src_h_emu} EMU) → tokens.json slide.width_emu/height_emu")

    layouts_dir = brand_pack / "layouts"
    backup_dir = brand_pack / "layouts.bak"
    if not args.dry_run:
        layouts_dir.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)

    todo: list[tuple[str, int]] = []
    for layout_name, slide_no in mapping.items():
        if requested is not None and layout_name not in requested:
            continue
        target = layouts_dir / f"{layout_name}.slide.dsl"
        if args.dry_run:
            print(f"  would derive {layout_name} ← p{slide_no} → {target}")
            continue
        if target.exists():
            shutil.copy2(target, backup_dir / target.name)
        todo.append((layout_name, slide_no))

    if args.dry_run:
        print(f"(dry-run: {len(todo)} layouts planned)")
        return 0

    work = functools.partial(
        _derive_one,
        source_pptx=source_pptx, canvas_w=canvas_w, canvas_h=canvas_h,
        tokens_path=tokens_path if tokens_path.exists() else None,
        brand_pack=brand_pack, brand_name=brand_name,
        carry_images=args.carry_images, raw=args.raw, src_w_emu=src_w_emu)

    workers = args.workers or min(8, max(1, (os.cpu_count() or 2) // 2))
    workers = min(workers, max(1, len(todo)))
    derived = 0
    if workers <= 1:
        for layout_name, slide_no in todo:
            name, size, lines = work(layout_name, slide_no)
            for line in lines:
                print(line)
            print(f"  ✓ {name} ← p{slide_no} ({size} bytes)")
            derived += 1
    else:
        # Slides are independent (disjoint output paths; sha-named native
        # sidecars rename atomically; soffice rasterization runs with a
        # throwaway profile per call) — fan out across processes. Results
        # print in submission order so logs stay diffable run-to-run.
        print(f"  deriving {len(todo)} layouts on {workers} workers")
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs = [(name, no, pool.submit(work, name, no))
                    for name, no in todo]
            for name, slide_no, fut in futs:
                name, size, lines = fut.result()
                for line in lines:
                    print(line)
                print(f"  ✓ {name} ← p{slide_no} ({size} bytes)")
                derived += 1

    print(f"\nderived {derived} layouts")

    # Default: emit the annotated documentation PDF so the operator sees
    # the same picker frontmatter / slot overlay / coverage rubric a
    # reviewer would. Suppress with --no-annotate (e.g. CI sweeps).
    if args.dry_run or args.no_annotate:
        return 0
    plan_path = _synthesize_showcase_plan(brand_pack, mapping, requested)
    if plan_path is None:
        return 0  # nothing to annotate (no layouts derived)
    out_pdf = args.annotate_out or (brand_pack / f"{brand_name}-annotated.pdf")
    print(f"\nrendering annotated documentation PDF → {out_pdf}")
    try:
        from feinschliff_builder.decompile.annotate import render_annotated_pdf
        render_annotated_pdf(plan_path, out_pdf)
    except FileNotFoundError as exc:
        # An external tool (soffice / pdftoppm / Chrome) is missing —
        # the layouts themselves shipped, only the documentation step
        # could not run. Soft-fail with a clear pointer.
        print(f"annotate: skipped ({exc}); install soffice + pdftoppm + "
              "Chrome to enable, or re-run with --no-annotate to silence",
              file=sys.stderr)
    return 0


def _synthesize_showcase_plan(brand_pack: Path, mapping: dict[str, int],
                              requested: set[str] | None) -> Path | None:
    """Write a minimal showcase plan in tmp pointing at every just-derived
    layout, in `verify-map.yaml` order. Each slide entry is `{layout: <abs>}`
    — the annotate renderer reads the per-layout frontmatter from those
    paths to build the overlay + detail pages.
    """
    layouts_dir = brand_pack / "layouts"
    slides = []
    for name in mapping:
        if requested is not None and name not in requested:
            continue
        lp = layouts_dir / f"{name}.slide.dsl"
        if lp.is_file():
            slides.append({"layout": str(lp)})
    if not slides:
        return None
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix=f"{brand_pack.name}-annotate-"))
    plan = tmp / "showcase-plan.yaml"
    import yaml as _yaml
    plan.write_text(_yaml.safe_dump(
        {"brand": brand_pack.name, "slides": slides},
        sort_keys=False, default_flow_style=False))
    return plan

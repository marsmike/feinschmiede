"""Post-decompile cleanup passes over a freshly derived `.slide.dsl`.

Flattening slideLayout/slideMaster inheritance (scripts/pptx_flatten_inherited.py)
makes master-based templates decompilable but brings template noise that the
hybrid decompiler currently reproduces faithfully:

  1. some flattened texts emit twice (exact-duplicate `text` lines);
  2. layout-placeholder prompt copies double a slide's own prompt box
     (two text boxes with near-identical rects, IoU > ~0.97);
  3. picture-frame helper captions ("Add Picture", "Add Text\\n…") land as
     real text boxes that overlay photos and shift slot numbering;
  4. the layout-placeholder *picture* is carried on top of the slide's own
     picture (two stacked near-identical native pics).

These passes run per slide right after `derive()` (see
feinschliff-builder decompile). All are idempotent. Keep-later policy on
the overlap passes: the decompiler emits in z-order, slide-owned shapes
last, so the LATER of two near-identical boxes is the slide's own.
"""
from __future__ import annotations

import base64
import re

__all__ = [
    "dedupe_text_lines",
    "drop_prompt_copies",
    "drop_helper_captions",
    "dedupe_native_pics",
    "strip_native_text_doubles",
    "cleanup_dsl",
    "unslotified_text_report",
]

_TEXT_GEO_RE = re.compile(
    r"^text\s+(\d+),(\d+)\b.*?maxwidth:(\d+)\s+maxheight:(\d+)")
# Trailing quoted label with escape support — `.*"(.*)"` would split on the
# `\"` pairs inside slot templates and capture garbage.
_TEXT_LABEL_RE = re.compile(r'^text\s+\d+,\d+\b[^"]*"((?:[^"\\]|\\.)*)"\s*$')
_NATIVE_B64_RE = re.compile(r'^native\s+\w+\s.*?b64:"([^"]+)"')
_XFRM_OFF_RE = re.compile(r'<a:off x="(-?\d+)" y="(-?\d+)"/>')
_XFRM_EXT_RE = re.compile(r'<a:ext cx="(\d+)" cy="(\d+)"/>')
_BAKED_T_RE = re.compile(r"<a:t>([^<]+)</a:t>")

# Helper captions PowerPoint bakes into picture/content frames. Exact match
# for the picture helper; prefix match for the multi-level text helper.
HELPER_CAPTION_EXACT = ("Add Picture",)
HELPER_CAPTION_PREFIX = ("Add Text\\n",)

# Near-identical rects only: true prompt copies overlap at >= ~0.97; real
# label/value pairs in KPI tiles overlap around 0.4-0.75 and must survive.
PROMPT_COPY_IOU = 0.9


def _iou(a: tuple, b: tuple) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0.0


def dedupe_text_lines(dsl_text: str) -> tuple[str, int]:
    """Drop exact-duplicate `text` lines (keep the first occurrence)."""
    out, seen, dropped = [], set(), 0
    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n")
        if body.startswith("text ") and body in seen:
            dropped += 1
            continue
        if body.startswith("text "):
            seen.add(body)
        out.append(line)
    return "".join(out), dropped


def drop_prompt_copies(dsl_text: str, *, iou: float = PROMPT_COPY_IOU
                       ) -> tuple[str, int]:
    """Drop the earlier of two text boxes whose rects are near-identical."""
    lines = dsl_text.splitlines(keepends=True)
    boxes = []
    for i, line in enumerate(lines):
        m = _TEXT_GEO_RE.match(line.strip())
        if m:
            boxes.append((i, tuple(float(g) for g in m.groups())))
    drop: set[int] = set()
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            ia, ra = boxes[a]
            ib, rb = boxes[b]
            if ia not in drop and _iou(ra, rb) > iou:
                drop.add(ia)
    return ("".join(ln for i, ln in enumerate(lines) if i not in drop),
            len(drop))


def drop_helper_captions(dsl_text: str) -> tuple[str, int]:
    """Drop PowerPoint's picture/content-frame helper captions."""
    out, dropped = [], 0
    for line in dsl_text.splitlines(keepends=True):
        m = _TEXT_LABEL_RE.match(line.strip())
        if m:
            label = m.group(1)
            if label in HELPER_CAPTION_EXACT or any(
                    label.startswith(p) for p in HELPER_CAPTION_PREFIX):
                dropped += 1
                continue
        out.append(line)
    return "".join(out), dropped


def _native_rect_emu(line: str) -> tuple | None:
    m = _NATIVE_B64_RE.match(line.strip())
    if m is None:
        return None
    try:
        xml = base64.b64decode(m.group(1)).decode("utf-8", "replace")
    except ValueError:
        return None
    off, ext = _XFRM_OFF_RE.search(xml), _XFRM_EXT_RE.search(xml)
    if not (off and ext):
        return None
    return (float(off.group(1)), float(off.group(2)),
            float(ext.group(1)), float(ext.group(2)))


def dedupe_native_pics(dsl_text: str, *, iou: float = PROMPT_COPY_IOU
                       ) -> tuple[str, int]:
    """Drop the earlier of two native pics with near-identical rects (EMU —
    IoU is scale-invariant, so no canvas conversion is needed)."""
    lines = dsl_text.splitlines(keepends=True)
    rects = []
    for i, line in enumerate(lines):
        if not line.strip().startswith("native "):
            continue
        r = _native_rect_emu(line)
        if r is not None:
            rects.append((i, r))
    drop: set[int] = set()
    for a in range(len(rects)):
        for b in range(a + 1, len(rects)):
            ia, ra = rects[a]
            ib, rb = rects[b]
            if ia not in drop and _iou(ra, rb) > iou:
                drop.add(ia)
    return ("".join(ln for i, ln in enumerate(lines) if i not in drop),
            len(drop))


def cleanup_dsl(dsl_text: str, asset_root=None, *, width_emu: float = 0.0,
                canvas_w: float = 1920.0) -> tuple[str, dict[str, int]]:
    """Run all post-decompile cleanup passes; returns (new_dsl, stats)."""
    stats: dict[str, int] = {}
    dsl_text, stats["dedupe_text"] = dedupe_text_lines(dsl_text)
    dsl_text, stats["prompt_copies"] = drop_prompt_copies(dsl_text)
    dsl_text, stats["helper_captions"] = drop_helper_captions(dsl_text)
    dsl_text, stats["native_pic_dupes"] = dedupe_native_pics(dsl_text)
    dsl_text, stats["native_text_doubles"] = strip_native_text_doubles(
        dsl_text, asset_root, width_emu=width_emu, canvas_w=canvas_w)
    return dsl_text, stats


_CHART_MARKERS = ("<c:chart", "<dgm:", "relIds")


def unslotified_text_report(dsl_text: str, asset_root=None) -> list[str]:
    """Texts a deck author cannot bind: literal `text` labels that escaped
    slotification, plus literal `<a:t>` runs in non-chart native payloads.

    The per-slide decompile loop runs slotify until this report is empty
    (chart/SmartArt labels excepted — those live in external parts)."""
    leftovers: list[str] = []
    for line in dsl_text.splitlines():
        body = line.strip()
        m = _TEXT_LABEL_RE.match(body)
        if m and m.group(1) and "{{" not in m.group(1):
            leftovers.append(f"text literal: {m.group(1)[:60]!r}")
            continue
        if not body.startswith("native "):
            continue
        xml = None
        bm = _NATIVE_B64_RE.match(body)
        if bm:
            try:
                xml = base64.b64decode(bm.group(1)).decode("utf-8", "replace")
            except ValueError:
                xml = None
        elif asset_root is not None:
            fm = re.search(r'xml_file:"([^"]+)"', body)
            if fm and (asset_root / fm.group(1)).is_file():
                xml = (asset_root / fm.group(1)).read_text(
                    encoding="utf-8", errors="replace")
        if xml is None or any(s in xml for s in _CHART_MARKERS):
            continue
        for t in _BAKED_T_RE.findall(xml):
            if t.strip() and "{{" not in t:
                leftovers.append(f"native text run: {t[:60]!r}")
    return leftovers


_NATIVE_LINE_KW_RE = re.compile(r'(\w+):"([^"]*)"')
# Matches default("…") in all three carrier encodings: raw XML text,
# XML-escaped (&quot;), and DSL-line backslash-escaped (\").
_RUN_DEFAULT_RE = re.compile(r'default\(\\?(?:&quot;|")(.*?)\\?(?:&quot;|")\)')


def _run_literal(run_text: str) -> str:
    """The human literal of an <a:t> run — its default(...) when the run is
    a slot template, else the run text itself."""
    m = _RUN_DEFAULT_RE.search(run_text)
    return m.group(1) if m else run_text


def strip_native_text_doubles(
    dsl_text: str, asset_root=None, *, width_emu: float = 0.0,
    canvas_w: float = 1920.0,
) -> tuple[str, int]:
    """Blank native text runs that DOUBLE a regular text line's label.

    The hybrid decompiler emits some text-bearing custGeom shapes twice: the
    shape goes native (label baked in the XML) AND its text frame is ALSO
    extracted as a `text` primitive at the same spot. With showcase defaults
    the two render stacked and invisible; the moment a deck binds one of
    them they diverge into double text. Policy: the regular `text` line wins
    (full styling + slot control) — the native run is blanked.

    A native run is a double when its literal equals a text line's literal
    (slot templates compared by their default) AND the boxes overlap
    (checked only when ``width_emu`` is known; without it, exact-literal
    match alone decides). Returns ``(new_dsl, blanked_count)``.
    """
    import base64 as _b64

    text_labels: list[tuple[str, tuple]] = []
    for line in dsl_text.splitlines():
        m = _TEXT_LABEL_RE.match(line.strip())
        if not m:
            continue
        geo = _TEXT_GEO_RE.match(line.strip())
        rect = tuple(float(g) for g in geo.groups()) if geo else None
        text_labels.append((_run_literal(m.group(1)), rect))
    if not text_labels:
        return dsl_text, 0
    labels = {lit for lit, _ in text_labels if lit.strip()}

    scale = (canvas_w / width_emu) if width_emu else None
    blanked = 0
    out_lines: list[str] = []
    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n")
        if not body.strip().startswith("native "):
            out_lines.append(line)
            continue
        kwargs = dict(_NATIVE_LINE_KW_RE.findall(body))
        xml: str | None = None
        sidecar = None
        if kwargs.get("b64"):
            try:
                xml = _b64.b64decode(kwargs["b64"]).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                xml = None
        elif kwargs.get("xml_file") and asset_root is not None:
            sidecar = asset_root / kwargs["xml_file"]
            if sidecar.is_file():
                xml = sidecar.read_text(encoding="utf-8")
        if xml is None or any(s in xml for s in _CHART_MARKERS):
            out_lines.append(line)
            continue

        native_rect_px = None
        if scale is not None:
            off, ext = _XFRM_OFF_RE.search(xml), _XFRM_EXT_RE.search(xml)
            if off and ext:
                native_rect_px = (float(off.group(1)) * scale,
                                  float(off.group(2)) * scale,
                                  float(ext.group(1)) * scale,
                                  float(ext.group(2)) * scale)

        def _overlaps_some_text(lit: str) -> bool:
            for tlit, trect in text_labels:
                if tlit != lit:
                    continue
                if native_rect_px is None or trect is None:
                    return True
                if _iou(native_rect_px, trect) > 0.0:
                    return True
            return False

        changed = False

        def repl(m: re.Match) -> str:
            nonlocal changed
            lit = _run_literal(m.group(1))
            if lit.strip() and lit in labels and _overlaps_some_text(lit):
                changed = True
                return "<a:t></a:t>"
            return m.group(0)

        new_xml = re.sub(r"<a:t>([^<]+)</a:t>", repl, xml)
        if not changed:
            out_lines.append(line)
            continue
        blanked += new_xml.count("<a:t></a:t>") - xml.count("<a:t></a:t>")
        if sidecar is not None:
            sidecar.write_text(new_xml, encoding="utf-8")
            out_lines.append(line)
        else:
            new_b64 = _b64.b64encode(new_xml.encode("utf-8")).decode("ascii")
            out_lines.append(
                body.replace(kwargs["b64"], new_b64, 1)
                + ("\n" if line.endswith("\n") else ""))
    return "".join(out_lines), blanked


def native_pic_rects(dsl_text: str, asset_root=None, *, width_emu: float,
                     canvas_w: float = 1920.0, min_px: float = 150.0) -> list[dict]:
    """Canvas-px rects of native PICTURES big enough to be content photos.

    Used as extra clip obstacles for `clip_text_to_images` — tile layouts
    carry their thumbnails as native pics, and text boxes that span the
    whole tile must clip at the photo edge exactly like at picture slots.
    Marks/logos (small) and non-pic natives are excluded; ``min_px`` is the
    minimum width AND height. Requires ``width_emu`` for the EMU→px scale.
    """
    rects: list[dict] = []
    if not width_emu:
        return rects
    scale = canvas_w / width_emu
    for line in dsl_text.splitlines():
        body = line.strip()
        if not body.startswith("native "):
            continue
        kwargs = dict(_NATIVE_LINE_KW_RE.findall(body))
        xml = None
        if kwargs.get("b64"):
            try:
                xml = base64.b64decode(kwargs["b64"]).decode("utf-8", "replace")
            except ValueError:
                continue
        elif kwargs.get("xml_file") and asset_root is not None:
            sc = asset_root / kwargs["xml_file"]
            if sc.is_file():
                xml = sc.read_text(encoding="utf-8", errors="replace")
        if not xml or "<p:pic" not in xml.split(">", 1)[0] + ">":
            continue
        off, ext = _XFRM_OFF_RE.search(xml), _XFRM_EXT_RE.search(xml)
        if not (off and ext):
            continue
        x, y = float(off.group(1)) * scale, float(off.group(2)) * scale
        w, h = float(ext.group(1)) * scale, float(ext.group(2)) * scale
        if w < min_px or h < min_px:
            continue
        m = re.match(r"^native\s+(\w+)", body)
        rects.append({"name": m.group(1) if m else "native", "x": x, "y": y,
                      "w": w, "h": h})
    return rects

"""Auto-generate layout-picker frontmatter for decompiled brand-pack layouts.

Decompiled layouts (`feinschliff-extra/brands/<brand>/layouts/*.slide.dsl`)
carry NO YAML frontmatter, so `feinschliff.layout_profile.build_profile_table`
(strict=False) silently drops every one of them — the /deck layout picker can
never choose a decompiled layout. This module closes that gap: it CLASSIFIES a
slotified layout from its DSL text alone (text slots, image slots, native
payloads) and emits the `---` frontmatter fence the picker contract requires
(`role` / `ideal_count` / `data_band` / `comparison`), plus extra keys the
parser tolerates and downstream deck planning exploits (`family`,
`fixed_chrome`, `chrome_note`, `slots`, `image_queries`, `slide_index`).

Classification heuristics — applied IN ORDER, first hit wins:

 1. slide_index == 1                          → title-primary  (framing, variety_exempt)
 2. title default / layout name ~ /agenda|inhalt|contents/i
                                              → agenda         (framing, variety_exempt)
 3. a slot default that is just a quote mark (`“`/`”`/`"`) or style:quote
                                              → quote          (voice)
 4. slide_index == total_slides, or title default ~ /thank|danke|contact|q&a$/i
                                              → closer         (closing, variety_exempt)
 5. native chart payload                      → data-comparison (comparison, data_band chart)
 6. native table payload                      → reference      (organizational, data_band table)
 7. native SmartArt payload                   → concept-diagram (process)
 8. native illustration chrome + ≤2 visible text slots
                                              → chapter-opener (framing, fixed_chrome,
                                                when_not_to_use: dense-content roles —
                                                a decorative divider must not carry facts)
 9. full-bleed image slot + ≤2 visible text slots
                                              → title-with-visual (image-driven)
10. ≥4 short body slots, ≥half numeric/percent defaults
                                              → data-quantity  (data, data_band kpi)
11. ≥3 body slots                             → content-columns (organizational)
12. otherwise                                 → content-columns (organizational)

Area-based fixed-chrome gate — applied AFTER classification, role unchanged:
when the native ILLUSTRATION payloads (kind "illustration" only, not
chart/table/smartart) together cover > 20 % of the canvas, the layout gets
`fixed_chrome: true` + a dense-content `when_not_to_use` list regardless of
its text-slot count. Motivation: an illustration-heavy layout with a text
column beside the artwork classifies as content-columns (>2 text slots), and
without the gate the picker happily pairs arbitrary content with an
unrelated illustration. Geometry comes from the payload's root
`<a:xfrm><a:off|a:ext>` in EMU, scaled by `canvas_w / 12192000` (standard
12192000x6858000 EMU slide). When any illustration payload cannot be
decoded the gate falls back to the old ≤2-visible-slots rule (rule 8).

Baked-text gate — an illustration payload whose XML carries non-whitespace
`<a:t>` runs gets `chrome_text: true` (+ "; baked text" on `chrome_note`):
the chrome draws its own labels, so binding the layout's overlapping text
slots overprints them (ghosting). The picker sinks such layouts for
content roles (`baked-text-guard`), mirroring the fixed-chrome guard.

Semantic annotation fields — every profile carries `description: ""` (one
line: what is on this slide) and `when_to_use: ""` (one line: when a deck
planner should pick this layout), and, when native illustration chrome is
present, `chrome_subject: ""` (what the illustration depicts); all are
meant to be filled by a later human/vision pass. The same pass may overrule
the heuristic slide-type by setting `family` + `family_curated: true` —
the marker makes the override survive regeneration (a bare `family` edit
reverts). Every profile also carries a mechanical `element_tree:` — one
compact line per slide element (`text <slot> role=… @x,y wxh <pt>pt`,
`image <slot> class=… @x,y wxh`, `native <kind> [@x,y wxh] [baked-text]`)
in reading order — the structural map a planner reads alongside the
description. Image slots appear in
`slots:` with `class: replace|keep` (replace = content photo the deck
should swap, keep = brand chrome such as a logo strip). `apply_profile`
MERGES instead of replacing: non-empty `description` / `chrome_subject` /
per-image `class` values in an existing fence survive a re-run, while all
mechanical fields regenerate. The `annotate` CLI (`python -m
feinschliff_builder.decompile.layout_profile_gen annotate …`) updates just
those annotation fields in an existing fence.

Slot roles (per text slot, in `slots:`): page-number (1-3 digit default),
footer (bottom strip), title (largest-pt slot in the top half), eyebrow
(small text above the title), source-note (small bottom-half text), body
(everything else). Geometry thresholds assume the decompiler's 1920x1080
design space and are scaled by the declared `canvas` when it differs.

`chars` is a rough fit capacity: chars-per-line × line count from the slot's
maxwidth / maxheight box at its declared point size (0.55 em average glyph
width, 1.5 em line height).

Native-payload kind detection stays cheap and text-level: decode the carried
XML (inline `b64:` or `xml_file:` sidecar under the brand's assets root) and
look for `<c:chart` (chart), `<dgm:`/`relIds` (SmartArt), `<a:tbl` (table);
anything else — and any decode failure — is decorative `illustration` chrome.
"""
from __future__ import annotations

import base64
import math
import re
from pathlib import Path

import yaml

from feinschliff.dsl.parser import split_frontmatter
from feinschmiede.dsl.tokens import load_tokens
from feinschmiede.geometry import units
from feinschmiede.text.measure import avg_char_width_ratio
from feinschliff_builder.decompile.slotify import crosses_image_edge

# --- DSL line patterns ------------------------------------------------------
# In the FILE the slot's inner quotes are backslash-escaped:
#   text … "{{ text_1 | default(\"Annual Review\") }}"
# The default body can never contain `"` (slotify curlifies them), so a lazy
# group terminated by `\")` is unambiguous.
_TEXT_SLOT_RE = re.compile(r'\{\{\s*(text_\d+)\s*\|\s*default\(\\"(.*?)\\"\)\s*\}\}')
_IMAGE_SLOT_RE = re.compile(r'\{\{\s*(image\d*)\s*\|\s*default\(\\"(.*?)\\"\)\s*\}\}')
_XY_RE = re.compile(r"^(?:text|picture)\s+(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")
_WH_RE = re.compile(r"\s(-?\d+(?:\.\d+)?)x(-?\d+(?:\.\d+)?)(?:\s|$)")
_SIZE_RE = re.compile(r"\bsize:(\d+(?:\.\d+)?)pt\b")
_STYLE_RE = re.compile(r"\bstyle:([\w-]+)")
_MAXW_RE = re.compile(r"\bmaxwidth:(\d+(?:\.\d+)?)")
_MAXH_RE = re.compile(r"\bmaxheight:(\d+(?:\.\d+)?)")
_CANVAS_RE = re.compile(r"^canvas\s+(\d+)x(\d+)", re.M)
_NATIVE_RE = re.compile(r"^native\s+\w+\s+(.*)$")
_NATIVE_KW_RE = re.compile(r'(\w+):"((?:[^"\\]|\\.)*)"')

# Root shape/group geometry inside a carried native payload. The FIRST
# <a:xfrm> block is the root one (nested children come later); `<a:ext` with
# cx/cy attributes cannot be confused with the `<a:ext uri=…>` extension-list
# element because of the attribute names.
_XFRM_BLOCK_RE = re.compile(r"<a:xfrm\b[^>]*>(.*?)</a:xfrm>", re.S)
_XFRM_OFF_RE = re.compile(r'<a:off\s+x="(-?\d+)"\s+y="(-?\d+)"')
_XFRM_EXT_RE = re.compile(r'<a:ext\s+cx="(\d+)"\s+cy="(\d+)"')

# Standard PowerPoint 16:9 slide in EMU; declared `canvas` maps onto it.
_EMU_SLIDE_W = 12192000.0

# Illustration payloads covering more than this canvas-area share make the
# layout fixed chrome (see module docstring).
_ILLUSTRATION_AREA_GATE = 0.20

# Dense-content roles that must not land on illustration-dominated chrome.
_CHROME_GATE_AVOID = [
    "role=content-columns", "role=data-quantity", "role=data-comparison",
    "role=data-timeline", "role=concept-diagram",
]

# Image-slot `class` heuristics: canvas-area share above which an image slot
# is a content photo (`replace`), below which — or at logo-strip aspect
# ratios — it is brand chrome (`keep`).
_IMAGE_REPLACE_SHARE = 0.15
_IMAGE_KEEP_SHARE = 0.04
_IMAGE_KEEP_ASPECT_HI = 6.0   # w/h above this = horizontal logo strip
_IMAGE_KEEP_ASPECT_LO = 0.17  # w/h below this = vertical strip
_IMAGE_CLASSES = ("keep", "replace")

# Annotation fields a human/vision pass fills in; `apply_profile` preserves
# their non-empty values across re-runs.
_ANNOTATION_KEYS = ("description", "chrome_subject", "when_to_use")

# The unified slide-type vocabulary (`family`). The heuristic classifier
# assigns one; a vision pass may overrule it with `family_curated: true`,
# which `apply_profile` then preserves across re-runs.
_FAMILIES = frozenset({
    "framing", "voice", "closing", "comparison",
    "organizational", "process", "image-driven", "data",
})

# Heuristic trigger patterns (see module docstring).
_AGENDA_RE = re.compile(r"agenda|inhalt|contents", re.I)
_CLOSER_RE = re.compile(r"thank|danke|contact|q&a$", re.I)
# Use-case layout names (master-derived packs name layouts after their
# slide-master use case): the NAME is authoritative over slide position.
_TITLE_NAME_RE = re.compile(r"^(title|cover)([-_ ]|$)", re.I)
_CHAPTER_NAME_RE = re.compile(r"^(chapter|section|divider)([-_ ]|$)", re.I)
_CLOSER_NAME_RE = re.compile(r"^(end|closer|thank)([-_ ]|$)", re.I)
# Template reference sheets (howto pages, design-element samples) — never
# content or position-derived roles.
_REFERENCE_NAME_RE = re.compile(
    r"howto|how-to|instruction|sample|element|legend", re.I)

# Native pictures at or under this canvas-area share are brand marks
# (logos, stamps) — not illustration chrome; they must not trip the
# decorative-divider rule, the area gate, or the chrome_subject slot.
_MARK_AREA_SHARE = 0.03
_QUOTE_DEFAULTS = {"“", "”", '"', "„"}
_NUMERIC_RE = re.compile(r"^[\d.,%€$+−-]+")
_PAGE_NUMBER_RE = re.compile(r"^\d{1,3}$")

# Body slots at or under this default length count as "short" for the
# data-quantity (KPI wall) heuristic — long prose can start with a digit
# without being a KPI value.
_SHORT_DEFAULT_LEN = 16

# Words that never make a useful image-search keyword: English glue plus the
# template boilerplate Microsoft layouts ship with.
_QUERY_STOPWORDS = frozenset({
    "this", "that", "with", "from", "your", "have", "will", "into", "over",
    "more", "than", "them", "then", "what", "when", "where", "which", "their",
    "there", "here", "been", "were", "also", "some", "very", "just", "only",
    "click", "edit", "master", "presentation", "headline", "placeholder",
    "lorem", "ipsum", "slide", "layout", "page", "text", "subtitle", "style",
    "styles", "title",
})


# --- DSL extraction ---------------------------------------------------------

def _parse_canvas(body: str) -> tuple[float, float]:
    m = _CANVAS_RE.search(body)
    return (float(m.group(1)), float(m.group(2))) if m else (1920.0, 1080.0)


def _parse_text_slots(body: str) -> list[dict]:
    """Each slotified `text` line → {name, default, x, y, pt, style, maxw, maxh}."""
    slots: list[dict] = []
    for line in body.splitlines():
        if not line.startswith("text "):
            continue
        m = _TEXT_SLOT_RE.search(line)
        if m is None:
            continue
        xy = _XY_RE.match(line)
        slots.append({
            "name": m.group(1),
            "default": m.group(2),
            "x": float(xy.group(1)) if xy else 0.0,
            "y": float(xy.group(2)) if xy else 0.0,
            "pt": float(_SIZE_RE.search(line).group(1)) if _SIZE_RE.search(line) else 18.0,
            "style": _STYLE_RE.search(line).group(1) if _STYLE_RE.search(line) else "",
            "maxw": float(_MAXW_RE.search(line).group(1)) if _MAXW_RE.search(line) else 400.0,
            "maxh": float(_MAXH_RE.search(line).group(1)) if _MAXH_RE.search(line) else 100.0,
        })
    return slots


def _parse_image_slots(body: str) -> list[dict]:
    """Each slotified `picture` line → {name, x, y, w, h}."""
    slots: list[dict] = []
    for line in body.splitlines():
        if not line.startswith("picture "):
            continue
        m = _IMAGE_SLOT_RE.search(line)
        if m is None:
            continue
        wh = _WH_RE.search(line.split('path:', 1)[0])
        xy = _XY_RE.match(line)
        slots.append({
            "name": m.group(1),
            "x": float(xy.group(1)) if xy else 0.0,
            "y": float(xy.group(2)) if xy else 0.0,
            "w": float(wh.group(1)) if wh else 0.0,
            "h": float(wh.group(2)) if wh else 0.0,
        })
    return slots


def _decode_native_xml(kwargs: dict[str, str], asset_root: Path | None) -> str | None:
    """Decode a native payload's carried XML (inline b64 or sidecar file);
    None on any failure — callers treat that as undecodable chrome."""
    try:
        if kwargs.get("b64"):
            return base64.b64decode(kwargs["b64"]).decode("utf-8", "replace")
        if kwargs.get("xml_file") and asset_root is not None:
            return (asset_root / kwargs["xml_file"]).read_text(
                encoding="utf-8", errors="replace")
    except Exception:
        pass
    return None


def _native_kind(xml: str | None) -> str:
    """Cheap text-level kind sniff over a native payload's carried XML."""
    if xml is None:
        return "illustration"
    if "graphicFrame" in xml and "<c:chart" in xml:
        return "chart"
    if "<dgm:" in xml or "relIds" in xml:
        return "smartart"
    if "<a:tbl" in xml:
        return "table"
    return "illustration"


_BAKED_TEXT_RE = re.compile(r"<a:t>([^<]+)</a:t>")


def _has_baked_text(xml: str) -> bool:
    """True when the payload carries non-whitespace `<a:t>` runs — chrome
    with its own labels baked in (a chevron flow with STEP texts). Binding
    the layout's text slots overprints those labels, so the profile flags
    it (`chrome_text`) for the picker's baked-text guard. Runs that the
    native slotify pass already rewrote to `{{ text_N | default(…) }}`
    templates are NOT baked — they bind like any other slot."""
    return any(t.strip() and "{{" not in t for t in _BAKED_TEXT_RE.findall(xml))


_NATIVE_SLOT_RE = re.compile(r'\{\{\s*(text_\d+)\s*\|\s*default\("([^"]*)"\)\s*\}\}')


def _parse_native_slots(natives: list[tuple[str, str | None]]) -> list[dict]:
    """Slot templates the native slotify pass planted inside payload XML.

    Each -> {name, default}. The geometry is the carrying native's box, so
    these get no per-slot rect (and no slot_warnings entry)."""
    slots: list[dict] = []
    for _kind, xml in natives:
        if not xml:
            continue
        for m in _NATIVE_SLOT_RE.finditer(xml):
            slots.append({"name": m.group(1), "default": m.group(2)})
    return slots


def _parse_natives(body: str, asset_root: Path | None) -> list[tuple[str, str | None]]:
    """Each `native` line → (kind, decoded XML or None)."""
    natives: list[tuple[str, str | None]] = []
    for line in body.splitlines():
        m = _NATIVE_RE.match(line)
        if m is None:
            continue
        kwargs = dict(_NATIVE_KW_RE.findall(m.group(1)))
        xml = _decode_native_xml(kwargs, asset_root)
        natives.append((_native_kind(xml), xml))
    return natives


def _demote_marks(
    natives: list[tuple[str, str | None]], canvas_w: float, canvas_h: float,
) -> list[tuple[str, str | None]]:
    """Re-kind tiny illustration natives (≤ _MARK_AREA_SHARE of the canvas)
    as 'mark' — flattened logo chrome on every slide must not classify as
    decorative illustration."""
    scale = canvas_w / _EMU_SLIDE_W
    out = []
    for kind, xml in natives:
        if kind == "illustration" and xml is not None:
            xfrm = _root_xfrm_emu(xml)
            if xfrm is not None:
                _x, _y, cx, cy = xfrm
                share = (cx * scale) * (cy * scale) / (canvas_w * canvas_h)
                if share <= _MARK_AREA_SHARE:
                    kind = "mark"
        out.append((kind, xml))
    return out


def _root_xfrm_emu(xml: str) -> tuple[float, float, float, float] | None:
    """(x, y, cx, cy) of the payload's root `<a:xfrm>` in EMU, or None when
    the root shape/group carries no usable geometry."""
    block = _XFRM_BLOCK_RE.search(xml)
    if block is None:
        return None
    off = _XFRM_OFF_RE.search(block.group(1))
    ext = _XFRM_EXT_RE.search(block.group(1))
    if off is None or ext is None:
        return None
    return (float(off.group(1)), float(off.group(2)),
            float(ext.group(1)), float(ext.group(2)))


def _illustration_area_share(
    natives: list[tuple[str, str | None]], canvas_w: float, canvas_h: float,
) -> float | None:
    """Canvas-area share covered by native ILLUSTRATION payloads (clipped to
    the slide). None when any illustration geometry cannot be decoded — the
    caller then falls back to the old slot-count gate for the layout."""
    scale = canvas_w / _EMU_SLIDE_W
    total = 0.0
    for kind, xml in natives:
        if kind != "illustration":
            continue
        if xml is None:
            return None
        xfrm = _root_xfrm_emu(xml)
        if xfrm is None:
            return None
        x, y, w, h = (v * scale for v in xfrm)
        vis_w = min(x + w, canvas_w) - max(x, 0.0)
        vis_h = min(y + h, canvas_h) - max(y, 0.0)
        if vis_w > 0 and vis_h > 0:
            total += vis_w * vis_h
    return total / (canvas_w * canvas_h)


def _n(v: float) -> str:
    """Compact number: integral floats print as ints, others trimmed."""
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _element_tree_scale(canvas_w: float, width_emu: float) -> float:
    """EMU→canvas-px for native geometry: the pack's REAL slide width when
    known — the 13.33in default constant mis-places natives on 12in decks
    (a 0.9x drift that broke overlay/exclusion geometry downstream)."""
    return canvas_w / (width_emu or _EMU_SLIDE_W)


def _element_tree(
    texts: list[dict],
    images: list[dict],
    natives: list[tuple[str, str | None]],
    *,
    width_emu: float = 0.0,
    slot_roles: dict[str, str],
    image_classes: dict[str, str],
    canvas_w: float,
) -> list[str]:
    """One compact line per slide element, sorted into reading order
    (top→bottom, left→right) — the structural 'what is where' a deck
    planner reads alongside `description`:

        native illustration @0,0 960x540 baked-text
        image image class=replace @1008,0 912x1080
        text text_1 role=title @76,76 922x122 20pt

    Natives whose root geometry cannot be decoded sort last and carry no
    `@x,y wxh` part. Purely mechanical — regenerated on every run.
    """
    scale = _element_tree_scale(canvas_w, width_emu)
    entries: list[tuple[float, float, str]] = []
    for kind, xml in natives:
        line = f"native {kind}"
        x = y = float("inf")
        xfrm = _root_xfrm_emu(xml) if xml is not None else None
        if xfrm is not None:
            ex, ey, ew, eh = (v * scale for v in xfrm)
            line += f" @{_n(ex)},{_n(ey)} {_n(ew)}x{_n(eh)}"
            x, y = ex, ey
        if (xml is not None and kind in ("illustration", "mark")
                and _has_baked_text(xml)):
            line += " baked-text"
        entries.append((y, x, line))
    for i in images:
        entries.append((i["y"], i["x"], (
            f"image {i['name']} class={image_classes.get(i['name'], 'replace')}"
            f" @{_n(i['x'])},{_n(i['y'])} {_n(i['w'])}x{_n(i['h'])}"
        )))
    for t in texts:
        entries.append((t["y"], t["x"], (
            f"text {t['name']} role={slot_roles[t['name']]}"
            f" @{_n(t['x'])},{_n(t['y'])} {_n(t['maxw'])}x{_n(t['maxh'])}"
            f" {_n(t['pt'])}pt"
        )))
    entries.sort(key=lambda e: (e[0], e[1]))
    return [line for _y, _x, line in entries]


# --- Slot roles -------------------------------------------------------------

def _char_capacity(slot: dict, *, px_per_pt: float = 2.0, tokens=None,
                   face: str | None = None) -> int:
    """Honest capacity of the slot box: measured chars/line × FULL lines.

    Char width: measured avg glyph advance for the resolved brand face
    (fallback 0.55em). pt→px: the pack's real slide scale — never the CSS
    96/72-DPI convention. 0 rows is an honest 0: a box shorter than one
    line holds no wrapped text (slot_warnings carries IMPOSSIBLE_BOX).
    Exception: a borderline-tight box that passes the soft-clip grace
    (_fits_one_line_soft) budgets one row — coherent with IMPOSSIBLE_BOX."""
    line_height, style_face = _style_metrics(slot.get("style", ""), tokens)
    size_px = slot["pt"] * px_per_pt
    if size_px <= 0:
        return 0
    cols = math.floor(slot["maxw"] / (_char_ratio(face or style_face) * size_px))
    rows = math.floor(slot["maxh"] / (line_height * size_px))
    if rows == 0 and _fits_one_line_soft(line_height * size_px, slot["maxh"]):
        # Borderline-tight box: one soft-clipped line renders fine (same
        # grace as the IMPOSSIBLE_BOX lint) — budget a single row.
        rows = 1
    return max(0, cols) * max(0, rows)


def _assign_slot_roles(texts: list[dict], canvas_h: float) -> dict[str, str]:
    """slot name → page-number | footer | title | eyebrow | source-note | body."""
    sy = canvas_h / 1080.0
    roles: dict[str, str] = {}
    for t in texts:
        if _PAGE_NUMBER_RE.fullmatch(t["default"].strip()):
            roles[t["name"]] = "page-number"
    for t in texts:
        if t["name"] in roles:
            continue
        if t["y"] >= 980 * sy or (t["style"] in ("body-sm", "detail")
                                  and t["y"] >= 900 * sy):
            roles[t["name"]] = "footer"
    # Title: largest-pt slot in the top half; ties break toward the top edge.
    candidates = [t for t in texts if t["name"] not in roles and t["y"] < 540 * sy]
    title = max(candidates, key=lambda t: (t["pt"], -t["y"]), default=None)
    if title is not None:
        roles[title["name"]] = "title"
    for t in texts:
        if t["name"] in roles:
            continue
        if title is not None and t["pt"] <= 18 and t["y"] < title["y"]:
            roles[t["name"]] = "eyebrow"
        elif t["y"] >= 540 * sy and t["pt"] <= 12:
            roles[t["name"]] = "source-note"
        else:
            roles[t["name"]] = "body"
    return roles


_MIN_CHARS_PER_LINE = 8
_FALLBACK_CHAR_RATIO = 0.55

# PPT soft-clips a line that exceeds its box by up to ~10% without visual
# damage (native bboxes routinely run that tight). Shared by the
# IMPOSSIBLE_BOX lint and _char_capacity so the two can never disagree on
# whether a box holds one line.
_LINE_FIT_GRACE = 1.10


def _fits_one_line_soft(line_h_px: float, maxh: float) -> bool:
    return maxh > 0 and line_h_px <= maxh * _LINE_FIT_GRACE + 0.5

# Roles that legitimately hold a digit or fixed short string — exempt from
# the NARROW_BOX chars-per-line lint.
_NARROW_BOX_EXEMPT_ROLES = frozenset({"page-number", "footer", "source-note"})


def _style_metrics(style_name: str, tokens) -> tuple[float, str | None]:
    """(line_height, primary_face) for a style bundle; (1.2, None) when the
    pack tokens are unavailable or the style doesn't resolve."""
    if tokens is None or not style_name:
        return 1.2, None
    try:
        resolved = tokens.resolve_style(style_name)
    except (KeyError, ValueError):
        return 1.2, None
    face = resolved.font_family[0] if resolved.font_family else None
    return resolved.line_height, face


def _char_ratio(face: str | None) -> float:
    if face:
        measured = avg_char_width_ratio(face)
        if measured:
            return measured
    return _FALLBACK_CHAR_RATIO


def _boxes_overlap(a: dict, b: dict) -> bool:
    return (a["x"] < b["x"] + b["maxw"] and b["x"] < a["x"] + a["maxw"]
            and a["y"] < b["y"] + b["maxh"] and b["y"] < a["y"] + a["maxh"])


def _slot_warnings(
    texts: list[dict],
    *,
    px_per_pt: float,
    tokens=None,
    slot_roles: dict[str, str] | None = None,
    images: list[dict] | None = None,
) -> dict[str, list[str]]:
    """Static box-sanity lint over slotified text nodes — content-free, only
    declared geometry and resolved type size. Results land in frontmatter
    `slot_warnings:` (planning LLMs and /improve-brand read them) and in the
    slotify summary print.

    ``slot_roles`` is used to suppress false positives for intentionally
    compact chrome slots:
    - NARROW_BOX is skipped for page-number / footer / source-note roles
      (these hold a digit or a short fixed string — 7 chars/line is fine).
    - IMPOSSIBLE_BOX is skipped when the default is 1-2 chars (decorative
      display glyphs such as oversized quotation marks).

    ``images`` (image slot geometry dicts from ``_parse_image_slots``) is
    used to detect TEXT_OVER_IMAGE: text boxes that partially cross a picture
    slot's edge (decompile artifact — the bound copy wraps onto the photo).
    Fully-contained overlays (intentional titles on full-bleed photos) are
    skipped.
    """
    out: dict[str, list[str]] = {}

    def _add(name: str, msg: str) -> None:
        out.setdefault(name, []).append(msg)

    for t in texts:
        size_px = t["pt"] * px_per_pt
        if size_px <= 0:
            continue
        line_height, face = _style_metrics(t["style"], tokens)
        line_h_px = size_px * line_height
        # 1-2 char defaults are decorative display glyphs (oversized quote marks
        # etc.) — overflow is the design.
        is_decorative_glyph = len(t["default"].strip()) <= 2
        # Grace shared with _char_capacity via _fits_one_line_soft / _LINE_FIT_GRACE.
        if t["maxh"] > 0 and not _fits_one_line_soft(line_h_px, t["maxh"]) \
                and not is_decorative_glyph:
            _add(t["name"], (
                f"IMPOSSIBLE_BOX: one line at {t['pt']:g}pt is ~{line_h_px:.0f}px "
                f"tall but the box is {t['maxh']:g}px"
            ))
        role = (slot_roles or {}).get(t["name"], "body")
        cols = math.floor(t["maxw"] / (_char_ratio(face) * size_px))
        # Skip NARROW_BOX for slots whose role is page-number / footer /
        # source-note — these hold a digit or a fixed short string by design.
        if (0 < cols < _MIN_CHARS_PER_LINE
                and role not in _NARROW_BOX_EXEMPT_ROLES):
            _add(t["name"], (
                f"NARROW_BOX: ~{cols} chars/line at {t['pt']:g}pt in a "
                f"{t['maxw']:g}px-wide box"
            ))
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            if _boxes_overlap(a, b):
                msg = (f"SLOT_BOX_OVERLAP: declared boxes of {a['name']} and "
                       f"{b['name']} intersect")
                _add(a["name"], msg)
                _add(b["name"], msg)
    # TEXT_OVER_IMAGE: text box partially crosses a picture slot's edge.
    # Fully-contained overlays (intentional titles on full-bleed photos) are
    # exempt — only partial overlaps (the text wraps off the free region).
    for t in texts:
        for img in images or []:
            if crosses_image_edge(t, img):
                _add(t["name"], (
                    f"TEXT_OVER_IMAGE: text box crosses the edge of picture "
                    f"'{img['name']}' ({img['w']:g}x{img['h']:g} at "
                    f"{img['x']:g},{img['y']:g}) — bound copy will wrap onto "
                    f"the image"
                ))
    return out


def _chrome_bboxes(natives, canvas_w: float, width_emu: float) -> list[list[int]]:
    """Design-px [x,y,w,h] for each decodable native chrome payload, scaled
    with the pack's REAL slide width (element_tree's fixed 12192000 scale is
    ~11% off on 12in packs — kept untouched there, correct here)."""
    scale = canvas_w / (width_emu or _EMU_SLIDE_W)
    boxes: list[list[int]] = []
    for _kind, xml in natives:
        xfrm = _root_xfrm_emu(xml) if xml is not None else None
        if xfrm is not None:
            x, y, w, h = (v * scale for v in xfrm)
            boxes.append([round(x), round(y), round(w), round(h)])
    return boxes


def _image_class(img: dict, canvas_w: float, canvas_h: float) -> str:
    """Heuristic content-photo vs brand-chrome call for an image slot:
    big → `replace`; tiny or logo-strip aspect → `keep`; else `replace`."""
    share = (img["w"] * img["h"]) / (canvas_w * canvas_h)
    if share > _IMAGE_REPLACE_SHARE:
        return "replace"
    aspect = img["w"] / img["h"] if img["h"] > 0 else float("inf")
    if (share < _IMAGE_KEEP_SHARE or aspect > _IMAGE_KEEP_ASPECT_HI
            or aspect < _IMAGE_KEEP_ASPECT_LO):
        return "keep"
    return "replace"


# --- Image queries ----------------------------------------------------------

def _keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z]+", text)
    out: list[str] = []
    for w in words:
        lw = w.lower()
        if len(lw) > 3 and lw not in _QUERY_STOPWORDS and lw not in out:
            out.append(lw)
    return out


def _image_query(layout_name: str, title_default: str) -> str:
    """2-4 lowercase search keywords for an image slot. Layered fallback:
    layout-name + title words → bare layout-name tokens → a generic query."""
    kws = _keywords(layout_name.replace("-", " ").replace("_", " ") + " "
                    + title_default.replace("\\n", " "))[:4]
    if len(kws) < 2:
        raw = [t.lower() for t in re.split(r"[^A-Za-z]+", layout_name) if t]
        kws = list(dict.fromkeys(kws + raw))[:4]
    if not kws:
        return "abstract background"
    return " ".join(kws)


# --- Classification ---------------------------------------------------------

def classify_layout(
    dsl_text: str,
    *,
    layout_name: str,
    slide_index: int,
    total_slides: int,
    asset_root: Path | None = None,
    brand_dir: Path | None = None,
) -> dict:
    """Classify one slotified layout into its frontmatter profile dict.

    The returned dict round-trips through YAML into a fence that
    `feinschliff.layout_profile.parse_profile` accepts; the extra keys
    (`family`, `slots`, `image_queries`, …) are tolerated/ignored there and
    consumed by deck planning instead.

    ``brand_dir`` is the pack root directory (contains ``tokens.json``).
    When supplied, slot_warnings uses the pack's real px/pt scale and
    chrome_bboxes uses the real slide width in EMU.
    """
    _, body = split_frontmatter(dsl_text)  # tolerate re-runs on profiled files
    # Layout fingerprint: short SHA-1 of the body so the picker / emitter
    # can detect drift and silent name shadowing across packs. `source` is
    # the pack name when known. Two `cover.slide.dsl` in different packs
    # have the same name but different `source_hash` — that tuple is the
    # unambiguous identity. Cheap (under a millisecond per layout).
    import hashlib as _hashlib
    source_hash = _hashlib.sha1(body.encode("utf-8")).hexdigest()[:12]
    canvas_w, canvas_h = _parse_canvas(body)
    tokens = None
    width_emu = 0.0
    if brand_dir is not None and (brand_dir / "tokens.json").exists():
        try:
            tokens = load_tokens(brand_dir)
            width_emu = float(tokens.slide("width_emu") or 0)
        except Exception:
            tokens = None
    px_per_pt = ((canvas_w * units.EMU_PER_PT / width_emu) if width_emu
                 else 1.0 / units.PX_TO_PT_BASELINE)
    sx, sy = canvas_w / 1920.0, canvas_h / 1080.0
    texts = _parse_text_slots(body)
    images = _parse_image_slots(body)
    natives = _demote_marks(_parse_natives(body, asset_root), canvas_w, canvas_h)
    native_kinds = [k for k, _xml in natives]
    native_slots = _parse_native_slots(natives)
    slot_roles = _assign_slot_roles(texts, canvas_h)

    title_slot = next((t for t in texts if slot_roles[t["name"]] == "title"), None)
    title_default = (title_slot or {}).get("default", "")
    body_slots = [t for t in texts if slot_roles[t["name"]] == "body"]
    n_body = len(body_slots)
    # "Visible" text = everything that is not running chrome (footer strip,
    # page number) — what a reader actually parses on the slide.
    n_visible = sum(1 for t in texts
                    if slot_roles[t["name"]] not in ("footer", "page-number"))
    full_bleed = any(i["w"] >= 1800 * sx and i["h"] >= 1000 * sy for i in images)
    kinds = set(native_kinds)

    role = "content-columns"
    family = "organizational"
    data_band = "none"
    comparison = False
    variety_exempt = False
    fixed_chrome = False
    when_not_to_use: list[str] | None = None

    short_body = [t for t in body_slots
                  if len(t["default"]) <= _SHORT_DEFAULT_LEN]
    numeric_short = [t for t in short_body if _NUMERIC_RE.match(t["default"].strip())]

    if slide_index == 1 or _TITLE_NAME_RE.search(layout_name):
        role, family, variety_exempt = "title-primary", "framing", True
    elif _CHAPTER_NAME_RE.search(layout_name):
        role, family, variety_exempt = "chapter-opener", "framing", True
    elif _AGENDA_RE.search(title_default) or _AGENDA_RE.search(layout_name):
        role, family, variety_exempt = "agenda", "framing", True
    elif _REFERENCE_NAME_RE.search(layout_name):
        role, family = "reference", "organizational"
    elif (any(t["default"].strip() in _QUOTE_DEFAULTS for t in texts)
          or "style:quote" in body):
        role, family = "quote", "voice"
    elif (slide_index == total_slides
          or _CLOSER_RE.search(title_default.strip())
          or _CLOSER_NAME_RE.search(layout_name)):
        role, family, variety_exempt = "closer", "closing", True
    elif "chart" in kinds:
        role, family, data_band, comparison = (
            "data-comparison", "comparison", "chart", True)
    elif "table" in kinds:
        role, family, data_band = "reference", "organizational", "table"
    elif "smartart" in kinds:
        role, family = "concept-diagram", "process"
    elif "illustration" in kinds and n_visible <= 2:
        # Decorative divider chrome — don't put dense facts on it.
        role, family = "chapter-opener", "framing"
    elif full_bleed and n_visible <= 2:
        role, family = "title-with-visual", "image-driven"
    elif (len(short_body) >= 4
          and len(numeric_short) * 2 >= len(short_body)):
        role, family, data_band = "data-quantity", "data", "kpi"
    elif n_body >= 3:
        role, family = "content-columns", "organizational"

    # Decorative-divider gate: any chapter-opener carrying illustration
    # chrome with ≤2 visible slots is fixed chrome — regardless of whether
    # the role came from rule 8 or a use-case layout name.
    if (role == "chapter-opener" and "illustration" in kinds
            and n_visible <= 2):
        fixed_chrome = True
        when_not_to_use = [
            "role=content-columns", "role=data-quantity", "role=data-comparison",
        ]

    # Area-based fixed-chrome gate (additive to rule 8 — role stays as
    # classified). None = some illustration geometry was undecodable; the
    # old slot-count rule above already covered that layout.
    illu_share = _illustration_area_share(natives, canvas_w, canvas_h)
    if illu_share is not None and illu_share > _ILLUSTRATION_AREA_GATE:
        fixed_chrome = True
        base = when_not_to_use or []
        when_not_to_use = base + [r for r in _CHROME_GATE_AVOID
                                  if r not in base]

    # Baked-text gate: decorative chrome whose XML carries its own visible
    # `<a:t>` labels. Independent of area/slot count — even a mark-sized
    # chevron with baked STEP texts makes the overlapping text slots
    # un-rebindable (new copy renders over the baked labels). Marks count
    # too: small ≠ text-free.
    chrome_text = any(
        kind in ("illustration", "mark") and xml is not None
        and _has_baked_text(xml)
        for kind, xml in natives
    )

    if role in ("title-primary", "chapter-opener", "quote", "closer"):
        ideal_count = [1, 2]
    else:
        lo = max(1, n_body)
        ideal_count = [lo, max(n_body, lo)]

    profile: dict = {
        "role": role,
        "ideal_count": ideal_count,
        "data_band": data_band,
        "comparison": comparison,
    }
    if variety_exempt:
        profile["variety_exempt"] = True
    if when_not_to_use:
        profile["when_not_to_use"] = when_not_to_use
    profile["family"] = family
    if fixed_chrome:
        profile["fixed_chrome"] = True
    if chrome_text:
        profile["chrome_text"] = True
    # Annotation slots for a later human/vision pass (see apply_profile —
    # non-empty values survive regeneration).
    profile["description"] = ""
    profile["when_to_use"] = ""
    if "illustration" in kinds:
        profile["chrome_subject"] = ""
    if native_kinds:
        counts = {k: native_kinds.count(k) for k in sorted(kinds)}
        profile["chrome_note"] = (
            "carries native source chrome verbatim: "
            + ", ".join(f"{n} {k}" for k, n in counts.items())
            + ("; baked text" if chrome_text else "")
        )
    profile["slide_index"] = slide_index
    if texts or images or native_slots:
        profile["slots"] = {
            t["name"]: {
                "role": slot_roles[t["name"]],
                "chars": _char_capacity(t, px_per_pt=px_per_pt, tokens=tokens),
                # Preview only — truncated so a lorem paragraph cannot bloat
                # the frontmatter; the authoritative default stays in the DSL.
                "default": (t["default"][:77] + "…"
                            if len(t["default"]) > 78 else t["default"]),
            }
            for t in texts
        }
        for i in images:
            profile["slots"][i["name"]] = {
                "role": "image",
                "class": _image_class(i, canvas_w, canvas_h),
            }
        for ns in native_slots:
            profile["slots"][ns["name"]] = {
                "role": "native-text",
                "chars": len(ns["default"]),
                "default": (ns["default"][:77] + "…"
                            if len(ns["default"]) > 78 else ns["default"]),
            }
        warnings = _slot_warnings(
            texts, px_per_pt=px_per_pt, tokens=tokens, slot_roles=slot_roles,
            images=images)
        if warnings:
            profile["slot_warnings"] = warnings
    if images:
        query = _image_query(layout_name, title_default)
        profile["image_queries"] = {i["name"]: query for i in images}
    image_classes = {
        i["name"]: _image_class(i, canvas_w, canvas_h) for i in images
    }
    bboxes = _chrome_bboxes(natives, canvas_w, width_emu)
    if bboxes:
        profile["chrome_bboxes"] = bboxes
    if texts or images or natives:
        profile["element_tree"] = _element_tree(
            texts, images, natives, width_emu=width_emu,
            slot_roles=slot_roles, image_classes=image_classes,
            canvas_w=canvas_w)
    profile["source_hash"] = source_hash
    if brand_dir is not None:
        profile["source"] = brand_dir.name
    return profile


# --- Frontmatter application ------------------------------------------------

def _strip_fence(dsl_text: str) -> str:
    """Drop a leading `--- … ---` fence (preceded only by blank lines),
    returning everything after it byte-identical. No fence → text unchanged."""
    lines = dsl_text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or lines[i].strip() != "---":
        return dsl_text
    for j in range(i + 1, len(lines)):
        if lines[j].strip() == "---":
            return "".join(lines[j + 1:])
    return dsl_text  # unterminated fence — leave the document alone


def _merge_annotations(profile: dict, old_fm: str | None) -> dict:
    """Carry annotation values from an existing fence into a freshly
    generated *profile*: non-empty `description` / `chrome_subject` and
    per-image-slot `class` overrides survive a re-run (a vision-annotation
    pass must never be wiped by regeneration); every mechanical field —
    role, ideal_count, slots geometry, … — comes from the new profile."""
    if old_fm is None:
        return profile
    try:
        old = yaml.safe_load(old_fm)
    except yaml.YAMLError:
        return profile
    if not isinstance(old, dict):
        return profile
    merged = dict(profile)
    for key in _ANNOTATION_KEYS:
        val = old.get(key)
        # Only keys the new profile still emits — a chrome_subject for an
        # illustration that no longer exists must not be resurrected.
        if key in merged and isinstance(val, str) and val.strip():
            merged[key] = val
    # Curated slide-type: a vision pass may overrule the heuristic `family`,
    # but only an explicit `family_curated: true` marker survives — a bare
    # hand-edit of `family` is mechanical tampering and regenerates.
    if (old.get("family_curated") is True
            and old.get("family") in _FAMILIES):
        merged["family"] = old["family"]
        merged["family_curated"] = True
    old_slots = old.get("slots")
    if isinstance(old_slots, dict) and isinstance(merged.get("slots"), dict):
        merged["slots"] = {
            name: dict(entry) if isinstance(entry, dict) else entry
            for name, entry in merged["slots"].items()
        }
        for name, entry in merged["slots"].items():
            if not (isinstance(entry, dict) and "class" in entry):
                continue
            prev = old_slots.get(name)
            if isinstance(prev, dict) and prev.get("class") in _IMAGE_CLASSES:
                entry["class"] = prev["class"]
    return merged


def _dump_fence(profile: dict) -> str:
    return yaml.safe_dump(profile, sort_keys=False, allow_unicode=True,
                          default_flow_style=None, width=120)


def apply_profile(dsl_text: str, profile: dict) -> str:
    """Prepend (or merge-replace) the YAML frontmatter fence; the body after
    the fence stays byte-identical, so re-running the generator is
    idempotent. An existing fence is MERGED, not clobbered: annotation
    fields survive per :func:`_merge_annotations`."""
    old_fm, _ = split_frontmatter(dsl_text)
    fm = _dump_fence(_merge_annotations(profile, old_fm))
    return "---\n" + fm + "---\n" + _strip_fence(dsl_text)


# --- Deck map ---------------------------------------------------------------

def derive_deck_map(profiles: dict[str, dict]) -> dict:
    """Reduce `{layout_name: profile}` to the deck-planning role map written
    to `<brand>/deck-map.yaml`: one cover/agenda/quote/closer, the
    chapter-opener section dividers, and everything else as content in slide
    order. Keys without a matching layout are omitted (except `content`)."""
    def idx(name: str) -> int:
        return int(profiles[name].get("slide_index", 10 ** 9))

    ordered = sorted(profiles, key=lambda n: (idx(n), n))
    by_role: dict[str, list[str]] = {}
    for name in ordered:
        by_role.setdefault(profiles[name]["role"], []).append(name)

    deck_map: dict = {}
    used: set[str] = set()
    covers = by_role.get("title-primary", [])
    if covers:
        deck_map["cover"] = covers[0]  # lowest slide index wins
        used.add(covers[0])
    agendas = by_role.get("agenda", [])
    if agendas:
        deck_map["agenda"] = agendas[0]
        used.add(agendas[0])
    sections = by_role.get("chapter-opener", [])
    if sections:
        deck_map["section"] = sections
        used.update(sections)
    quotes = by_role.get("quote", [])
    if quotes:
        deck_map["quote"] = quotes[0]
        used.add(quotes[0])
    closers = by_role.get("closer", [])
    if closers:
        deck_map["closer"] = closers[-1]  # highest slide index wins
        used.add(closers[-1])
    deck_map["content"] = [n for n in ordered if n not in used]
    return deck_map


# --- Annotation CLI -----------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """`python -m feinschliff_builder.decompile.layout_profile_gen annotate
    <layout.slide.dsl> [--description …] [--chrome-subject …]
    [--image-class slot=keep|replace …]` — update just the annotation fields
    in an EXISTING frontmatter fence. Creating the fence is the generator's
    job (feinschliff-builder slotify), not this command's."""
    import argparse
    import sys

    ap = argparse.ArgumentParser(prog="layout_profile_gen")
    sub = ap.add_subparsers(dest="command", required=True)
    an = sub.add_parser("annotate", help="fill the vision-annotation fields")
    an.add_argument("layout", type=Path, help="profiled .slide.dsl file")
    an.add_argument("--description", help="one line: what is on this slide")
    an.add_argument("--chrome-subject",
                    help="what the native illustration depicts")
    an.add_argument("--when-to-use",
                    help="one line: when a planner should pick this layout")
    an.add_argument("--family",
                    help="curated slide-type override (sets family_curated); "
                         "one of: " + ", ".join(sorted(_FAMILIES)))
    an.add_argument("--image-class", action="append", default=[],
                    metavar="SLOT=keep|replace",
                    help="override an image slot's class (repeatable)")
    args = ap.parse_args(argv)

    try:
        text = args.layout.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"{args.layout}: cannot read layout file: {exc}", file=sys.stderr)
        return 2
    fm, _ = split_frontmatter(text)
    try:
        profile = yaml.safe_load(fm) if fm is not None else None
    except yaml.YAMLError:
        profile = None
    if not isinstance(profile, dict):
        print(f"{args.layout}: no parseable frontmatter fence — run the "
              "profile generator first; `annotate` only updates its fields.",
              file=sys.stderr)
        return 2
    if args.description is not None:
        profile["description"] = args.description
    if args.chrome_subject is not None:
        profile["chrome_subject"] = args.chrome_subject
    if args.when_to_use is not None:
        profile["when_to_use"] = args.when_to_use
    if args.family is not None:
        if args.family not in _FAMILIES:
            print(f"--family {args.family!r}: expected one of "
                  + ", ".join(sorted(_FAMILIES)), file=sys.stderr)
            return 2
        profile["family"] = args.family
        profile["family_curated"] = True
    for spec in args.image_class:
        slot, sep, cls = spec.partition("=")
        entry = profile.get("slots", {}).get(slot)
        if not sep or cls not in _IMAGE_CLASSES or not isinstance(entry, dict):
            print(f"--image-class {spec!r}: expected <existing image slot>="
                  f"{'|'.join(_IMAGE_CLASSES)}", file=sys.stderr)
            return 2
        entry["class"] = cls
    args.layout.write_text("---\n" + _dump_fence(profile) + "---\n"
                           + _strip_fence(text), encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover — exercised via main() in tests
    raise SystemExit(main())

"""Slotify pass over decompiled `.slide.dsl` layouts.

The hybrid decompiler emits slide-faithful layouts whose text is LITERAL —
right for measuring decompile fidelity, useless as a fillable template. This
pass rewrites every literal text label into

    text … "{{ text_N | default(\"<original literal>\") }}"

so the layout becomes a real template: a bare build (empty ctx) renders the
original showcase copy via the `default(…)` filter, and a deck build binds
`text_1..text_N` in ctx to replace it. Picture placeholders are already
slotified at decompile time (`path:"{{ image | default(\"…\") }}"`); native
chrome (logos, custGeom decoration) intentionally stays fixed.

Grammar constraints honoured (see feinschliff/dsl/expander.py):
  * `_DEFAULT_FILTER_RE` allows no ASCII `"` inside default("…") — escaped
    quotes in the source literal are typographically curlified (“…”).
  * `_SLOT_RE` bodies cannot contain `{`/`}` — labels with braces stay
    literal rather than emitting a slot that cannot parse.

Slot numbering is per-file, in line order: text_1, text_2, …
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# A top-level text primitive whose trailing bare-quoted token is the label.
# Group 1 = everything up to the opening quote, group 2 = raw escaped label.
_TEXT_LINE_RE = re.compile(r'^(text\b[^"]*)"((?:[^"\\]|\\.)*)"\s*$')

# --- Geometry helpers (shared with layout_profile_gen) ----------------------

# X,Y and WxH patterns for `picture` and slot-bearing `text` lines.
_GEO_XY_RE = re.compile(r"^(?:text|picture)\s+(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")
_GEO_WH_RE = re.compile(r"\s(-?\d+(?:\.\d+)?)x(-?\d+(?:\.\d+)?)(?:\s|$)")
_GEO_MAXW_RE = re.compile(r"\bmaxwidth:(\d+(?:\.\d+)?)")
_GEO_MAXH_RE = re.compile(r"\bmaxheight:(\d+(?:\.\d+)?)")
_GEO_TEXT_SLOT_RE = re.compile(r"\{\{\s*(text_\d+)\s*\|")
_GEO_IMAGE_SLOT_RE = re.compile(r"\{\{\s*image\w*\s*\|")

# Overlaps must exceed this many design-px on BOTH axes to count — kissing
# edges and 1-2 px decompile jitter are not collisions.
IMAGE_OVERLAP_EPSILON = 8.0


def crosses_image_edge(t: dict, img: dict) -> bool:
    """True when a text box PARTIALLY overlaps a picture box.

    A text box fully inside the picture is an intentional overlay
    (chapter openers, captions on photos) and returns False.

    ``t``   — {x, y, maxw, maxh} text descriptor.
    ``img`` — {x, y, w, h} picture descriptor.

    Exported publicly so layout_profile_gen can import it.
    """
    ix0, iy0 = img["x"], img["y"]
    ix1, iy1 = ix0 + img["w"], iy0 + img["h"]
    tx0, ty0 = t["x"], t["y"]
    tx1, ty1 = tx0 + t["maxw"], ty0 + t["maxh"]
    overlap_w = min(tx1, ix1) - max(tx0, ix0)
    overlap_h = min(ty1, iy1) - max(ty0, iy0)
    if overlap_w <= IMAGE_OVERLAP_EPSILON or overlap_h <= IMAGE_OVERLAP_EPSILON:
        return False
    contained = (
        tx0 >= ix0 - IMAGE_OVERLAP_EPSILON
        and ty0 >= iy0 - IMAGE_OVERLAP_EPSILON
        and tx1 <= ix1 + IMAGE_OVERLAP_EPSILON
        and ty1 <= iy1 + IMAGE_OVERLAP_EPSILON
    )
    return not contained


# Gutter kept between a clipped text box and the picture edge (design-px).
_CLIP_GUTTER = 16.0
# Minimum useful width / height after a clip; below this the clip is skipped
# (TEXT_OVER_IMAGE warning in the profile covers the warn-only case).
_CLIP_MIN_W = 200.0   # narrower than this is not a usable text column
_CLIP_MIN_H = 60.0    # shorter than this is not a usable text box


def _parse_pictures_for_clip(dsl_text: str) -> list[dict]:
    """Parse `picture` lines that carry an image slot into geometry dicts."""
    pics: list[dict] = []
    for line in dsl_text.splitlines():
        if not line.startswith("picture "):
            continue
        if not _GEO_IMAGE_SLOT_RE.search(line):
            continue
        xy = _GEO_XY_RE.match(line)
        # geometry precedes the path: keyword — chop it off to avoid matching
        # e.g. "1920x1080" in the path string.
        prefix = line.split("path:", 1)[0]
        wh = _GEO_WH_RE.search(prefix)
        if xy is None or wh is None:
            continue
        m_name = re.search(r"\{\{\s*(\w+)\s*\|", line)
        pics.append({
            "name": m_name.group(1) if m_name else "?",
            "x": float(xy.group(1)), "y": float(xy.group(2)),
            "w": float(wh.group(1)), "h": float(wh.group(2)),
            "_line": line,
        })
    return pics


def _parse_slot_texts_for_clip(dsl_text: str) -> list[dict]:
    """Parse slot-bearing `text` lines into geometry + name dicts."""
    texts: list[dict] = []
    for line in dsl_text.splitlines():
        if not line.startswith("text "):
            continue
        m = _GEO_TEXT_SLOT_RE.search(line)
        if m is None:
            continue
        xy = _GEO_XY_RE.match(line)
        mw = _GEO_MAXW_RE.search(line)
        mh = _GEO_MAXH_RE.search(line)
        if xy is None or mw is None or mh is None:
            continue
        texts.append({
            "name": m.group(1),
            "x": float(xy.group(1)), "y": float(xy.group(2)),
            "maxw": float(mw.group(1)), "maxh": float(mh.group(1)),
            "_line": line,
        })
    return texts


def _fmt_num(v: float) -> str:
    """Format a geometry number: integral when whole, :g otherwise."""
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def clip_text_to_images(dsl_text: str,
                        extra_images: list[dict] | None = None
                        ) -> tuple[str, list[str]]:
    """Shrink slot-bearing text boxes that cross a picture slot's edge so the
    box ends at the image boundary (with a small gutter).

    Never moves the origin; only shrinks ``maxwidth`` (image to the right) or
    ``maxheight`` (image below). When the origin itself sits inside a picture,
    or the remainder would be unusably narrow/short, the box is left alone —
    the TEXT_OVER_IMAGE pack warning in the profile covers it.

    Returns ``(new_dsl, [log lines])``.  Log lines have the form::

        text_3: maxwidth 1835 -> 915 (clipped at picture 'image2')

    Idempotent: a clipped box no longer crosses the edge -> second run is a no-op.
    """
    pics = _parse_pictures_for_clip(dsl_text)
    if extra_images:
        # native content photos (tile thumbnails etc.) clip exactly like
        # picture slots — see cleanup.native_pic_rects
        pics = pics + [dict(r, _line="") for r in extra_images]
    if not pics:
        return dsl_text, []

    texts = _parse_slot_texts_for_clip(dsl_text)
    if not texts:
        return dsl_text, []

    # Build a mapping: original line text -> replacement line text.
    replacements: dict[str, str] = {}  # original line -> rewritten line
    logs: list[str] = []

    for t in texts:
        current = dict(t)  # mutable copy - updated by successive picture clips
        current_line = t["_line"]

        for pic in pics:
            if not crosses_image_edge(current, pic):
                continue

            ix0 = pic["x"]
            iy0 = pic["y"]
            tx0, ty0 = current["x"], current["y"]

            # Only clip when origin is OUTSIDE the picture on the candidate axis.
            can_clip_w = tx0 < ix0 - IMAGE_OVERLAP_EPSILON
            can_clip_h = ty0 < iy0 - IMAGE_OVERLAP_EPSILON

            clip_axis: str | None = None
            new_val: float = 0.0
            old_val: float = 0.0

            if can_clip_w and can_clip_h:
                # Both axes possible — pick the one that preserves more area.
                new_w = ix0 - tx0 - _CLIP_GUTTER
                new_h = iy0 - ty0 - _CLIP_GUTTER
                if new_w * current["maxh"] >= current["maxw"] * new_h:
                    clip_axis, new_val, old_val = "w", new_w, current["maxw"]
                else:
                    clip_axis, new_val, old_val = "h", new_h, current["maxh"]
            elif can_clip_w:
                clip_axis = "w"
                new_val = ix0 - tx0 - _CLIP_GUTTER
                old_val = current["maxw"]
            elif can_clip_h:
                clip_axis = "h"
                new_val = iy0 - ty0 - _CLIP_GUTTER
                old_val = current["maxh"]
            else:
                # Origin inside the picture. Tile layouts (thumbnail left,
                # text spanning the whole tile) are fixable by SHIFTING the
                # box to the photo's right edge when that leaves a usable
                # column; everything else stays warn-only.
                ix1 = pic["x"] + pic["w"]
                tx1 = tx0 + current["maxw"]
                new_x = ix1 + _CLIP_GUTTER
                new_w = tx1 - new_x
                if (ix1 < tx1 and new_w >= max(_CLIP_MIN_W, 0.25 * current["maxw"])):
                    new_line = re.sub(
                        r"^(text\s+)(-?\d+(?:\.\d+)?),",
                        lambda m: f"{m.group(1)}{_fmt_num(new_x)},",
                        current_line, count=1)
                    new_line = _GEO_MAXW_RE.sub(
                        f"maxwidth:{_fmt_num(new_w)}", new_line, count=1)
                    logs.append(
                        f"{current['name']}: x {_fmt_num(tx0)} -> {_fmt_num(new_x)}, "
                        f"maxwidth {_fmt_num(current['maxw'])} -> {_fmt_num(new_w)}"
                        f" (shifted right of picture '{pic['name']}')")
                    current["x"] = new_x
                    current["maxw"] = new_w
                    replacements[t["_line"]] = new_line
                    current_line = new_line
                continue

            # Usability guards.
            if clip_axis == "w":
                if new_val < max(_CLIP_MIN_W, 0.25 * current["maxw"]):
                    continue  # too narrow — skip
            else:
                if new_val < max(_CLIP_MIN_H, 0.25 * current["maxh"]):
                    continue  # too short — skip

            if clip_axis == "w":
                new_line = _GEO_MAXW_RE.sub(
                    f"maxwidth:{_fmt_num(new_val)}", current_line, count=1)
                logs.append(
                    f"{current['name']}: maxwidth {_fmt_num(old_val)} -> {_fmt_num(new_val)}"
                    f" (clipped at picture '{pic['name']}')"
                )
                current["maxw"] = new_val
            else:
                new_line = _GEO_MAXH_RE.sub(
                    f"maxheight:{_fmt_num(new_val)}", current_line, count=1)
                logs.append(
                    f"{current['name']}: maxheight {_fmt_num(old_val)} -> {_fmt_num(new_val)}"
                    f" (clipped at picture '{pic['name']}')"
                )
                current["maxh"] = new_val

            replacements[t["_line"]] = new_line
            current_line = new_line  # for subsequent picture iterations

    if not replacements:
        return dsl_text, []

    # Apply replacements line-by-line (exact string match is safe because
    # every DSL line is unique in practice).
    out_lines: list[str] = []
    for line in dsl_text.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        if stripped in replacements:
            repl = replacements[stripped]
            out_lines.append(repl + ("\n" if line.endswith("\n") else ""))
        else:
            out_lines.append(line)
    return "".join(out_lines), logs


def _curlify(raw: str) -> str:
    r"""Replace escaped ASCII quotes (`\"`) in a raw DSL literal with curly
    quotes so the literal can ride inside the expander's default("…") filter.
    Literal backslashes (`\\`) are protected first, mirroring the parser's
    `_unquote` ordering. Opening/closing forms alternate per run of text."""
    protected = raw.replace("\\\\", "\x00")
    out: list[str] = []
    open_next = True
    for chunk in protected.split('\\"'):
        out.append(chunk)
        out.append("“" if open_next else "”")
        open_next = not open_next
    s = "".join(out[:-1])  # drop the trailing quote added after the last chunk
    return s.replace("\x00", "\\\\")


def slotify_dsl(dsl_text: str) -> tuple[str, list[str]]:
    """Rewrite literal text labels in one layout's DSL into `text_N` slots.

    Returns `(new_dsl_text, slot_names)`. Lines left untouched: non-text
    primitives, empty labels, labels already containing a slot (`{{`), and
    labels with `{`/`}` (cannot ride in the slot grammar).
    """
    out_lines: list[str] = []
    slots: list[str] = []
    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n")
        m = _TEXT_LINE_RE.match(body)
        if m is None:
            out_lines.append(line)
            continue
        prefix, raw = m.group(1), m.group(2)
        if not raw or "{" in raw or "}" in raw:
            out_lines.append(line)
            continue
        name = f"text_{len(slots) + 1}"
        slots.append(name)
        default = _curlify(raw)
        new_body = f'{prefix}"{{{{ {name} | default(\\"{default}\\") }}}}"'
        out_lines.append(new_body + ("\n" if line.endswith("\n") else ""))
    return "".join(out_lines), slots


def slotify_layout_file(path: Path) -> list[str]:
    """Slotify one `.slide.dsl` in place; returns the created slot names."""
    text = path.read_text(encoding="utf-8")
    new_text, slots = slotify_dsl(text)
    if slots:
        path.write_text(new_text, encoding="utf-8")
    return slots


def _text_fit_flag(brand_pack: Path, key: str, *, default: bool = True) -> bool:
    """Read a boolean flag from ``tokens.json`` ``"text-fit"`` block.

    Supports plain bool and ``{"$value": bool}`` wrapped form.  Any parse
    error or missing file returns ``default`` (the safe non-breaking choice
    for both autoshrink and clip-to-images).
    """
    try:
        raw = json.loads((brand_pack / "tokens.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    val = (raw.get("text-fit") or {}).get(key, default)
    if isinstance(val, dict):
        val = val.get("$value", default)
    return val if isinstance(val, bool) else str(val).lower() != "false"


def autoshrink_enabled(brand_pack: Path) -> bool:
    """Return True when the brand pack opts into autoshrink (the default).

    Pack-level opt-out: ``tokens.json`` ``"text-fit": {"autoshrink": false}``
    (or ``{"autoshrink": {"$value": false}}``).  Any parse error or missing
    file -> True (safe default).
    """
    return _text_fit_flag(brand_pack, "autoshrink", default=True)


def clip_to_images_enabled(brand_pack: Path) -> bool:
    """Return True when the brand pack opts into clip-to-images (the default).

    Pack-level opt-out: ``tokens.json`` ``"text-fit": {"clip-to-images": false}``
    (or ``{"clip-to-images": {"$value": false}}``).  Any parse error or
    missing file -> True (safe default).
    """
    return _text_fit_flag(brand_pack, "clip-to-images", default=True)


_SLOT_NAME_RE = re.compile(r"\{\{\s*(text_\d+)\b")
_TEXT_PREFIX_RE = re.compile(r'^(text\s+[^"]*?)\s*("(?:\{\{.*)$)')

# Roles whose boxes were sized for showcase copy but receive arbitrary real
# content — graceful shrink to the 10pt emit floor beats silent overflow.
_AUTOSHRINK_ROLES = frozenset({"title", "body"})


def add_autoshrink(dsl_text: str, slot_roles: dict[str, str]) -> str:
    """Add `autoshrink:true` to slot-bearing text lines whose slot role is
    title/body. Idempotent; never touches the quoted label."""
    out_lines: list[str] = []
    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n")
        slot = _SLOT_NAME_RE.search(body)
        if (not body.startswith("text ") or slot is None
                or "autoshrink:" in body
                or slot_roles.get(slot.group(1)) not in _AUTOSHRINK_ROLES):
            out_lines.append(line)
            continue
        m = _TEXT_PREFIX_RE.match(body)
        if m is None:
            out_lines.append(line)
            continue
        new_body = f"{m.group(1)} autoshrink:true {m.group(2)}"
        out_lines.append(new_body + ("\n" if line.endswith("\n") else ""))
    return "".join(out_lines)


# ---------------------------------------------------------------------------
# Native-payload text slotification
# ---------------------------------------------------------------------------

# A `native` line and its kwargs. Payload may be inline (`b64:"…"`) or a
# sidecar reference (`xml_file:"…"` under the brand pack's assets dir).
_NATIVE_LINE_RE = re.compile(r"^native\s+(\w+)\s+(.*)$")
_NATIVE_KW_RE = re.compile(r'(\w+):"([^"]*)"')
_NATIVE_T_RE = re.compile(r"(<a:t>)([^<]+)(</a:t>)")

# Chart / SmartArt payloads keep their text native for now: their labels live
# in external parts (`parts:`/`parts_file:`), not in the frame XML — a future
# pass can extend slotification into the part graph.
_NATIVE_SKIP_MARKERS = ("<c:chart", "<dgm:", "relIds")


_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _coalesce_runs(xml: str) -> str:
    """Merge ADJACENT runs with identical run properties inside each
    paragraph. Source decks split sentences into per-word runs (spellcheck /
    incremental-edit artifacts); slotifying those yields one useless slot
    per word with a chars budget of that word's length. Identical-rPr
    neighbours are visually one run — merge before slotification."""
    from lxml import etree
    try:
        root = etree.fromstring(xml.encode("utf-8"))
    except Exception:
        return xml
    changed = False
    for para in root.iter(f"{{{_A_NS}}}p"):
        prev = None       # (run element, rPr signature)
        for run in list(para):
            if run.tag != f"{{{_A_NS}}}r":
                prev = None
                continue
            t = run.find(f"{{{_A_NS}}}t")
            if t is None:
                prev = None
                continue
            rpr = run.find(f"{{{_A_NS}}}rPr")
            if rpr is not None:
                # proofing/edit artifacts (spellcheck err, dirty, smtClean,
                # noProof) split visually identical runs — ignore them
                _clean = etree.fromstring(etree.tostring(rpr))
                for _attr in ("err", "dirty", "smtClean", "noProof"):
                    _clean.attrib.pop(_attr, None)
                sig = etree.tostring(_clean)
            else:
                sig = b""
            if prev is not None and prev[1] == sig:
                pt = prev[0].find(f"{{{_A_NS}}}t")
                pt.text = (pt.text or "") + (t.text or "")
                para.remove(run)
                changed = True
            else:
                prev = (run, sig)
    return etree.tostring(root, encoding="unicode") if changed else xml


def _slotify_native_xml(
    xml: str, next_idx: int
) -> tuple[str, list[dict]]:
    """Replace literal `<a:t>` runs with `{{ text_N | default("…") }}`.

    Returns ``(new_xml, slot_dicts)``; each slot dict is
    ``{"name", "default"}`` with the default already XML-unescaped (the DSL
    frontmatter wants the human literal, the XML keeps the escaped form).
    Runs that are whitespace-only, already slotified, or contain braces /
    ASCII quotes that cannot ride the slot grammar stay literal.
    """
    from xml.sax.saxutils import escape as _xml_escape
    from xml.sax.saxutils import unescape as _xml_unescape

    xml = _coalesce_runs(xml)
    slots: list[dict] = []

    def repl(m: re.Match) -> str:
        literal = _xml_unescape(m.group(2))
        if not literal.strip() or "{" in literal or "}" in literal:
            return m.group(0)
        if '"' in literal:
            literal = _curlify(literal.replace('"', '\\"'))
        name = f"text_{next_idx + len(slots)}"
        slots.append({"name": name, "default": literal})
        template = f'{{{{ {name} | default("{literal}") }}}}'
        return m.group(1) + _xml_escape(template) + m.group(3)

    return _NATIVE_T_RE.sub(repl, xml), slots


_PIC_XFRM_OFF_RE = re.compile(r'<a:off\s+x="(-?\d+)"\s+y="(-?\d+)"\s*/>')
_PIC_XFRM_EXT_RE = re.compile(r'<a:ext\s+cx="(\d+)"\s+cy="(\d+)"\s*/>')
_PIC_NAME_RE = re.compile(r'<p:cNvPr\s[^>]*\bname="([^"]*)"')
_PIC_BLIP_RE = re.compile(r'<a:blip\s[^>]*\br:embed="([^"]*)"')
_PIC_DECORATIVE_RE = re.compile(r'<adec:decorative\s+val="1"')
_PIC_LOGO_NAME_RE = re.compile(r"logo|mark|icon|signet", re.IGNORECASE)
# Split a native payload XML into individual <p:pic>…</p:pic> blocks.
_PIC_ELEMENT_RE = re.compile(r"<p:pic\b.*?</p:pic>", re.DOTALL)
# Detect presence of <p:grpSp> to trigger ElementTree descent.
_GRPSP_RE = re.compile(r"<p:grpSp\b")
# Relationship block: maps rId -> target filename + ext
_REL_BLOCK_RE = re.compile(r'<Relationship\s[^>]*\bId="([^"]*)"[^>]*\bTarget="([^"]*)"')

_EMU_PER_PX = 9525  # PowerPoint standard: 1 design-px = 9525 EMU

# XML namespace map used for ElementTree queries in the group-descent pass.
_ET_NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "adec": "http://schemas.microsoft.com/office/drawing/2017/decorative",
}

# Clark-notation tag constants for ElementTree (avoids repeated f-string noise).
_TAG_PIC = "{http://schemas.openxmlformats.org/presentationml/2006/main}pic"
_TAG_GRPSP = "{http://schemas.openxmlformats.org/presentationml/2006/main}grpSp"
_TAG_GRPSPPR = "{http://schemas.openxmlformats.org/presentationml/2006/main}grpSpPr"
_TAG_SPPR = "{http://schemas.openxmlformats.org/presentationml/2006/main}spPr"
_TAG_XFRM = "{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm"
_TAG_OFF = "{http://schemas.openxmlformats.org/drawingml/2006/main}off"
_TAG_EXT = "{http://schemas.openxmlformats.org/drawingml/2006/main}ext"
_TAG_CHOFF = "{http://schemas.openxmlformats.org/drawingml/2006/main}chOff"
_TAG_CHEXT = "{http://schemas.openxmlformats.org/drawingml/2006/main}chExt"
_TAG_BLIP = "{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
_TAG_CNVPR = "{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr"
_TAG_NVPICPR = "{http://schemas.openxmlformats.org/presentationml/2006/main}nvPicPr"
_TAG_NVPR = "{http://schemas.openxmlformats.org/presentationml/2006/main}nvPr"
_TAG_BFILL = "{http://schemas.openxmlformats.org/presentationml/2006/main}blipFill"
_ATTR_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
_ATTR_DECORATIVE = "{http://schemas.microsoft.com/office/drawing/2017/decorative}decorative"


def _et_collect_grouped_pics(root_el, parent_map):
    """Walk all ``<p:grpSp>`` elements in *root_el*, yielding
    ``(pic_el, offset_x_emu, offset_y_emu)`` for each ``<p:pic>`` found
    inside a group.  Top-level ``<p:pic>`` children are NOT yielded here
    (they are handled by the existing regex pass).

    Nested groups are descended recursively; offsets accumulate following
    the same pure-translation formula used in
    ``pptx_svg_decompile._walk``:

        child_off = parent_off + group.<a:off> − group.<a:chOff>

    Scaled groups (ext ≠ chExt) are skipped (offset-only carry, consistent
    with the decompiler's own skip logic).
    """
    import xml.etree.ElementTree as ET

    def _walk_group(grp_el, ox_emu: int, oy_emu: int):
        """Yield (pic_el, canvas_x_emu, canvas_y_emu) for pics inside grp_el."""
        # Compute this group's translation offset.
        grp_xfrm = grp_el.find(f"{_TAG_GRPSPPR}/{_TAG_XFRM}")
        child_ox, child_oy = ox_emu, oy_emu
        if grp_xfrm is not None:
            off_el = grp_xfrm.find(_TAG_OFF)
            ext_el = grp_xfrm.find(_TAG_EXT)
            choff_el = grp_xfrm.find(_TAG_CHOFF)
            chext_el = grp_xfrm.find(_TAG_CHEXT)
            if off_el is not None and choff_el is not None:
                try:
                    gox = int(off_el.get("x", "0"))
                    goy = int(off_el.get("y", "0"))
                    chox = int(choff_el.get("x", "0"))
                    choy = int(choff_el.get("y", "0"))
                    if ext_el is not None and chext_el is not None:
                        # Check for scaling — skip scaled groups (same as decompiler).
                        cx = int(ext_el.get("cx", "0"))
                        cy = int(ext_el.get("cy", "0"))
                        chcx = int(chext_el.get("cx", "0"))
                        chcy = int(chext_el.get("cy", "0"))
                        if chcx > 0 and chcy > 0:
                            sx = cx / chcx
                            sy = cy / chcy
                            if abs(sx - 1.0) > 0.001 or abs(sy - 1.0) > 0.001:
                                # Scaled group: skip (can't apply pure translation).
                                return
                    # Pure translation: formula from pptx_svg_decompile._walk
                    child_ox = ox_emu + gox - chox
                    child_oy = oy_emu + goy - choy
                except (ValueError, TypeError):
                    pass

        for child in grp_el:
            if child.tag == _TAG_PIC:
                yield (child, child_ox, child_oy)
            elif child.tag == _TAG_GRPSP:
                yield from _walk_group(child, child_ox, child_oy)

    # Walk only DIRECT children of root_el that are grpSp (top-level groups).
    # Nested groups are handled recursively inside _walk_group — calling
    # _walk_group on every grpSp via iter() would double-yield nested pics.
    for child in root_el:
        if child.tag == _TAG_GRPSP:
            yield from _walk_group(child, 0, 0)


def slotify_native_pictures(
    dsl_text: str,
    asset_root: Path | None,
    canvas_w_px: int = 1920,
    canvas_h_px: int = 1080,
    area_threshold: float = 0.015,
    next_idx: int = 1,
) -> tuple[str, list[dict], list[str]]:
    """Promote qualifying content ``<p:pic>`` elements inside native payloads
    to top-level ``image`` DSL slots.

    For each ``native <id>`` line whose payload XML contains ``<p:pic>``
    elements, this function:

    1. Decodes the XML (b64 inline or xml_file sidecar).
    2. Inspects each ``<p:pic>`` for geometry and skip conditions.
    3. For qualifying pics, emits a ``picture x,y wxh path:"{{ image_<N>
       | default(\"…\") }}" cover:true`` DSL line, saves extracted image
       bytes when resolvable, and removes the ``<p:pic>`` from the payload.
    4. Re-encodes the modified XML and updates the native line.

    ``picture`` is the engine's only image-rendering primitive (see
    ``feinschliff/dsl/parser.py``); an earlier version emitted a non-existent
    ``image image_N class=replace …`` line that crashed the build with
    ``unknown-compound`` errors. The slot itself is still ``image_<N>``,
    consistent with hand-authored layouts that declare image-bearing slots
    in their ``slots:`` block.

    Skip conditions (any one causes the pic to stay in the native payload):
    - Area ratio below ``area_threshold`` (default 1.5%; small chrome /
      decorative). Tiled content grids — 4-card product rows, 5-tile
      feature strips, n×m photo galleries — typically sit at 2-4% per
      tile, well above the 1.5% floor. Logos (~0.1%) and supergraphic
      strips (~0.4%) stay below it.
    - Name matches ``logo|mark|icon|signet`` (case-insensitive).
    - Carries ``<adec:decorative val="1">``.
    - Has no ``<a:blip r:embed="…">`` (no actual image data).

    Image DSL lines are inserted right before the ``native`` block they came
    from, or after the last existing ``image``/``picture`` line if one exists
    earlier in the file — whichever avoids splitting the native block.

    Returns ``(new_dsl, image_slot_dicts, log_lines)`` where each slot dict is
    ``{"name", "native_id", "x", "y", "w", "h", "asset_path"}``.
    """
    import base64
    import hashlib

    canvas_area = canvas_w_px * canvas_h_px

    out_lines: list[str] = []
    all_slots: list[dict] = []
    logs: list[str] = []
    current_idx = next_idx

    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n")
        m = _NATIVE_LINE_RE.match(body)
        if m is None:
            out_lines.append(line)
            continue

        native_id, rest = m.group(1), m.group(2)
        kwargs = dict(_NATIVE_KW_RE.findall(rest))
        xml: str | None = None
        sidecar: Path | None = None

        if kwargs.get("b64"):
            try:
                xml = base64.b64decode(kwargs["b64"]).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                xml = None
        elif kwargs.get("xml_file") and asset_root is not None:
            sidecar = asset_root / kwargs["xml_file"]
            if sidecar.is_file():
                xml = sidecar.read_text(encoding="utf-8")

        if xml is None or "<p:pic" not in xml:
            out_lines.append(line)
            continue

        # Parse relationship block for RID → filename/ext mapping
        rid_map: dict[str, tuple[str, str]] = {}
        for rm in _REL_BLOCK_RE.finditer(xml):
            rid, target = rm.group(1), rm.group(2)
            import posixpath
            ext = posixpath.splitext(target)[1].lstrip(".")
            rid_map[rid] = (target, ext or "bin")

        # Check whether the payload has any <p:grpSp> containers.  When it
        # does, we use an ElementTree-based walk so we can (a) apply the
        # group-to-canvas offset translation and (b) surgically remove just
        # the promoted <p:pic> from its parent group rather than from the
        # whole XML string.  When there are no groups the fast regex path is
        # kept unchanged for backward compatibility.
        has_groups = bool(_GRPSP_RE.search(xml))

        if has_groups:
            import xml.etree.ElementTree as ET

            # Register all namespaces so ET round-trips them cleanly.
            for _pfx, _uri in _ET_NS.items():
                ET.register_namespace(_pfx, _uri)
            # Also pre-register the decorative namespace if present.
            ET.register_namespace(
                "adec",
                "http://schemas.microsoft.com/office/drawing/2017/decorative",
            )

            try:
                root_el = ET.fromstring(xml)
            except ET.ParseError:
                # Malformed XML — fall back to skipping this native block.
                out_lines.append(line)
                continue

            # Build a parent-map so we can remove children by reference.
            parent_map = {c: p for p in root_el.iter() for c in p}

            # Collect (pic_el, offset_x_emu, offset_y_emu) for ALL pics:
            #   • Direct children: offset = (0, 0).
            #   • Pics inside <p:grpSp>: offset from _et_collect_grouped_pics.
            all_pic_entries: list[tuple] = []  # (pic_el, ox_emu, oy_emu)
            for direct_pic in root_el:
                if direct_pic.tag == _TAG_PIC:
                    all_pic_entries.append((direct_pic, 0, 0))
            for grouped_entry in _et_collect_grouped_pics(root_el, parent_map):
                all_pic_entries.append(grouped_entry)

            if not all_pic_entries:
                out_lines.append(line)
                continue

            image_lines: list[str] = []
            slot_dicts: list[dict] = []
            pics_to_remove: list = []  # pic_el references for ET removal

            for pic_el, grp_ox_emu, grp_oy_emu in all_pic_entries:
                # --- Skip: decorative ---
                nvpr = pic_el.find(f"{_TAG_NVPICPR}/{_TAG_NVPR}")
                if nvpr is not None:
                    dec = nvpr.find(
                        "{http://schemas.microsoft.com/office/drawing/2017/decorative}decorative"
                    )
                    if dec is not None and dec.get("val") == "1":
                        continue

                # --- Skip: no blip ---
                bfill = pic_el.find(_TAG_BFILL)
                blip_el = bfill.find(_TAG_BLIP) if bfill is not None else None
                r_id = blip_el.get(_ATTR_EMBED) if blip_el is not None else None
                if r_id is None:
                    continue

                # --- Skip: logo/mark name ---
                cnvpr = pic_el.find(f"{_TAG_NVPICPR}/{_TAG_CNVPR}")
                if cnvpr is not None:
                    pic_name = cnvpr.get("name", "")
                    if _PIC_LOGO_NAME_RE.search(pic_name):
                        continue

                # --- Geometry: pic-local coords + group translation ---
                sppr = pic_el.find(_TAG_SPPR)
                xfrm = sppr.find(_TAG_XFRM) if sppr is not None else None
                if xfrm is None:
                    continue
                off_el = xfrm.find(_TAG_OFF)
                ext_el = xfrm.find(_TAG_EXT)
                if off_el is None or ext_el is None:
                    continue
                try:
                    pic_x_emu = int(off_el.get("x", "0"))
                    pic_y_emu = int(off_el.get("y", "0"))
                    cx_emu = int(ext_el.get("cx", "0"))
                    cy_emu = int(ext_el.get("cy", "0"))
                except (ValueError, TypeError):
                    continue

                # Canvas coords: apply group translation offset.
                canvas_x_emu = pic_x_emu + grp_ox_emu
                canvas_y_emu = pic_y_emu + grp_oy_emu

                x_px = canvas_x_emu // _EMU_PER_PX
                y_px = canvas_y_emu // _EMU_PER_PX
                w_px = cx_emu // _EMU_PER_PX
                h_px = cy_emu // _EMU_PER_PX

                if w_px <= 0 or h_px <= 0:
                    continue
                area_ratio = (w_px * h_px) / canvas_area
                if area_ratio < area_threshold:
                    continue

                # --- Image bytes extraction (best-effort) ---
                asset_path: str | None = None
                if asset_root is not None and r_id in rid_map:
                    _target, _ext = rid_map[r_id]
                    candidate = asset_root / _target.lstrip("/")
                    if candidate.is_file():
                        img_bytes = candidate.read_bytes()
                        sha8 = hashlib.sha1(img_bytes).hexdigest()[:8]
                        dest = asset_root / f"native_pic_{sha8}.{_ext}"
                        if not dest.exists():
                            dest.write_bytes(img_bytes)
                        asset_path = str(dest)

                # --- Slot allocation ---
                slot_name = f"image_{current_idx}"
                current_idx += 1
                default_path = asset_path or ""
                image_lines.append(
                    f'picture {x_px},{y_px} {w_px}x{h_px} '
                    f'path:"{{{{ {slot_name} | default(\\"{default_path}\\") }}}}" '
                    f'cover:true'
                )
                slot_dicts.append({
                    "name": slot_name,
                    "native_id": native_id,
                    "x": x_px, "y": y_px,
                    "w": w_px, "h": h_px,
                    "asset_path": asset_path,
                })
                pics_to_remove.append(pic_el)

            if not slot_dicts:
                out_lines.append(line)
                continue

            # Remove promoted <p:pic> elements via ElementTree (surgical:
            # removes just the pic from its parent, leaving sibling shapes
            # inside groups intact).
            for pic_el in pics_to_remove:
                parent_el = parent_map.get(pic_el)
                if parent_el is not None:
                    try:
                        parent_el.remove(pic_el)
                    except ValueError:
                        pass  # already removed (shouldn't happen)

            new_xml = ET.tostring(root_el, encoding="unicode")

        else:
            # --- Fast regex path (no groups present) ---
            pics = _PIC_ELEMENT_RE.findall(xml)
            if not pics:
                out_lines.append(line)
                continue

            image_lines = []
            slot_dicts = []

            for pic_xml in pics:
                # --- Skip conditions ---
                if _PIC_DECORATIVE_RE.search(pic_xml):
                    continue
                blip_m = _PIC_BLIP_RE.search(pic_xml)
                if blip_m is None:
                    continue
                name_m = _PIC_NAME_RE.search(pic_xml)
                if name_m and _PIC_LOGO_NAME_RE.search(name_m.group(1)):
                    continue

                # --- Geometry ---
                off_m = _PIC_XFRM_OFF_RE.search(pic_xml)
                ext_m = _PIC_XFRM_EXT_RE.search(pic_xml)
                if not (off_m and ext_m):
                    continue
                x_px = int(off_m.group(1)) // _EMU_PER_PX
                y_px = int(off_m.group(2)) // _EMU_PER_PX
                w_px = int(ext_m.group(1)) // _EMU_PER_PX
                h_px = int(ext_m.group(2)) // _EMU_PER_PX

                if w_px <= 0 or h_px <= 0:
                    continue
                area_ratio = (w_px * h_px) / canvas_area
                if area_ratio < area_threshold:
                    continue

                # --- Image bytes extraction (best-effort) ---
                asset_path: str | None = None
                r_id = blip_m.group(1)
                if asset_root is not None and r_id in rid_map:
                    _target, ext = rid_map[r_id]
                    # For sidecar payloads the image file lives under asset_root.
                    # Try to locate it relative to the sidecar directory.
                    candidate = asset_root / _target.lstrip("/")
                    if candidate.is_file():
                        img_bytes = candidate.read_bytes()
                        sha8 = hashlib.sha1(img_bytes).hexdigest()[:8]
                        dest = asset_root / f"native_pic_{sha8}.{ext}"
                        if not dest.exists():
                            dest.write_bytes(img_bytes)
                        asset_path = str(dest)

                # --- Slot allocation ---
                slot_name = f"image_{current_idx}"
                current_idx += 1
                # Emit as a `picture` primitive (the engine's only image-rendering
                # primitive — see feinschliff/dsl/parser.py and the existing
                # decompiler emission for slot-typed pictures). `path:` carries
                # the Jinja-bound slot with a default that points at the
                # extracted asset when one was found; otherwise the slot's
                # default empty string lets a bare build leave the slot blank.
                default_path = asset_path or ""
                # The path expression is `path:"{{ slot | default(\"…\") }}"`
                # mirroring the convention used by hand-authored layouts (e.g.
                # bsh `text-picture.slide.dsl`). `cover:true` matches the
                # `class=replace` semantic (fill, do not crop).
                image_lines.append(
                    f'picture {x_px},{y_px} {w_px}x{h_px} '
                    f'path:"{{{{ {slot_name} | default(\\"{default_path}\\") }}}}" '
                    f'cover:true'
                )
                slot_dicts.append({
                    "name": slot_name,
                    "native_id": native_id,
                    "x": x_px, "y": y_px,
                    "w": w_px, "h": h_px,
                    "asset_path": asset_path,
                })

            if not slot_dicts:
                # No pics qualified — leave the line unchanged.
                out_lines.append(line)
                continue

            # Remove promoted <p:pic> elements from the XML.
            # Cross-check by geometry to identify which pic_xml strings to drop.
            promoted_set: set[str] = set()
            for pic_xml in pics:
                off_m = _PIC_XFRM_OFF_RE.search(pic_xml)
                ext_m = _PIC_XFRM_EXT_RE.search(pic_xml)
                if not (off_m and ext_m):
                    continue
                x_px = int(off_m.group(1)) // _EMU_PER_PX
                y_px = int(off_m.group(2)) // _EMU_PER_PX
                w_px = int(ext_m.group(1)) // _EMU_PER_PX
                h_px = int(ext_m.group(2)) // _EMU_PER_PX
                for d in slot_dicts:
                    if d["x"] == x_px and d["y"] == y_px and d["w"] == w_px and d["h"] == h_px:
                        promoted_set.add(pic_xml)
                        break

            new_xml = xml
            for pic_xml in promoted_set:
                new_xml = new_xml.replace(pic_xml, "", 1)

        # Re-encode the modified native payload.
        new_native_line: str
        if sidecar is not None:
            sidecar.write_text(new_xml, encoding="utf-8")
            new_native_line = line
        else:
            new_b64 = base64.b64encode(new_xml.encode("utf-8")).decode("ascii")
            new_body = body.replace(kwargs["b64"], new_b64, 1)
            new_native_line = new_body + ("\n" if line.endswith("\n") else "")

        # Emit image DSL lines immediately before this native line.
        for img_line in image_lines:
            out_lines.append(img_line + ("\n" if line.endswith("\n") else ""))
        out_lines.append(new_native_line)
        all_slots.extend(slot_dicts)
        logs.append(
            f"{native_id}: {len(slot_dicts)} pic(s) promoted "
            f"({', '.join(d['name'] for d in slot_dicts)})"
        )

    return "".join(out_lines), all_slots, logs


def slotify_native_text(
    dsl_text: str, asset_root: Path | None
) -> tuple[str, list[dict], list[str]]:
    """Slotify the text runs of every `native` payload in one layout's DSL.

    Inline payloads are rewritten in place (re-encoded `b64:`); sidecar
    payloads (`xml_file:`) are rewritten on disk under ``asset_root``. Slot
    numbering continues after the highest existing ``text_N`` in the DSL.
    Charts and SmartArt are skipped (labels live in external parts).

    Returns ``(new_dsl, slot_dicts, log_lines)`` where slot dicts carry
    ``{"name", "default", "native_id"}``.
    """
    import base64

    existing = [int(m.group(1)) for m in re.finditer(r"\btext_(\d+)\b", dsl_text)]
    next_idx = max(existing, default=0) + 1

    out_lines: list[str] = []
    all_slots: list[dict] = []
    logs: list[str] = []
    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n")
        m = _NATIVE_LINE_RE.match(body)
        if m is None:
            out_lines.append(line)
            continue
        native_id, rest = m.group(1), m.group(2)
        kwargs = dict(_NATIVE_KW_RE.findall(rest))
        xml: str | None = None
        sidecar: Path | None = None
        if kwargs.get("b64"):
            try:
                xml = base64.b64decode(kwargs["b64"]).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                xml = None
        elif kwargs.get("xml_file") and asset_root is not None:
            sidecar = asset_root / kwargs["xml_file"]
            if sidecar.is_file():
                xml = sidecar.read_text(encoding="utf-8")
        if xml is None or any(s in xml for s in _NATIVE_SKIP_MARKERS):
            out_lines.append(line)
            continue
        new_xml, slots = _slotify_native_xml(xml, next_idx)
        if not slots:
            out_lines.append(line)
            continue
        next_idx += len(slots)
        for s in slots:
            s["native_id"] = native_id
        all_slots.extend(slots)
        logs.append(f"{native_id}: {len(slots)} text run(s) slotified "
                    f"({', '.join(s['name'] for s in slots)})")
        if sidecar is not None:
            sidecar.write_text(new_xml, encoding="utf-8")
            out_lines.append(line)
        else:
            new_b64 = base64.b64encode(new_xml.encode("utf-8")).decode("ascii")
            new_body = body.replace(kwargs["b64"], new_b64, 1)
            out_lines.append(new_body + ("\n" if line.endswith("\n") else ""))
    return "".join(out_lines), all_slots, logs

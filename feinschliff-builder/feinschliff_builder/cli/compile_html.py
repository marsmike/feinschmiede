"""`feinschliff compile-html …` — parse a brand's claude-design HTML and
emit `.slide.dsl` skeletons for each `<section data-slots="…">`.

Each output file carries the slot schema as a header docstring + a
`canvas` + `theme` line. The body is intentionally minimal — the author
fills in primitives. This is the "scaffold a new brand's layouts" step.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path


_SECTION_RE = re.compile(
    r'<section\s+([^>]*?)>',
    re.IGNORECASE | re.DOTALL,
)
_ATTR_RE = re.compile(r'data-([a-z-]+)\s*=\s*"([^"]*)"')
_COMMENT_RE = re.compile(r'<!--\s*=+\s*(\d+)\s*·\s*([^=]+?)\s*=+\s*-->')


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("html_path", help="Path to claude-design HTML")
    parser.add_argument("-o", "--out-dir", required=True,
                        help="Directory to write .slide.dsl skeletons into")
    parser.add_argument("--theme", required=True,
                        help="Theme name to write into each layout (e.g. 'feinschliff', 'catppuccin-macchiato'). Required so authoring a new brand fails loudly rather than silently mis-themed.")
    parser.add_argument("--prefix", default="",
                        help="Optional filename prefix (e.g. '03-')")
    parser.set_defaults(func=cmd_compile_html)


def cmd_compile_html(args) -> int:
    src = Path(args.html_path).resolve()
    if not src.is_file():
        print(f"compile-html: source not found: {src}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    text = src.read_text()
    sections = list(_iter_sections(text))
    if not sections:
        print(f"compile-html: no <section data-slots=…> found in {src}", file=sys.stderr)
        return 1

    written: list[Path] = []
    for idx, (number, label, attrs) in enumerate(sections, 1):
        slug = _slugify(label or attrs.get("label", f"slide-{number or idx}"))
        out_path = out_dir / f"{args.prefix}{slug}.slide.dsl"
        out_path.write_text(_render_skeleton(
            slug=slug, number=number or idx,
            label=label or attrs.get("label", slug),
            attrs=attrs,
            theme=args.theme,
        ))
        written.append(out_path)

    print(f"compile-html: wrote {len(written)} skeletons to {out_dir}")
    for p in written:
        print(f"  · {p.name}")
    return 0


def _iter_sections(text: str):
    """Yield (slide_number, label, attrs_dict) per `<section data-slots=…>`.

    `attrs_dict` includes every `data-*` attribute and the parsed JSON of
    `data-slots` under the key `_slots`. Slide number + label are taken
    from the nearest preceding `<!-- = N · Label = -->` comment in the
    source HTML, falling back to the section's sequence number.
    """
    seq = 0
    for m in _SECTION_RE.finditer(text):
        attrs_blob = m.group(1)
        attrs: dict[str, str] = {}
        for am in _ATTR_RE.finditer(attrs_blob):
            attrs[am.group(1)] = html.unescape(am.group(2))
        if "slots" not in attrs:
            continue

        seq += 1
        # Scan all comment matches and find the closest preceding `<!-- = N · Label = -->`.
        nearest_n, nearest_lbl, nearest_pos = None, None, -1
        for cm in _COMMENT_RE.finditer(text):
            if cm.start() < m.start() and cm.start() > nearest_pos:
                nearest_pos = cm.start()
                try:
                    nearest_n = int(cm.group(1))
                except ValueError:
                    nearest_n = seq
                nearest_lbl = cm.group(2).strip()
        slide_number = nearest_n or seq
        slide_label = nearest_lbl
        try:
            attrs["_slots"] = json.loads(attrs["slots"])
        except json.JSONDecodeError:
            attrs["_slots"] = {}
        yield slide_number, slide_label, attrs


def _slugify(label: str) -> str:
    s = label.lower().strip()
    s = re.sub(r"[\s·•]+", "-", s)
    s = re.sub(r"[^a-z0-9\-]+", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "slide"


def _render_skeleton(*, slug: str, number: int, label: str,
                     attrs: dict, theme: str) -> str:
    slots = attrs.get("_slots", {})
    role = attrs.get("role", "")
    when_to_use = attrs.get("when-to-use", "")
    when_not_to_use = attrs.get("when-not-to-use", "")

    slot_lines = []
    for name, spec in slots.items():
        kind = spec.get("type", "string") if isinstance(spec, dict) else "any"
        maxlen = spec.get("maxLength") if isinstance(spec, dict) else None
        opt = "opt" if isinstance(spec, dict) and spec.get("optional") else "req"
        desc = spec.get("description", "") if isinstance(spec, dict) else ""
        bits = [kind, opt]
        if maxlen is not None:
            bits.append(f"≤{maxlen}")
        slot_lines.append(f"#   {name:<16} {', '.join(bits)}  {desc}".rstrip())

    body = [
        f"# {slug} — auto-generated skeleton from claude-design slide {number}.",
        f"# Label:        {label}",
        f"# Role:         {role}",
    ]
    if when_to_use:
        body.append(f"# When to use:  {when_to_use}")
    if when_not_to_use:
        body.append(f"# Avoid when:   {when_not_to_use}")
    body += [
        "#",
        "# Slot schema (from data-slots):",
        *slot_lines,
        "# Deck-level: footer_left, footer_center, footer_right (when applicable).",
        "",
        "canvas 1920x1080",
        f"theme {theme}",
        "",
        "header pgmeta:\"{{ pgmeta }}\"",
        "",
        "# TODO: lay out the slide. Inspect the corresponding canonical .pptx",
        "# baseline + the HTML section for positions and styling cues.",
        "",
        "footer left:\"{{ footer_left }}\" right:\"{{ footer_right }}\"",
        "",
    ]
    return "\n".join(body)

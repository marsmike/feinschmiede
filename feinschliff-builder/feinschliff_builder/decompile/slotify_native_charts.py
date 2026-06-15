"""Slotify pass: promote ``<c:chart>`` native payloads to parameterised
``svg … from:`` diagram DSL lines.

v1 scope: barChart → ``barchart``; pieChart / doughnutChart → ``pie``.
All other chart types are logged and skipped (native stays unchanged).
Series values and dPt colour overrides are baked into the sidecar as
defaults; a bare build renders identically to the source PPTX.

Sidecar written to ``<asset_root>/diagrams/chart_<stem>_N.svg.dsl``;
DSL line: ``svg chart_N x,y WxH from:"../assets/diagrams/..."``.
``<c:chart>`` is removed from the native payload; the surrounding
``<p:graphicFrame>`` shell is preserved.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# OOXML namespace constants
# ---------------------------------------------------------------------------

_NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"

# Namespace map for lxml XPath / findall
_NSMAP: dict[str, str] = {
    "c": _NS_C,
    "a": _NS_A,
    "p": _NS_P,
}

# Chart type tag → DSL primitive name (None = unsupported in v1)
_CHART_TYPE_MAP: dict[str, str | None] = {
    f"{{{_NS_C}}}barChart":      "barchart",
    f"{{{_NS_C}}}pieChart":      "pie",
    f"{{{_NS_C}}}doughnutChart": "pie",
    # v1 defer:
    f"{{{_NS_C}}}lineChart":     None,
    f"{{{_NS_C}}}scatterChart":  None,
    f"{{{_NS_C}}}areaChart":     None,
    f"{{{_NS_C}}}radarChart":    None,
    f"{{{_NS_C}}}bubbleChart":   None,
    f"{{{_NS_C}}}stockChart":    None,
}

_ACCENT_CYCLE = ["accent1", "accent2", "accent3", "accent4", "accent5", "accent6"]
_NATIVE_LINE_RE = re.compile(r"^native\s+(\w+)\s+(.*)$")
_NATIVE_KW_RE = re.compile(r'(\w+):"([^"]*)"')
_XFRM_OFF_RE = re.compile(r'<a:off\s+x="(-?\d+)"\s+y="(-?\d+)"\s*/>')
_XFRM_EXT_RE = re.compile(r'<a:ext\s+cx="(\d+)"\s+cy="(\d+)"\s*/>')
_EMU_PER_PX = 9525


def _try_lxml(xml: str):
    try:
        from lxml import etree  # type: ignore[import]
        return etree.fromstring(xml.encode("utf-8"))
    except Exception:
        return None


def _find_chart_element(root):
    return root.find(f".//{{{_NS_C}}}chart")


def _find_plot_area(chart_el):
    return chart_el.find(f"{{{_NS_C}}}plotArea")


def _detect_chart_type(plot_area) -> tuple[str, str | None]:
    """Return (tag, primitive) for the first chart type in plotArea."""
    for child in plot_area:
        tag = child.tag
        if tag in _CHART_TYPE_MAP:
            return tag, _CHART_TYPE_MAP[tag]
        if tag.startswith(f"{{{_NS_C}}}") and tag.endswith("Chart"):
            return tag, None
    return "", None


def _extract_solid_fill_hex(spPr) -> str | None:
    if spPr is None:
        return None
    clr = spPr.find(f".//{{{_NS_A}}}srgbClr")
    if clr is not None:
        val = clr.get("val")
        if val:
            return val.strip().upper()
    return None


def _parse_num_ref(el) -> list[float]:
    values: list[float] = []
    for v_el in el.iter(f"{{{_NS_C}}}v"):
        try:
            values.append(float(v_el.text or "0"))
        except ValueError:
            values.append(0.0)
    return values


def _parse_str_ref(el) -> list[str]:
    return [v_el.text or "" for v_el in el.iter(f"{{{_NS_C}}}v")]


def _dpt_color_map(ser_el) -> dict[int, str]:
    result: dict[int, str] = {}
    for dpt in ser_el.findall(f"{{{_NS_C}}}dPt"):
        idx_el = dpt.find(f"{{{_NS_C}}}idx")
        if idx_el is None:
            continue
        try:
            idx = int(idx_el.get("val", "-1"))
        except ValueError:
            continue
        hex_color = _extract_solid_fill_hex(dpt.find(f"{{{_NS_C}}}spPr"))
        if hex_color is not None:
            result[idx] = hex_color
    return result


def _series_color(ser_el) -> str | None:
    return _extract_solid_fill_hex(ser_el.find(f"{{{_NS_C}}}spPr"))


def _color_token_or_hex(color: str | None, fallback_idx: int) -> str:
    """Hex colour (#RRGGBB) when available; otherwise cycle through accent tokens."""
    if color:
        return f"#{color}"
    return _ACCENT_CYCLE[fallback_idx % len(_ACCENT_CYCLE)]


def _build_barchart_dsl(
    series_data: list[tuple[list[float], list[str], dict[int, str], str | None]],
    canvas_w: int = 800,
    canvas_h: int = 400,
) -> str:
    """Emit ``barchart`` SVG-DSL body. v1: first series only."""
    if not series_data:
        return f"barchart chart 0,0 {canvas_w}x{canvas_h} bars:1,accent1"
    vals, labels, dpt_colors, ser_color = series_data[0]
    if not vals:
        return f"barchart chart 0,0 {canvas_w}x{canvas_h} bars:1,accent1"
    bar_parts = [
        f"{v},{_color_token_or_hex(dpt_colors.get(i) or ser_color, i)}"
        for i, v in enumerate(vals)
    ]
    lines: list[str] = []
    if labels:
        lines.append(f"# categories: {', '.join(labels)}")
    lines.append(
        f"barchart chart 0,0 {canvas_w}x{canvas_h} bars:{';'.join(bar_parts)} max:{max(vals)}"
    )
    return "\n".join(lines)


def _build_pie_dsl(
    series_data: list[tuple[list[float], list[str], dict[int, str], str | None]],
    canvas_w: int = 400,
    canvas_h: int = 400,
) -> str:
    """Emit ``pie`` SVG-DSL body. v1: first series only."""
    cx, cy = canvas_w // 2, canvas_h // 2
    r = min(canvas_w, canvas_h) // 2 - 10
    fallback = f"pie chart {cx},{cy} r:{r} slices:1,accent1"
    if not series_data:
        return fallback
    vals, labels, dpt_colors, ser_color = series_data[0]
    if not vals:
        return fallback
    slice_parts = [
        f"{v},{_color_token_or_hex(dpt_colors.get(i) or ser_color, i)}"
        for i, v in enumerate(vals)
    ]
    lines: list[str] = []
    if labels:
        lines.append(f"# categories: {', '.join(labels)}")
    lines.append(f"pie chart {cx},{cy} r:{r} slices:{';'.join(slice_parts)}")
    return "\n".join(lines)


def _parse_chart_series(chart_el) -> list[tuple[list[float], list[str], dict[int, str], str | None]]:
    """Extract (values, labels, dpt_colors, series_color) per <c:ser>."""
    plot_area = _find_plot_area(chart_el)
    if plot_area is None:
        return []

    result = []
    for child in plot_area:
        # Each chart type element contains <c:ser> children
        if not child.tag.startswith(f"{{{_NS_C}}}") or not child.tag.endswith("Chart"):
            continue
        for ser_el in child.findall(f"{{{_NS_C}}}ser"):
            # Values from <c:val>
            vals: list[float] = []
            val_el = ser_el.find(f"{{{_NS_C}}}val")
            if val_el is not None:
                for sub in val_el:
                    vals = _parse_num_ref(sub)
                    if vals:
                        break

            # Category labels from <c:cat>
            labels: list[str] = []
            cat_el = ser_el.find(f"{{{_NS_C}}}cat")
            if cat_el is not None:
                for sub in cat_el:
                    labels = _parse_str_ref(sub)
                    if labels:
                        break

            # Per-data-point colour overrides
            dpt_colors = _dpt_color_map(ser_el)

            # Series-level colour
            ser_color = _series_color(ser_el)

            result.append((vals, labels, dpt_colors, ser_color))

    return result


def _process_native_payload(
    xml: str,
    stem: str,
    next_idx: int,
    asset_root: Path,
    canvas_w_px: int = 1920,
    canvas_h_px: int = 1080,
) -> tuple[str | None, str | None, str | None, str]:
    """Try to promote the first <c:chart> in xml.

    Returns (dsl_line, sidecar_rel, chart_tag, modified_xml).
    dsl_line is None when chart is unsupported or parse fails.
    """
    root = _try_lxml(xml)
    if root is None:
        return None, None, None, xml

    chart_el = _find_chart_element(root)
    if chart_el is None:
        return None, None, None, xml

    plot_area = _find_plot_area(chart_el)
    if plot_area is None:
        return None, None, None, xml

    chart_tag, primitive = _detect_chart_type(plot_area)
    if not chart_tag:
        return None, None, None, xml

    if primitive is None:
        # Unsupported type — caller logs the skip
        return None, None, chart_tag, xml

    # Extract geometry from the surrounding <p:graphicFrame> / <p:sp> xfrm
    off_m = _XFRM_OFF_RE.search(xml)
    ext_m = _XFRM_EXT_RE.search(xml)
    if not (off_m and ext_m):
        return None, None, chart_tag, xml

    x_px = int(off_m.group(1)) // _EMU_PER_PX
    y_px = int(off_m.group(2)) // _EMU_PER_PX
    w_px = int(ext_m.group(1)) // _EMU_PER_PX
    h_px = int(ext_m.group(2)) // _EMU_PER_PX

    if w_px <= 0 or h_px <= 0:
        return None, None, chart_tag, xml

    # Parse series data
    series_data = _parse_chart_series(chart_el)

    # Build DSL body for the sidecar
    if primitive == "barchart":
        dsl_body = _build_barchart_dsl(series_data, canvas_w=w_px, canvas_h=h_px)
    else:  # pie
        dsl_body = _build_pie_dsl(series_data, canvas_w=w_px, canvas_h=h_px)

    # Write sidecar file
    diagrams_dir = asset_root / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)
    slot_name = f"chart_{next_idx}"
    sidecar_name = f"chart_{stem}_{next_idx}.svg.dsl"
    sidecar_path = diagrams_dir / sidecar_name
    sidecar_path.write_text(dsl_body + "\n", encoding="utf-8")

    # Path relative to layouts/ dir (one level up from assets/)
    sidecar_rel = f"../assets/diagrams/{sidecar_name}"

    # Emit the DSL line
    dsl_line = f'svg {slot_name} {x_px},{y_px} {w_px}x{h_px} from:"{sidecar_rel}"'

    # Remove <c:chart> from the native XML.
    # The surrounding <p:graphicFrame> shell is preserved.
    try:
        from lxml import etree  # type: ignore[import]
        chart_parent = chart_el.getparent()
        if chart_parent is not None:
            chart_parent.remove(chart_el)
        modified_xml = etree.tostring(root, encoding="unicode")
    except Exception:
        modified_xml = xml  # Fallback: leave xml unchanged

    return dsl_line, sidecar_rel, chart_tag, modified_xml


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def slotify_native_charts(
    dsl_text: str,
    asset_root: Path | None,
    canvas_w_px: int = 1920,
    canvas_h_px: int = 1080,
    next_idx: int = 1,
) -> tuple[str, list[dict], list[str]]:
    """Promote supported <c:chart> elements inside native payloads to
    ``svg chart_N x,y WxH from:"../assets/diagrams/..."`` DSL lines.

    Supported: barChart → barchart; pieChart / doughnutChart → pie.
    Unsupported types are skipped (native unchanged, skip logged).
    Returns (new_dsl, chart_slot_dicts, log_lines).
    Each slot dict: {"name", "native_id", "x", "y", "w", "h", "sidecar"}.
    """
    if asset_root is None:
        # No asset_root = cannot write sidecars → no-op
        return dsl_text, [], []

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
        elif kwargs.get("xml_file"):
            sidecar = asset_root / kwargs["xml_file"]
            if sidecar.is_file():
                xml = sidecar.read_text(encoding="utf-8")

        # Quick pre-filter: skip payloads that contain no chart namespace ref
        if xml is None or f"{{{_NS_C}}}" not in xml and f"c:" not in xml:
            out_lines.append(line)
            continue

        # More specific: must have a <c:chart or the Clark-notation tag
        if "<c:chart" not in xml and f"{{{_NS_C}}}chart" not in xml:
            out_lines.append(line)
            continue

        # Derive a short stem from native_id for sidecar filename
        stem = re.sub(r"[^A-Za-z0-9_-]", "_", native_id)

        dsl_line, sidecar_rel, chart_tag, modified_xml = _process_native_payload(
            xml=xml,
            stem=stem,
            next_idx=current_idx,
            asset_root=asset_root,
            canvas_w_px=canvas_w_px,
            canvas_h_px=canvas_h_px,
        )

        if dsl_line is None:
            # Unsupported or parse failure
            tag_short = chart_tag.split("}")[-1] if chart_tag and "}" in chart_tag else (chart_tag or "unknown")
            if chart_tag:
                logs.append(f"{native_id}: skip {tag_short} (unsupported in v1)")
            out_lines.append(line)
            continue

        # Re-encode the modified native payload (chart element removed)
        new_native_line: str
        if sidecar is not None:
            sidecar.write_text(modified_xml, encoding="utf-8")
            new_native_line = line
        else:
            new_b64 = base64.b64encode(modified_xml.encode("utf-8")).decode("ascii")
            new_body = body.replace(kwargs["b64"], new_b64, 1)
            new_native_line = new_body + ("\n" if line.endswith("\n") else "")

        # Emit SVG DSL line before the native line
        out_lines.append(dsl_line + ("\n" if line.endswith("\n") else ""))
        out_lines.append(new_native_line)

        # Record slot metadata
        # Parse geometry again for the slot dict (already validated in _process)
        off_m = _XFRM_OFF_RE.search(xml)
        ext_m = _XFRM_EXT_RE.search(xml)
        x_px = int(off_m.group(1)) // _EMU_PER_PX if off_m else 0
        y_px = int(off_m.group(2)) // _EMU_PER_PX if off_m else 0
        w_px = int(ext_m.group(1)) // _EMU_PER_PX if ext_m else 0
        h_px = int(ext_m.group(2)) // _EMU_PER_PX if ext_m else 0

        slot_name = f"chart_{current_idx}"
        all_slots.append({
            "name": slot_name,
            "native_id": native_id,
            "x": x_px,
            "y": y_px,
            "w": w_px,
            "h": h_px,
            "sidecar": sidecar_rel,
        })
        logs.append(f"{native_id}: promoted to {slot_name} (svg from:{sidecar_rel!r})")
        current_idx += 1

    return "".join(out_lines), all_slots, logs

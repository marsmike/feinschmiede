"""Slotify pass: expose chart values, category labels, and per-point colours
from native ``<p:graphicFrame>`` chart payloads as bindable DSL slots.

Design principle
----------------
The original ``<c:chart>`` OOXML is left **100 % intact** so PowerPoint renders
it with its native chart engine — full visual fidelity.  Only the *values*,
*category labels*, and *per-point colours* are exposed as Jinja-renderable kw-
args that a deck plan can override at build time.  The chart shell (XML blob,
style/color parts, embedded xlsx) stays byte-for-byte verbatim.

Supported chart types (v1)
--------------------------
``pieChart``, ``doughnutChart``, ``barChart`` — all other types are skipped
silently; the native line is left unchanged and a skip is logged.

Slot encoding
-------------
Each kw-arg value is a **base64-encoded JSON list** to sidestep DSL
quote-escape issues:

    chart_categories:"{{ chart_1_categories | default('<b64>') }}"
    chart_values:"{{ chart_1_values | default('<b64>') }}"
    chart_colors:"{{ chart_1_colors | default('<b64>') }}"

where ``<b64>`` is ``base64(json.dumps(list))``.  A bare build decodes
the default and produces the same output as the original PPTX.

Counter ``N`` (in ``chart_N_*``) is per-layout, monotonic, starting at 1.

Idempotency
-----------
Running this pass twice on a layout that already has ``chart_categories``
kw-args is a no-op: any native line that already carries ``chart_categories``
is skipped.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# OOXML namespace constants
# ---------------------------------------------------------------------------

_NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"

# Supported chart type local names (v1).
_SUPPORTED_CHART_TAGS = {
    f"{{{_NS_C}}}pieChart",
    f"{{{_NS_C}}}doughnutChart",
    f"{{{_NS_C}}}barChart",
}

# Native-line and kw-arg patterns (must match slotify.py's definitions).
_NATIVE_LINE_RE = re.compile(r"^(native\s+\w+\s+)(.*)\s*$")
_NATIVE_KW_RE = re.compile(r'(\w+):"([^"]*)"')


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _b64_json(obj) -> str:
    """Return base64(json.dumps(obj)) as an ASCII string."""
    return base64.b64encode(json.dumps(obj, ensure_ascii=False).encode("utf-8")).decode("ascii")


def _load_sidecar(parts_file_ref: str, asset_root: Path) -> list[dict] | None:
    """Resolve *parts_file* relative to *asset_root* and return the parsed JSON list.
    Returns None on any error."""
    p = Path(parts_file_ref)
    if not p.is_absolute():
        p = asset_root / p
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_bytes())
    except Exception:
        return None


def _find_chart_xml(entries: list[dict]) -> str | None:
    """Return decoded chart XML from the first ``drawingml.chart+xml`` part, or None."""
    for e in entries:
        if "content_type" in e and e["content_type"].endswith("drawingml.chart+xml"):
            try:
                return base64.b64decode(e["blob"]).decode("utf-8")
            except Exception:
                return None
    return None


def _detect_chart_type(root):
    """Return the lxml element of the first supported chart type inside
    ``<c:plotArea>``, or None if the chart type is unsupported / absent."""
    try:
        from lxml import etree  # noqa: F401 — availability probe only
    except ImportError:
        return None
    plot_area = root.find(f".//{{{_NS_C}}}plotArea")
    if plot_area is None:
        return None
    for child in plot_area:
        if child.tag in _SUPPORTED_CHART_TAGS:
            return child
    return None


def _extract_series_data(chart_root) -> tuple[list[str], list[float], list[str]] | None:
    """Extract (categories, values, colors) from series 0 of *chart_root*.

    Returns None if the structure is missing or malformed.

    - categories: list of str label texts in idx order
    - values: list of float numerics in idx order
    - colors: list of hex strings (without ``#``) in idx order; empty string
      for any missing dPt colour
    """
    # Locate first <c:ser>
    ser = chart_root.find(f".//{{{_NS_C}}}ser")
    if ser is None:
        return None

    # --- category labels from <c:cat>//<c:strCache>//<c:pt> ---
    categories: list[str] = []
    cat_cache = ser.find(
        f"{{{_NS_C}}}cat/{{{_NS_C}}}strRef/{{{_NS_C}}}strCache"
    )
    if cat_cache is not None:
        pts = sorted(
            cat_cache.findall(f"{{{_NS_C}}}pt"),
            key=lambda e: int(e.get("idx", "0"))
        )
        for pt in pts:
            v = pt.find(f"{{{_NS_C}}}v")
            categories.append(v.text if v is not None and v.text else "")

    # --- numeric values from <c:val>//<c:numCache>//<c:pt> ---
    values: list[float] = []
    val_cache = ser.find(
        f"{{{_NS_C}}}val/{{{_NS_C}}}numRef/{{{_NS_C}}}numCache"
    )
    if val_cache is not None:
        pts = sorted(
            val_cache.findall(f"{{{_NS_C}}}pt"),
            key=lambda e: int(e.get("idx", "0"))
        )
        for pt in pts:
            v = pt.find(f"{{{_NS_C}}}v")
            try:
                values.append(float(v.text) if v is not None and v.text else 0.0)
            except ValueError:
                values.append(0.0)

    # --- per-point colour overrides from <c:dPt> ---
    # Build idx → hex map; fill list to max(len(categories), len(values))
    dpt_colors: dict[int, str] = {}
    for dpt in ser.findall(f"{{{_NS_C}}}dPt"):
        idx_el = dpt.find(f"{{{_NS_C}}}idx")
        if idx_el is None:
            continue
        idx = int(idx_el.get("val", "-1"))
        if idx < 0:
            continue
        sp_pr = dpt.find(f"{{{_NS_C}}}spPr")
        if sp_pr is None:
            continue
        clr_el = sp_pr.find(f".//{{{_NS_A}}}srgbClr")
        if clr_el is not None:
            val = clr_el.get("val")
            if val:
                dpt_colors[idx] = val.strip().upper()

    max_len = max(len(categories), len(values), 0)
    colors: list[str] = [dpt_colors.get(i, "") for i in range(max_len)]

    if not categories and not values:
        return None

    return categories, values, colors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def slotify_native_charts(
    dsl_text: str,
    asset_root: Path,
) -> tuple[str, list[str]]:
    """Walk *dsl_text* lines and add chart-slot kw-args to qualifying native lines.

    For each ``native <id> … parts_file:"…"`` line whose sidecar contains a
    supported chart type, three kw-args are appended:

        chart_categories:"{{ chart_N_categories | default('<b64>') }}"
        chart_values:"{{ chart_N_values | default('<b64>') }}"
        chart_colors:"{{ chart_N_colors | default('<b64>') }}"

    Lines that already carry ``chart_categories`` (idempotency), or whose chart
    type is unsupported, are left untouched.

    Parameters
    ----------
    dsl_text:
        Full text of a ``.slide.dsl`` layout file.
    asset_root:
        Path to the brand pack's ``assets/`` directory (used to resolve
        ``parts_file:`` references).

    Returns
    -------
    (new_dsl_text, log_lines)
        *log_lines* contains one entry per native line processed (skipped or
        slotified).
    """
    try:
        from lxml import etree
    except ImportError:
        return dsl_text, ["slotify_native_charts: lxml not available — skip"]

    out_lines: list[str] = []
    logs: list[str] = []
    chart_counter = 0

    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n").rstrip("\r")
        m = _NATIVE_LINE_RE.match(body)
        if m is None:
            out_lines.append(line)
            continue

        prefix, rest = m.group(1), m.group(2)
        kwargs = dict(_NATIVE_KW_RE.findall(rest))

        # Idempotency guard
        if "chart_categories" in kwargs:
            out_lines.append(line)
            continue

        parts_file = kwargs.get("parts_file")
        if not parts_file:
            out_lines.append(line)
            continue

        entries = _load_sidecar(parts_file, asset_root)
        if entries is None:
            out_lines.append(line)
            continue

        chart_xml = _find_chart_xml(entries)
        if chart_xml is None:
            # No chart part in this sidecar (e.g. diagram)
            out_lines.append(line)
            continue

        try:
            root = etree.fromstring(chart_xml.encode("utf-8"))
        except Exception as exc:
            logs.append(f"skipped {parts_file!r}: lxml parse error — {exc}")
            out_lines.append(line)
            continue

        chart_el = _detect_chart_type(root)
        if chart_el is None:
            tag_name = ""
            plot_area = root.find(f".//{{{_NS_C}}}plotArea")
            if plot_area is not None:
                for child in plot_area:
                    if isinstance(child.tag, str) and child.tag.startswith(f"{{{_NS_C}}}") and child.tag.endswith("Chart"):
                        tag_name = child.tag.split("}")[-1]
                        break
            logs.append(
                f"skipped {parts_file!r}: unsupported chart type"
                + (f" ({tag_name})" if tag_name else "")
            )
            out_lines.append(line)
            continue

        result = _extract_series_data(root)
        if result is None:
            logs.append(f"skipped {parts_file!r}: could not extract series data")
            out_lines.append(line)
            continue

        categories, values, colors = result
        chart_counter += 1
        n = chart_counter

        cats_b64 = _b64_json(categories)
        vals_b64 = _b64_json(values)
        cols_b64 = _b64_json(colors)

        new_body = (
            f'{prefix}{rest} '
            f'chart_categories:"{{{{ chart_{n}_categories | default(\'{cats_b64}\') }}}}" '
            f'chart_values:"{{{{ chart_{n}_values | default(\'{vals_b64}\') }}}}" '
            f'chart_colors:"{{{{ chart_{n}_colors | default(\'{cols_b64}\') }}}}"'
        )
        logs.append(
            f"slotified chart_{n}: {len(categories)} categories, "
            f"{len(values)} values, {len(colors)} color overrides"
        )
        # Preserve line ending
        eol = "\n" if line.endswith("\n") else ""
        out_lines.append(new_body + eol)

    return "".join(out_lines), logs

"""Tests for slotify_native_charts — promotes qualifying <c:chart> elements
inside native payloads to top-level ``svg … from:`` diagram DSL lines."""
from __future__ import annotations

import base64
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Namespace constants (mirroring the module under test)
# ---------------------------------------------------------------------------

_NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"

_EMU = 9525  # 1 design-px in EMU


def _b64(xml: str) -> str:
    return base64.b64encode(xml.encode()).decode("ascii")


# ---------------------------------------------------------------------------
# XML fragment builders
# ---------------------------------------------------------------------------

def _make_bar_chart_xml(
    x_emu: int,
    y_emu: int,
    cx_emu: int,
    cy_emu: int,
    values: list[float] | None = None,
    categories: list[str] | None = None,
    series_color: str | None = None,
    dpt_colors: dict[int, str] | None = None,
) -> str:
    """Build a minimal <p:graphicFrame> containing a <c:barChart>."""
    values = values or [10.0, 20.0, 15.0]
    categories = categories or ["A", "B", "C"]
    dpt_colors = dpt_colors or {}

    # Build <c:val> numeric reference
    val_pts = "".join(
        f'<c:pt xmlns:c="{_NS_C}" idx="{i}"><c:v>{v}</c:v></c:pt>'
        for i, v in enumerate(values)
    )
    val_elem = (
        f'<c:val xmlns:c="{_NS_C}">'
        f'<c:numLit xmlns:c="{_NS_C}">'
        f'{val_pts}'
        f'</c:numLit></c:val>'
    )

    # Build <c:cat> string reference
    cat_pts = "".join(
        f'<c:pt xmlns:c="{_NS_C}" idx="{i}"><c:v>{lbl}</c:v></c:pt>'
        for i, lbl in enumerate(categories)
    )
    cat_elem = (
        f'<c:cat xmlns:c="{_NS_C}">'
        f'<c:strLit xmlns:c="{_NS_C}">'
        f'{cat_pts}'
        f'</c:strLit></c:cat>'
    )

    # Series-level colour
    ser_spPr = ""
    if series_color:
        ser_spPr = (
            f'<c:spPr xmlns:c="{_NS_C}">'
            f'<a:solidFill xmlns:a="{_NS_A}">'
            f'<a:srgbClr xmlns:a="{_NS_A}" val="{series_color}"/>'
            f'</a:solidFill></c:spPr>'
        )

    # Per-data-point colour overrides
    dpt_elems = ""
    for idx, hex_color in dpt_colors.items():
        dpt_elems += (
            f'<c:dPt xmlns:c="{_NS_C}">'
            f'<c:idx xmlns:c="{_NS_C}" val="{idx}"/>'
            f'<c:spPr xmlns:c="{_NS_C}">'
            f'<a:solidFill xmlns:a="{_NS_A}">'
            f'<a:srgbClr xmlns:a="{_NS_A}" val="{hex_color}"/>'
            f'</a:solidFill></c:spPr>'
            f'</c:dPt>'
        )

    bar_chart = (
        f'<c:barChart xmlns:c="{_NS_C}">'
        f'<c:ser xmlns:c="{_NS_C}">'
        f'{ser_spPr}'
        f'{dpt_elems}'
        f'{cat_elem}'
        f'{val_elem}'
        f'</c:ser>'
        f'</c:barChart>'
    )

    return _wrap_in_graphic_frame(bar_chart, x_emu, y_emu, cx_emu, cy_emu)


def _make_pie_chart_xml(
    x_emu: int,
    y_emu: int,
    cx_emu: int,
    cy_emu: int,
    values: list[float] | None = None,
    categories: list[str] | None = None,
    dpt_colors: dict[int, str] | None = None,
    doughnut: bool = False,
) -> str:
    """Build a minimal <p:graphicFrame> containing a <c:pieChart>."""
    values = values or [30.0, 50.0, 20.0]
    categories = categories or ["X", "Y", "Z"]
    dpt_colors = dpt_colors or {}

    val_pts = "".join(
        f'<c:pt xmlns:c="{_NS_C}" idx="{i}"><c:v>{v}</c:v></c:pt>'
        for i, v in enumerate(values)
    )
    val_elem = (
        f'<c:val xmlns:c="{_NS_C}">'
        f'<c:numLit xmlns:c="{_NS_C}">{val_pts}</c:numLit>'
        f'</c:val>'
    )

    cat_pts = "".join(
        f'<c:pt xmlns:c="{_NS_C}" idx="{i}"><c:v>{lbl}</c:v></c:pt>'
        for i, lbl in enumerate(categories)
    )
    cat_elem = (
        f'<c:cat xmlns:c="{_NS_C}">'
        f'<c:strLit xmlns:c="{_NS_C}">{cat_pts}</c:strLit>'
        f'</c:cat>'
    )

    dpt_elems = ""
    for idx, hex_color in dpt_colors.items():
        dpt_elems += (
            f'<c:dPt xmlns:c="{_NS_C}">'
            f'<c:idx xmlns:c="{_NS_C}" val="{idx}"/>'
            f'<c:spPr xmlns:c="{_NS_C}">'
            f'<a:solidFill xmlns:a="{_NS_A}">'
            f'<a:srgbClr xmlns:a="{_NS_A}" val="{hex_color}"/>'
            f'</a:solidFill></c:spPr>'
            f'</c:dPt>'
        )

    chart_type = "doughnutChart" if doughnut else "pieChart"
    pie_chart = (
        f'<c:{chart_type} xmlns:c="{_NS_C}">'
        f'<c:ser xmlns:c="{_NS_C}">'
        f'{dpt_elems}'
        f'{cat_elem}'
        f'{val_elem}'
        f'</c:ser>'
        f'</c:{chart_type}>'
    )

    return _wrap_in_graphic_frame(pie_chart, x_emu, y_emu, cx_emu, cy_emu)


def _make_line_chart_xml(
    x_emu: int,
    y_emu: int,
    cx_emu: int,
    cy_emu: int,
) -> str:
    """Build a minimal <p:graphicFrame> containing a <c:lineChart>."""
    line_chart = (
        f'<c:lineChart xmlns:c="{_NS_C}">'
        f'<c:ser xmlns:c="{_NS_C}">'
        f'<c:val xmlns:c="{_NS_C}">'
        f'<c:numLit xmlns:c="{_NS_C}">'
        f'<c:pt xmlns:c="{_NS_C}" idx="0"><c:v>1</c:v></c:pt>'
        f'<c:pt xmlns:c="{_NS_C}" idx="1"><c:v>2</c:v></c:pt>'
        f'</c:numLit></c:val>'
        f'</c:ser>'
        f'</c:lineChart>'
    )
    return _wrap_in_graphic_frame(line_chart, x_emu, y_emu, cx_emu, cy_emu)


def _wrap_in_graphic_frame(chart_body_xml: str, x_emu: int, y_emu: int, cx_emu: int, cy_emu: int) -> str:
    """Wrap a chart plot-area XML in a <p:graphicFrame> with xfrm geometry."""
    return (
        f'<p:graphicFrame xmlns:p="{_NS_P}" xmlns:a="{_NS_A}">'
        f'<p:xfrm>'
        f'<a:off x="{x_emu}" y="{y_emu}"/>'
        f'<a:ext cx="{cx_emu}" cy="{cy_emu}"/>'
        f'</p:xfrm>'
        f'<p:graphic xmlns:p="{_NS_P}">'
        f'<p:graphicData xmlns:p="{_NS_P}">'
        f'<c:chart xmlns:c="{_NS_C}">'
        f'<c:plotArea xmlns:c="{_NS_C}">'
        f'{chart_body_xml}'
        f'</c:plotArea>'
        f'</c:chart>'
        f'</p:graphicData>'
        f'</p:graphic>'
        f'</p:graphicFrame>'
    )


# Canvas: 1920x1080 design-px
_CANVAS_W_PX = 1920
_CANVAS_H_PX = 1080

# A chart occupying a large portion of the canvas
_CHART_X_EMU = 100 * _EMU
_CHART_Y_EMU = 200 * _EMU
_CHART_CX_EMU = 800 * _EMU
_CHART_CY_EMU = 400 * _EMU


# ---------------------------------------------------------------------------
# Import under test
# ---------------------------------------------------------------------------

from feinschliff_builder.decompile.slotify_native_charts import slotify_native_charts


# ---------------------------------------------------------------------------
# Happy path: 3-bar barchart promotion
# ---------------------------------------------------------------------------


def test_barchart_promoted_to_svg_slot(tmp_path):
    """A 3-bar barChart: emits svg DSL line, writes sidecar, removes <c:chart>."""
    values = [10.0, 20.0, 15.0]
    categories = ["Q1", "Q2", "Q3"]
    xml = _make_bar_chart_xml(
        _CHART_X_EMU, _CHART_Y_EMU, _CHART_CX_EMU, _CHART_CY_EMU,
        values=values,
        categories=categories,
    )
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    dsl = f'canvas 1920x1080\nnative frame1 b64:"{_b64(xml)}"\n'

    new_dsl, slots, logs = slotify_native_charts(
        dsl, asset_root,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    # One slot promoted
    assert len(slots) == 1
    s = slots[0]
    assert s["name"] == "chart_1"
    assert s["native_id"] == "frame1"
    assert s["x"] == 100
    assert s["y"] == 200
    assert s["w"] == 800
    assert s["h"] == 400

    # DSL contains svg directive before the native line
    lines = new_dsl.splitlines()
    svg_idx = next((i for i, l in enumerate(lines) if l.startswith("svg chart_1 ")), None)
    native_idx = next((i for i, l in enumerate(lines) if l.startswith("native ")), None)
    assert svg_idx is not None, "Expected svg chart_1 line"
    assert native_idx is not None, "Expected native line"
    assert svg_idx < native_idx, "svg line must precede native line"

    # DSL line has correct bbox
    svg_line = lines[svg_idx]
    assert "100,200 800x400" in svg_line
    assert 'from:"' in svg_line

    # Sidecar written under assets/diagrams/
    diagrams_dir = asset_root / "diagrams"
    assert diagrams_dir.is_dir()
    sidecar_files = list(diagrams_dir.glob("chart_frame1_1.svg.dsl"))
    assert len(sidecar_files) == 1, f"Expected sidecar file, got: {list(diagrams_dir.iterdir())}"

    # Sidecar contains the extracted values and barchart directive
    sidecar_body = sidecar_files[0].read_text()
    assert "barchart" in sidecar_body
    # All three values present
    for v in values:
        assert str(v) in sidecar_body
    # Category labels present as comments
    for cat in categories:
        assert cat in sidecar_body

    # <c:chart> removed from native payload
    new_b64 = re.search(r'b64:"([^"]+)"', new_dsl).group(1)
    new_xml = base64.b64decode(new_b64).decode("utf-8")
    assert "c:chart" not in new_xml or f"{{{_NS_C}}}chart" not in new_xml

    # At least one log line mentioning the promotion
    assert any("frame1" in l and "chart_1" in l for l in logs)


# ---------------------------------------------------------------------------
# Happy path: pie chart with dPt colour override
# ---------------------------------------------------------------------------


def test_pie_chart_with_dpt_color_override(tmp_path):
    """A pieChart with one dPt colour override: sidecar uses that hex colour."""
    values = [30.0, 50.0, 20.0]
    # Override slice index 1 with red
    dpt_colors = {1: "FF0000"}

    xml = _make_pie_chart_xml(
        _CHART_X_EMU, _CHART_Y_EMU, _CHART_CX_EMU, _CHART_CY_EMU,
        values=values,
        dpt_colors=dpt_colors,
    )
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    dsl = f'native frame1 b64:"{_b64(xml)}"\n'

    new_dsl, slots, logs = slotify_native_charts(
        dsl, asset_root,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    assert len(slots) == 1
    assert slots[0]["name"] == "chart_1"

    sidecar_files = list((asset_root / "diagrams").glob("chart_frame1_1.svg.dsl"))
    assert len(sidecar_files) == 1
    sidecar_body = sidecar_files[0].read_text()

    # Must be a pie primitive
    assert "pie " in sidecar_body

    # The dPt colour override (#FF0000) should appear in the sidecar
    assert "#FF0000" in sidecar_body or "FF0000" in sidecar_body.upper()

    # All values present
    for v in values:
        assert str(v) in sidecar_body


# ---------------------------------------------------------------------------
# doughnut chart maps to pie primitive
# ---------------------------------------------------------------------------


def test_doughnut_chart_maps_to_pie(tmp_path):
    """doughnutChart is treated as pie — same primitive."""
    xml = _make_pie_chart_xml(
        _CHART_X_EMU, _CHART_Y_EMU, _CHART_CX_EMU, _CHART_CY_EMU,
        doughnut=True,
    )
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    dsl = f'native frame1 b64:"{_b64(xml)}"\n'

    new_dsl, slots, logs = slotify_native_charts(dsl, asset_root)

    assert len(slots) == 1
    sidecar_body = (asset_root / "diagrams" / "chart_frame1_1.svg.dsl").read_text()
    assert "pie " in sidecar_body


# ---------------------------------------------------------------------------
# Unsupported chart type: lineChart → NOT promoted; native stays unchanged
# ---------------------------------------------------------------------------


def test_line_chart_not_promoted(tmp_path):
    """lineChart is unsupported in v1 — native stays unchanged; skip logged."""
    xml = _make_line_chart_xml(
        _CHART_X_EMU, _CHART_Y_EMU, _CHART_CX_EMU, _CHART_CY_EMU,
    )
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    original_dsl = f'canvas 1920x1080\nnative frame1 b64:"{_b64(xml)}"\n'

    new_dsl, slots, logs = slotify_native_charts(
        original_dsl, asset_root,
        canvas_w_px=_CANVAS_W_PX, canvas_h_px=_CANVAS_H_PX,
    )

    # No promotion
    assert slots == []
    # DSL unchanged
    assert new_dsl == original_dsl
    # Skip logged but no failure
    assert any("skip" in l.lower() or "lineChart" in l or "line" in l.lower() for l in logs)
    # No sidecar written
    diagrams_dir = asset_root / "diagrams"
    assert not diagrams_dir.exists() or list(diagrams_dir.iterdir()) == []


# ---------------------------------------------------------------------------
# Native without any chart is left untouched
# ---------------------------------------------------------------------------


def test_native_without_chart_untouched(tmp_path):
    payload = f'<p:sp xmlns:p="{_NS_P}"><a:t xmlns:a="{_NS_A}">Hello</a:t></p:sp>'
    dsl = f'native text1 b64:"{_b64(payload)}"\n'
    asset_root = tmp_path / "assets"
    asset_root.mkdir()

    new_dsl, slots, logs = slotify_native_charts(dsl, asset_root)

    assert slots == []
    assert logs == []
    assert new_dsl == dsl


# ---------------------------------------------------------------------------
# asset_root=None → no-op
# ---------------------------------------------------------------------------


def test_no_asset_root_is_noop():
    xml = _make_bar_chart_xml(
        _CHART_X_EMU, _CHART_Y_EMU, _CHART_CX_EMU, _CHART_CY_EMU,
    )
    dsl = f'native frame1 b64:"{_b64(xml)}"\n'

    new_dsl, slots, logs = slotify_native_charts(dsl, None)

    assert slots == []
    assert new_dsl == dsl


# ---------------------------------------------------------------------------
# next_idx parameter controls slot numbering
# ---------------------------------------------------------------------------


def test_next_idx_controls_slot_name(tmp_path):
    xml = _make_bar_chart_xml(
        _CHART_X_EMU, _CHART_Y_EMU, _CHART_CX_EMU, _CHART_CY_EMU,
    )
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    dsl = f'native frame1 b64:"{_b64(xml)}"\n'

    _, slots, _ = slotify_native_charts(dsl, asset_root, next_idx=5)

    assert len(slots) == 1
    assert slots[0]["name"] == "chart_5"


# ---------------------------------------------------------------------------
# svg DSL line appears before native line
# ---------------------------------------------------------------------------


def test_svg_line_before_native(tmp_path):
    xml = _make_bar_chart_xml(
        _CHART_X_EMU, _CHART_Y_EMU, _CHART_CX_EMU, _CHART_CY_EMU,
    )
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    dsl = f'canvas 1920x1080\nnative frame1 b64:"{_b64(xml)}"\n'

    new_dsl, slots, _ = slotify_native_charts(dsl, asset_root)

    lines = new_dsl.splitlines()
    svg_idx = next(i for i, l in enumerate(lines) if l.startswith("svg "))
    native_idx = next(i for i, l in enumerate(lines) if l.startswith("native "))
    assert svg_idx < native_idx


# ---------------------------------------------------------------------------
# Idempotency: second run finds no chart (already removed)
# ---------------------------------------------------------------------------


def test_idempotent_second_run(tmp_path):
    xml = _make_bar_chart_xml(
        _CHART_X_EMU, _CHART_Y_EMU, _CHART_CX_EMU, _CHART_CY_EMU,
    )
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    dsl = f'native frame1 b64:"{_b64(xml)}"\n'

    first_dsl, slots1, _ = slotify_native_charts(dsl, asset_root)
    second_dsl, slots2, _ = slotify_native_charts(first_dsl, asset_root, next_idx=2)

    assert slots2 == []
    assert first_dsl == second_dsl


# ---------------------------------------------------------------------------
# Sidecar xml_file payload: chart removed in the sidecar file on disk
# ---------------------------------------------------------------------------


def test_sidecar_xml_file_chart_removed(tmp_path):
    """When native uses xml_file: the sidecar is updated on disk."""
    asset_root = tmp_path / "assets"
    asset_root.mkdir()

    xml = _make_bar_chart_xml(
        _CHART_X_EMU, _CHART_Y_EMU, _CHART_CX_EMU, _CHART_CY_EMU,
        values=[5.0, 10.0],
    )
    sidecar_name = "slide01_chart.xml"
    (asset_root / sidecar_name).write_text(xml, encoding="utf-8")

    dsl = f'native frame1 xml_file:"{sidecar_name}"\n'

    new_dsl, slots, logs = slotify_native_charts(dsl, asset_root)

    assert len(slots) == 1
    # Sidecar on disk should no longer have <c:chart
    updated = (asset_root / sidecar_name).read_text()
    assert "c:chart" not in updated or "plotArea" not in updated

    # DSL line unchanged (sidecar re-written, native line stays the same)
    assert 'xml_file:"' in new_dsl


# ---------------------------------------------------------------------------
# Default data in sidecar matches source PPTX values
# ---------------------------------------------------------------------------


def test_default_data_matches_source_values(tmp_path):
    """The sidecar bakes in the original values as defaults."""
    values = [42.0, 7.5, 100.0]
    xml = _make_bar_chart_xml(
        _CHART_X_EMU, _CHART_Y_EMU, _CHART_CX_EMU, _CHART_CY_EMU,
        values=values,
    )
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    dsl = f'native frame1 b64:"{_b64(xml)}"\n'

    _, slots, _ = slotify_native_charts(dsl, asset_root)

    assert len(slots) == 1
    sidecar = asset_root / "diagrams" / "chart_frame1_1.svg.dsl"
    body = sidecar.read_text()
    for v in values:
        assert str(v) in body, f"Value {v} missing from sidecar: {body!r}"

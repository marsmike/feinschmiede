"""Tests for slotify_native_charts — expose chart data as bindable DSL slots.

Design invariant: the chart OOXML is NEVER modified by the slotify pass.
Only kw-args are added to the DSL line.  The build-time patcher is tested
separately via _patch_chart_entries + _patch_chart_xml.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from feinschliff_builder.decompile.slotify_native_charts import (
    slotify_native_charts,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _b64j(obj) -> str:
    return base64.b64encode(json.dumps(obj).encode()).decode()


def _decode_kwarg(value: str):
    return json.loads(base64.b64decode(value).decode())


def _make_chart_xml(chart_type: str = "pieChart", categories=None, values=None, colors=None) -> str:
    """Build a minimal chart XML fragment for testing."""
    if categories is None:
        categories = ["Q1", "Q2"]
    if values is None:
        values = [8.2, 3.2]
    if colors is None:
        colors = ["FF6840", ""]

    cat_pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>' for i, v in enumerate(categories))
    val_pts = "".join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>' for i, v in enumerate(values))

    dPts = ""
    for i, hex_c in enumerate(colors):
        if hex_c:
            dPts += (
                f'<c:dPt><c:idx val="{i}"/><c:spPr>'
                f'<a:solidFill xmlns:a="{_NS_A}"><a:srgbClr val="{hex_c}"/></a:solidFill>'
                f"</c:spPr></c:dPt>"
            )

    return (
        f'<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\'?>'
        f'<c:chartSpace xmlns:c="{_NS_C}" xmlns:a="{_NS_A}">'
        f"<c:chart><c:plotArea>"
        f"<c:{chart_type}>"
        f"<c:ser><c:idx val=\"0\"/><c:order val=\"0\"/>"
        f"{dPts}"
        f"<c:cat><c:strRef><c:strCache>"
        f'<c:ptCount val="{len(categories)}"/>'
        f"{cat_pts}"
        f"</c:strCache></c:strRef></c:cat>"
        f"<c:val><c:numRef><c:numCache>"
        f'<c:ptCount val="{len(values)}"/>'
        f"{val_pts}"
        f"</c:numCache></c:numRef></c:val>"
        f"</c:ser>"
        f"</c:{chart_type}>"
        f"</c:plotArea></c:chart>"
        f"</c:chartSpace>"
    )


def _make_sidecar_json(chart_xml: str) -> list:
    """Build a parts sidecar list with a single chart+xml entry."""
    return [
        {
            "partname": "/ppt/charts/chart1.xml",
            "content_type": "application/vnd.openxmlformats-officedocument.drawingml.chart+xml",
            "blob": base64.b64encode(chart_xml.encode()).decode(),
            "reltype": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart",
            "parent": "slide",
            "src_rid": "rId2",
        }
    ]


def _write_sidecar(tmp_path: Path, data: list, name: str = "chart1.json") -> Path:
    native_dir = tmp_path / "native"
    native_dir.mkdir(parents=True, exist_ok=True)
    p = native_dir / name
    p.write_text(json.dumps(data))
    return p


def _make_native_line(parts_rel: str = "native/chart1.json") -> str:
    b64_frame = base64.b64encode(
        b'<p:graphicFrame xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
        b' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        b'<p:nvGraphicFramePr/><p:xfrm/><a:graphic/></p:graphicFrame>'
    ).decode()
    return f'native graphic1 b64:"{b64_frame}" parts_file:"{parts_rel}"\n'


# ---------------------------------------------------------------------------
# Slotify-side tests
# ---------------------------------------------------------------------------

class TestSlotifyNativeCharts:
    def test_pie_chart_gains_three_kwargs(self, tmp_path):
        """Slotify on golden pie chart → three new kw-args on the native line."""
        chart_xml = _make_chart_xml("pieChart", ["Q1", "Q2"], [8.2, 3.2], ["FF6840", ""])
        sidecar = _make_sidecar_json(chart_xml)
        sidecar_path = _write_sidecar(tmp_path, sidecar)

        dsl = f'canvas 1920x1080\n{_make_native_line("native/chart1.json")}'
        new_dsl, logs = slotify_native_charts(dsl, tmp_path)

        # Must gain chart_categories, chart_values, chart_colors
        assert 'chart_categories:"' in new_dsl
        assert 'chart_values:"' in new_dsl
        assert 'chart_colors:"' in new_dsl

        # Extract the native line
        native_line = next(ln for ln in new_dsl.splitlines() if ln.startswith("native "))

        # Find and decode kw-arg values
        import re
        kw = dict(re.findall(r'(\w+):"([^"]*)"', native_line))

        cats = _decode_kwarg(
            re.search(r"chart_1_categories \| default\('([^']+)'\)", native_line).group(1)
        )
        vals = _decode_kwarg(
            re.search(r"chart_1_values \| default\('([^']+)'\)", native_line).group(1)
        )
        cols = _decode_kwarg(
            re.search(r"chart_1_colors \| default\('([^']+)'\)", native_line).group(1)
        )

        assert cats == ["Q1", "Q2"]
        assert vals == pytest.approx([8.2, 3.2])
        assert cols[0] == "FF6840"

    def test_bar_chart_slotified(self, tmp_path):
        """barChart is a supported type — gets slotified."""
        chart_xml = _make_chart_xml("barChart", ["A", "B"], [10.0, 20.0], ["", ""])
        sidecar = _make_sidecar_json(chart_xml)
        _write_sidecar(tmp_path, sidecar)

        dsl = _make_native_line("native/chart1.json")
        new_dsl, logs = slotify_native_charts(dsl, tmp_path)
        assert "chart_categories" in new_dsl
        assert any("slotified chart_1" in lg for lg in logs)

    def test_line_chart_skipped(self, tmp_path):
        """lineChart is unsupported in v1 — native line left unchanged."""
        chart_xml = _make_chart_xml("lineChart", ["A", "B"], [1.0, 2.0], ["", ""])
        sidecar = _make_sidecar_json(chart_xml)
        _write_sidecar(tmp_path, sidecar)

        original_line = _make_native_line("native/chart1.json")
        new_dsl, logs = slotify_native_charts(original_line, tmp_path)

        assert "chart_categories" not in new_dsl
        assert new_dsl.rstrip("\n") == original_line.rstrip("\n")
        assert any("unsupported chart type" in lg for lg in logs)

    def test_idempotency(self, tmp_path):
        """Running slotify twice does NOT double-add the kwargs."""
        chart_xml = _make_chart_xml("pieChart")
        sidecar = _make_sidecar_json(chart_xml)
        _write_sidecar(tmp_path, sidecar)

        dsl = _make_native_line("native/chart1.json")
        once, _ = slotify_native_charts(dsl, tmp_path)
        twice, _ = slotify_native_charts(once, tmp_path)

        # Count occurrences of chart_categories in the native line
        native_line = next(ln for ln in twice.splitlines() if ln.startswith("native "))
        assert native_line.count("chart_categories") == 1
        assert native_line.count("chart_values") == 1
        assert native_line.count("chart_colors") == 1

    def test_monotonic_counter_across_charts(self, tmp_path):
        """Multiple charts in the same layout get chart_1_*, chart_2_*, …"""
        chart_xml = _make_chart_xml("pieChart")
        sidecar = _make_sidecar_json(chart_xml)
        # Write same sidecar under two names
        (tmp_path / "native").mkdir(exist_ok=True)
        for name in ("chart1.json", "chart2.json"):
            (tmp_path / "native" / name).write_text(json.dumps(sidecar))

        dsl = (
            _make_native_line("native/chart1.json")
            + _make_native_line("native/chart2.json").replace("graphic1", "graphic2")
        )
        new_dsl, logs = slotify_native_charts(dsl, tmp_path)

        assert "chart_1_categories" in new_dsl
        assert "chart_2_categories" in new_dsl

    def test_golden_fixture(self, tmp_path):
        """Slotify against the golden BSH-derived fixture (sanitised)."""
        fixture_path = Path(__file__).parent / "fixtures" / "chart_pie_2slice.json"
        if not fixture_path.is_file():
            pytest.skip("golden fixture not present")

        import shutil
        native_dir = tmp_path / "native"
        native_dir.mkdir()
        dest = native_dir / "chart_pie_2slice.json"
        shutil.copy(fixture_path, dest)

        dsl = _make_native_line("native/chart_pie_2slice.json")
        new_dsl, logs = slotify_native_charts(dsl, tmp_path)

        assert "chart_categories" in new_dsl
        native_line = next(ln for ln in new_dsl.splitlines() if ln.startswith("native "))

        import re
        cats = _decode_kwarg(
            re.search(r"chart_1_categories \| default\('([^']+)'\)", native_line).group(1)
        )
        assert cats == ["1. Quartal", "2. Quartal"]

        vals = _decode_kwarg(
            re.search(r"chart_1_values \| default\('([^']+)'\)", native_line).group(1)
        )
        assert len(vals) == 2


# ---------------------------------------------------------------------------
# Build-time patcher tests
# ---------------------------------------------------------------------------

class TestPatchChartEntries:
    """Test _patch_chart_entries via the public pptx_emit surface."""

    def _make_mock_node(self, **kw_args):
        """Return a minimal object that looks like DSLNode for the patcher."""
        from types import SimpleNamespace
        return SimpleNamespace(kw_args=kw_args, line_no=1)

    def _patch(self, chart_xml: str, **kw_args) -> str:
        """Apply _patch_chart_entries and return the resulting chart XML."""
        from feinschliff.dsl.pptx_emit import _patch_chart_entries
        entry = {
            "partname": "/ppt/charts/chart1.xml",
            "content_type": "application/vnd.openxmlformats-officedocument.drawingml.chart+xml",
            "blob": base64.b64encode(chart_xml.encode()).decode(),
            "reltype": "...",
            "parent": "slide",
            "src_rid": "rId2",
        }
        entries = [entry]
        node = self._make_mock_node(**kw_args)
        _patch_chart_entries(entries, node)
        return base64.b64decode(entries[0]["blob"]).decode()

    def test_no_bindings_chart_unchanged(self):
        """With no chart_* kw-args the blob is left byte-for-byte identical."""
        chart_xml = _make_chart_xml("pieChart", ["Q1", "Q2"], [8.2, 3.2], ["FF6840", ""])
        from feinschliff.dsl.pptx_emit import _patch_chart_entries
        entry = {
            "partname": "/ppt/charts/chart1.xml",
            "content_type": "application/vnd.openxmlformats-officedocument.drawingml.chart+xml",
            "blob": base64.b64encode(chart_xml.encode()).decode(),
            "reltype": "...",
            "parent": "slide",
            "src_rid": "rId2",
        }
        original_blob = entry["blob"]
        node = self._make_mock_node()  # no chart_* kw-args
        _patch_chart_entries([entry], node)
        # Blob must be identical (no patching happened at all)
        assert entry["blob"] == original_blob

    def test_patch_values(self):
        """Bound chart_values replaces <c:v> in numCache."""
        chart_xml = _make_chart_xml("pieChart", ["Q1", "Q2"], [8.2, 3.2], ["", ""])
        new_vals = [10.0, 20.0, 30.0]
        result = self._patch(
            chart_xml,
            chart_values=_b64j(new_vals),
        )
        from lxml import etree
        root = etree.fromstring(result.encode())
        NS_C = _NS_C
        val_cache = root.find(f".//{{{NS_C}}}numCache")
        assert val_cache is not None
        pts = val_cache.findall(f"{{{NS_C}}}pt")
        extracted = [float(pt.find(f"{{{NS_C}}}v").text) for pt in pts]
        assert extracted == pytest.approx([10.0, 20.0, 30.0])

    def test_patch_categories(self):
        """Bound chart_categories replaces <c:v> text in strCache."""
        chart_xml = _make_chart_xml("pieChart", ["Q1", "Q2"], [8.2, 3.2], ["", ""])
        new_cats = ["Jan", "Feb", "Mar"]
        result = self._patch(
            chart_xml,
            chart_categories=_b64j(new_cats),
        )
        from lxml import etree
        root = etree.fromstring(result.encode())
        NS_C = _NS_C
        str_cache = root.find(f".//{{{NS_C}}}strCache")
        assert str_cache is not None
        pts = str_cache.findall(f"{{{NS_C}}}pt")
        extracted = [pt.find(f"{{{NS_C}}}v").text for pt in pts]
        assert extracted == ["Jan", "Feb", "Mar"]

    def test_patch_colors(self):
        """Bound chart_colors updates <a:srgbClr val> for each dPt."""
        chart_xml = _make_chart_xml(
            "pieChart", ["Q1", "Q2", "Q3"], [1.0, 2.0, 3.0],
            ["FF0000", "00FF00", "0000FF"]
        )
        new_colors = ["00FF00", "0000FF", "FF0000"]
        result = self._patch(
            chart_xml,
            chart_colors=_b64j(new_colors),
        )
        from lxml import etree
        root = etree.fromstring(result.encode())
        NS_C = _NS_C
        NS_A = _NS_A
        dpts = root.findall(f".//{{{NS_C}}}dPt")
        assert len(dpts) == 3
        extracted = []
        for dpt in sorted(dpts, key=lambda e: int(e.find(f"{{{NS_C}}}idx").get("val", "0"))):
            clr = dpt.find(f".//{{{NS_A}}}srgbClr")
            extracted.append(clr.get("val") if clr is not None else None)
        assert extracted == ["00FF00", "0000FF", "FF0000"]

    def test_patch_colors_creates_new_dpt(self):
        """If no dPt exists for a given idx, the patcher creates one."""
        # chart with NO dPt elements
        chart_xml = _make_chart_xml("pieChart", ["Q1", "Q2"], [5.0, 6.0], ["", ""])
        new_colors = ["AABBCC", ""]
        result = self._patch(
            chart_xml,
            chart_colors=_b64j(new_colors),
        )
        from lxml import etree
        root = etree.fromstring(result.encode())
        NS_C = _NS_C
        NS_A = _NS_A
        dpts = root.findall(f".//{{{NS_C}}}dPt")
        assert len(dpts) == 1  # only idx=0 has a colour
        clr = dpts[0].find(f".//{{{NS_A}}}srgbClr")
        assert clr is not None
        assert clr.get("val") == "AABBCC"

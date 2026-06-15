"""Tests for the per-layout semantic annotation framework.

Covers:
- manifest_for_pack: slot_inventory counts, existing annotation round-trip
- apply_annotation: write, read-back, partial update, lossy-field preservation
- CLI subcommands: describe-layouts and annotate-layout end-to-end
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
import yaml

from feinschliff_builder.cli.main import main
from feinschliff_builder.decompile.annotate_layouts import (
    apply_annotation,
    manifest_for_pack,
)

# ---------------------------------------------------------------------------
# Helpers for building synthetic pack fixtures
# ---------------------------------------------------------------------------

_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"


def _b64(xml: str) -> str:
    return base64.b64encode(xml.encode()).decode("ascii")


def _chart_xml() -> str:
    """Minimal XML that passes the <c:chart sniff."""
    return (
        f'<c:chartSpace xmlns:c="{_NS_C}">'
        f'  <c:chart/>'
        f'</c:chartSpace>'
    )


_LAYOUT_BODY = """\
# synthetic layout
canvas 1920x1080
theme acme

text 100,100 style:title size:44pt maxwidth:800 maxheight:120 "{{ text_1 | default(\\"Headline\\") }}"
text 100,280 style:body size:18pt maxwidth:800 maxheight:400 "{{ text_2 | default(\\"Body copy\\") }}"
text 100,280 style:body size:18pt maxwidth:800 maxheight:400 "{{ text_3 | default(\\"Third slot\\") }}"
picture 1000,100 800x700 path:"{{ image | default(\\"photo.jpg\\") }}" cover:true
"""


def _make_pack(
    tmp_path: Path,
    *,
    stem: str = "acme-slide",
    body_extra: str = "",
    frontmatter: dict | None = None,
) -> Path:
    """Create a minimal synthetic brand pack with one layout."""
    pack = tmp_path / "acme"
    (pack / "layouts").mkdir(parents=True)

    fm_block = ""
    if frontmatter is not None:
        fm_yaml = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
        fm_block = "---\n" + fm_yaml + "---\n"

    dsl = fm_block + _LAYOUT_BODY
    if body_extra:
        dsl += body_extra + "\n"

    (pack / "layouts" / f"{stem}.slide.dsl").write_text(dsl, encoding="utf-8")
    return pack


# ---------------------------------------------------------------------------
# manifest_for_pack: slot_inventory counts
# ---------------------------------------------------------------------------

class TestManifestSlotInventory:
    def test_text_and_image_counts(self, tmp_path):
        """3 text slots + 1 image slot are counted correctly."""
        pack = _make_pack(tmp_path)
        manifest = manifest_for_pack(pack)
        assert len(manifest) == 1
        inv = manifest[0]["slot_inventory"]
        assert inv["text_slots"] == 3
        assert inv["image_slots"] == 1

    def test_chart_in_native_payload(self, tmp_path):
        """A native payload containing <c:chart increments chart_count."""
        chart_b64 = _b64(_chart_xml())
        native_line = f'native chart b64:"{chart_b64}"'
        pack = _make_pack(tmp_path, body_extra=native_line)
        manifest = manifest_for_pack(pack)
        inv = manifest[0]["slot_inventory"]
        assert inv["chart_count"] == 1
        assert inv["table_count"] == 0
        assert inv["smartart_count"] == 0
        assert inv["native_graphic_frames"] == 1
        # Illustration (non-data) native should be 0
        assert inv["native_pics"] == 0

    def test_no_native_payloads(self, tmp_path):
        """Layout with no native lines has zeros for all native counts."""
        pack = _make_pack(tmp_path)
        manifest = manifest_for_pack(pack)
        inv = manifest[0]["slot_inventory"]
        assert inv["chart_count"] == 0
        assert inv["table_count"] == 0
        assert inv["smartart_count"] == 0
        assert inv["native_pics"] == 0
        assert inv["native_graphic_frames"] == 0

    def test_native_shape_reserved_zero(self, tmp_path):
        """native_shapes is always 0 (reserved field)."""
        pack = _make_pack(tmp_path)
        inv = manifest_for_pack(pack)[0]["slot_inventory"]
        assert inv["native_shapes"] == 0


# ---------------------------------------------------------------------------
# manifest_for_pack: annotation round-trip
# ---------------------------------------------------------------------------

class TestManifestAnnotationReading:
    def test_reads_existing_description_and_when_to_use(self, tmp_path):
        """Existing annotation values are surfaced in the manifest."""
        fm = {
            "role": "content-columns",
            "description": "A bold two-column comparison slide",
            "when_to_use": "Use for side-by-side comparisons.",
        }
        pack = _make_pack(tmp_path, frontmatter=fm)
        entry = manifest_for_pack(pack)[0]
        assert entry["current_description"] == "A bold two-column comparison slide"
        assert entry["current_when_to_use"] == "Use for side-by-side comparisons."

    def test_empty_string_defaults_when_missing(self, tmp_path):
        """Missing annotation fields default to empty string, not None."""
        pack = _make_pack(tmp_path, frontmatter={"role": "content-columns"})
        entry = manifest_for_pack(pack)[0]
        for key in (
            "current_description",
            "current_when_to_use",
            "current_when_not_to_use",
            "current_chrome_subject",
            "current_primary_message",
        ):
            assert entry[key] == "", f"{key} should be '' when absent"

    def test_primary_message_read(self, tmp_path):
        """primary_message is surfaced when present."""
        fm = {"role": "content-columns", "primary_message": "Act now."}
        pack = _make_pack(tmp_path, frontmatter=fm)
        entry = manifest_for_pack(pack)[0]
        assert entry["current_primary_message"] == "Act now."

    def test_stem_and_path(self, tmp_path):
        """stem and path are correct for the layout file."""
        pack = _make_pack(tmp_path, stem="globex-intro")
        entry = manifest_for_pack(pack)[0]
        assert entry["stem"] == "globex-intro"
        assert entry["path"].endswith("globex-intro.slide.dsl")

    def test_no_layouts_dir_returns_empty(self, tmp_path):
        """A pack directory without layouts/ returns an empty list."""
        pack = tmp_path / "empty-pack"
        pack.mkdir()
        assert manifest_for_pack(pack) == []

    def test_multiple_layouts_sorted(self, tmp_path):
        """Multiple layouts are returned sorted by stem."""
        pack = tmp_path / "multi"
        (pack / "layouts").mkdir(parents=True)
        for stem in ("zebra", "alpha", "middle"):
            (pack / "layouts" / f"{stem}.slide.dsl").write_text(
                "canvas 1920x1080\n", encoding="utf-8"
            )
        stems = [e["stem"] for e in manifest_for_pack(pack)]
        assert stems == sorted(stems)


# ---------------------------------------------------------------------------
# apply_annotation: write and read-back
# ---------------------------------------------------------------------------

class TestApplyAnnotation:
    def _layout_with_fm(self, tmp_path: Path, fm: dict, body: str = "") -> Path:
        fm_yaml = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
        dsl = f"---\n{fm_yaml}---\n{body or 'canvas 1920x1080\n'}"
        p = tmp_path / "test.slide.dsl"
        p.write_text(dsl, encoding="utf-8")
        return p

    def _layout_no_fm(self, tmp_path: Path) -> Path:
        p = tmp_path / "bare.slide.dsl"
        p.write_text("canvas 1920x1080\n", encoding="utf-8")
        return p

    def test_writes_description_into_empty_frontmatter(self, tmp_path):
        """apply_annotation writes description into a layout with no frontmatter."""
        p = self._layout_no_fm(tmp_path)
        apply_annotation(p, {"description": "Minimal cover slide"})
        text = p.read_text()
        fm_text = text.split("---")[1]
        fm = yaml.safe_load(fm_text)
        assert fm["description"] == "Minimal cover slide"

    def test_read_back_identical(self, tmp_path):
        """Written annotation round-trips exactly through YAML."""
        p = self._layout_no_fm(tmp_path)
        apply_annotation(p, {
            "description": "Product intro with photo right",
            "when_to_use": "Opening slides with a hero image.",
        })
        text = p.read_text()
        fm_text = text.split("---")[1]
        fm = yaml.safe_load(fm_text)
        assert fm["description"] == "Product intro with photo right"
        assert fm["when_to_use"] == "Opening slides with a hero image."

    def test_preserves_mechanical_fields(self, tmp_path):
        """Existing mechanical fields (role, slots, etc.) are not touched."""
        fm = {
            "role": "title-primary",
            "ideal_count": [1, 2],
            "data_band": "none",
            "description": "",
        }
        p = self._layout_with_fm(tmp_path, fm)
        apply_annotation(p, {"description": "Bold cover"})
        updated = yaml.safe_load(p.read_text().split("---")[1])
        assert updated["role"] == "title-primary"
        assert updated["ideal_count"] == [1, 2]
        assert updated["data_band"] == "none"
        assert updated["description"] == "Bold cover"

    def test_only_writes_supplied_keys(self, tmp_path):
        """Unspecified annotation keys are not changed or zeroed."""
        fm = {
            "role": "content-columns",
            "description": "Already filled in",
            "when_to_use": "Existing guidance",
            "chrome_subject": "",
        }
        p = self._layout_with_fm(tmp_path, fm)
        # Supply only chrome_subject; description + when_to_use must survive.
        apply_annotation(p, {"chrome_subject": "City skyline illustration"})
        updated = yaml.safe_load(p.read_text().split("---")[1])
        assert updated["description"] == "Already filled in"
        assert updated["when_to_use"] == "Existing guidance"
        assert updated["chrome_subject"] == "City skyline illustration"

    def test_unrecognised_keys_ignored(self, tmp_path):
        """Keys not in the recognised annotation set are silently ignored."""
        p = self._layout_no_fm(tmp_path)
        apply_annotation(p, {"description": "ok", "bogus_key": "should not appear"})
        fm = yaml.safe_load(p.read_text().split("---")[1])
        assert "bogus_key" not in fm

    def test_preserves_slot_warnings(self, tmp_path):
        """slot_warnings block survives a rewrite (big lossy YAML)."""
        fm = {
            "role": "content-columns",
            "description": "",
            "slot_warnings": {"text_1": ["NARROW_BOX: fits ~3 chars"]},
        }
        p = self._layout_with_fm(tmp_path, fm)
        apply_annotation(p, {"description": "Narrow box slide"})
        updated = yaml.safe_load(p.read_text().split("---")[1])
        assert updated["slot_warnings"] == {"text_1": ["NARROW_BOX: fits ~3 chars"]}

    def test_preserves_chrome_bboxes(self, tmp_path):
        """chrome_bboxes list survives a rewrite."""
        bboxes = [[0, 0, 960, 540], [100, 200, 300, 150]]
        fm = {"role": "content-columns", "chrome_bboxes": bboxes}
        p = self._layout_with_fm(tmp_path, fm)
        apply_annotation(p, {"description": "With chrome"})
        updated = yaml.safe_load(p.read_text().split("---")[1])
        assert updated["chrome_bboxes"] == bboxes

    def test_preserves_element_tree(self, tmp_path):
        """element_tree list survives a rewrite."""
        tree = [
            "text text_1 role=title @100,100 800x120 44pt",
            "image image class=replace @1000,100 800x700",
        ]
        fm = {"role": "content-columns", "element_tree": tree}
        p = self._layout_with_fm(tmp_path, fm)
        apply_annotation(p, {"when_to_use": "Intro with photo"})
        updated = yaml.safe_load(p.read_text().split("---")[1])
        assert updated["element_tree"] == tree

    def test_body_preserved_exactly(self, tmp_path):
        """The DSL body after the fence is not altered."""
        body = "canvas 1920x1080\ntext 0,0 \"hello\"\n"
        fm = {"role": "content-columns"}
        p = self._layout_with_fm(tmp_path, fm, body=body)
        apply_annotation(p, {"description": "test"})
        text = p.read_text()
        # Body starts after the closing ---
        _, _, after = text.partition("---\n")
        _, _, actual_body = after.partition("---\n")
        assert actual_body == body

    def test_write_primary_message(self, tmp_path):
        """primary_message (new optional field) is written and read back."""
        p = self._layout_no_fm(tmp_path)
        apply_annotation(p, {"primary_message": "Streamline your workflow."})
        fm = yaml.safe_load(p.read_text().split("---")[1])
        assert fm["primary_message"] == "Streamline your workflow."

    def test_layout_not_found_raises(self, tmp_path):
        """apply_annotation raises OSError when the layout file doesn't exist."""
        p = tmp_path / "nonexistent.slide.dsl"
        with pytest.raises(OSError):
            apply_annotation(p, {"description": "x"})


# ---------------------------------------------------------------------------
# CLI subcommands: end-to-end
# ---------------------------------------------------------------------------

class TestCLIDescribeLayouts:
    def test_json_output(self, tmp_path, capsys):
        """describe-layouts prints a valid JSON array to stdout."""
        pack = _make_pack(tmp_path, frontmatter={"role": "content-columns"})
        rc = main(["brand", "describe-layouts", "--brand-pack", str(pack)])
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["stem"] == "acme-slide"
        assert "slot_inventory" in data[0]

    def test_yaml_output(self, tmp_path, capsys):
        """describe-layouts --format yaml prints valid YAML."""
        pack = _make_pack(tmp_path)
        rc = main(["brand", "describe-layouts", "--brand-pack", str(pack),
                   "--format", "yaml"])
        assert rc == 0
        out = capsys.readouterr().out
        data = yaml.safe_load(out)
        assert isinstance(data, list)
        assert data[0]["stem"] == "acme-slide"

    def test_missing_layouts_dir_exits_nonzero(self, tmp_path, capsys):
        """describe-layouts returns non-zero for a pack without layouts/."""
        empty = tmp_path / "empty-pack"
        empty.mkdir()
        rc = main(["brand", "describe-layouts", "--brand-pack", str(empty)])
        assert rc != 0

    def test_slot_inventory_in_output(self, tmp_path, capsys):
        """JSON output includes correct slot_inventory counts."""
        pack = _make_pack(tmp_path)
        main(["brand", "describe-layouts", "--brand-pack", str(pack)])
        out = capsys.readouterr().out
        data = json.loads(out)
        inv = data[0]["slot_inventory"]
        assert inv["text_slots"] == 3
        assert inv["image_slots"] == 1


class TestCLIAnnotateLayout:
    def test_writes_description(self, tmp_path, capsys):
        """annotate-layout writes --description into the layout's frontmatter."""
        pack = _make_pack(tmp_path, frontmatter={"role": "content-columns"})
        rc = main([
            "brand", "annotate-layout",
            "--brand-pack", str(pack),
            "--layout", "acme-slide",
            "--description", "Synthetic product intro",
        ])
        assert rc == 0
        dsl = (pack / "layouts" / "acme-slide.slide.dsl").read_text()
        fm = yaml.safe_load(dsl.split("---")[1])
        assert fm["description"] == "Synthetic product intro"

    def test_writes_all_fields(self, tmp_path, capsys):
        """annotate-layout writes all five supported fields."""
        pack = _make_pack(tmp_path, frontmatter={"role": "content-columns"})
        rc = main([
            "brand", "annotate-layout",
            "--brand-pack", str(pack),
            "--layout", "acme-slide",
            "--description", "A slide",
            "--when-to-use", "Use it often",
            "--when-not-to-use", "Not for data",
            "--chrome-subject", "Abstract cityscape",
            "--primary-message", "Scale fast.",
        ])
        assert rc == 0
        dsl = (pack / "layouts" / "acme-slide.slide.dsl").read_text()
        fm = yaml.safe_load(dsl.split("---")[1])
        assert fm["description"] == "A slide"
        assert fm["when_to_use"] == "Use it often"
        assert fm["when_not_to_use"] == "Not for data"
        assert fm["chrome_subject"] == "Abstract cityscape"
        assert fm["primary_message"] == "Scale fast."

    def test_missing_layout_returns_nonzero(self, tmp_path, capsys):
        """annotate-layout returns exit code 1 when the layout stem doesn't exist."""
        pack = _make_pack(tmp_path)
        rc = main([
            "brand", "annotate-layout",
            "--brand-pack", str(pack),
            "--layout", "nonexistent-layout",
            "--description", "x",
        ])
        assert rc == 1
        err = capsys.readouterr().err
        assert "not found" in err

    def test_no_fields_supplied_returns_nonzero(self, tmp_path, capsys):
        """annotate-layout without any annotation flags returns exit code 1."""
        pack = _make_pack(tmp_path)
        rc = main([
            "brand", "annotate-layout",
            "--brand-pack", str(pack),
            "--layout", "acme-slide",
        ])
        assert rc == 1

    def test_partial_update_preserves_others(self, tmp_path):
        """Supplying one field leaves other annotation fields untouched."""
        fm = {
            "role": "content-columns",
            "description": "Pre-filled description",
            "when_to_use": "Pre-filled guidance",
        }
        pack = _make_pack(tmp_path, frontmatter=fm)
        main([
            "brand", "annotate-layout",
            "--brand-pack", str(pack),
            "--layout", "acme-slide",
            "--chrome-subject", "Mountains at dusk",
        ])
        dsl = (pack / "layouts" / "acme-slide.slide.dsl").read_text()
        updated = yaml.safe_load(dsl.split("---")[1])
        assert updated["description"] == "Pre-filled description"
        assert updated["when_to_use"] == "Pre-filled guidance"
        assert updated["chrome_subject"] == "Mountains at dusk"

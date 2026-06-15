"""Catalog parsing: layouts.yaml + snippets.yaml + master.pptx.ref resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from feinschmiede.master_template import load_catalog


def _write(brand_pack: Path, layouts_yaml: str, snippets_yaml: str | None = None) -> None:
    brand_pack.mkdir(parents=True, exist_ok=True)
    (brand_pack / "layouts.yaml").write_text(layouts_yaml)
    if snippets_yaml is not None:
        (brand_pack / "snippets.yaml").write_text(snippets_yaml)


def test_resolves_master_ref(tmp_path):
    master = tmp_path / "real-master.pptx"
    master.write_bytes(b"")
    pack = tmp_path / "pack"
    _write(
        pack,
        "layouts: []\n",
    )
    (pack / "master.pptx.ref").write_text(str(master))

    cat = load_catalog(pack)
    assert cat.master_pptx == master
    assert cat.source_deck == master


def test_source_deck_ref_overrides_master_for_cloning(tmp_path):
    master = tmp_path / "master.pptx"
    master.write_bytes(b"")
    source = tmp_path / "richer-source.pptx"
    source.write_bytes(b"")
    pack = tmp_path / "pack"
    _write(pack, "layouts: []\n")
    (pack / "master.pptx.ref").write_text(str(master))
    (pack / "source_deck.pptx.ref").write_text(str(source))

    cat = load_catalog(pack)
    assert cat.master_pptx == master
    assert cat.source_deck == source


def test_layout_entry_parses_placeholders_and_hero(tmp_path):
    pack = tmp_path / "pack"
    (pack / "master.pptx").parent.mkdir(parents=True, exist_ok=True)
    (pack).mkdir(parents=True, exist_ok=True)
    (pack / "master.pptx").write_bytes(b"")
    _write(
        pack,
        """
layouts:
  - name: "Title + Graphical Content + Text"
    role: content
    placeholders:
      - idx: 0
        type: TITLE
        role: headline
        char_budget: 80
      - idx: 1
        type: OBJECT
        role: body_or_chart
        char_budget: 600
        accepts: [text, chart, picture]
  - name: "Chapter horizontal"
    role: chapter
    placeholders:
      - idx: 15
        type: BODY
        role: chapter_title
        char_budget: 60
    hero_image:
      bbox_emu: [0, 0, 10969625, 2055939]
      required: true
""",
    )
    cat = load_catalog(pack)
    layout = cat.layouts["Title + Graphical Content + Text"]
    assert layout.role == "content"
    assert layout.placeholders[1].accepts == ("text", "chart", "picture")
    assert layout.placeholders[1].char_budget == 600

    chapter = cat.layouts["Chapter horizontal"]
    assert chapter.hero_image_bbox_emu == (0, 0, 10969625, 2055939)


def test_snippets_optional(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "master.pptx").write_bytes(b"")
    _write(pack, "layouts: []\n")
    cat = load_catalog(pack)
    assert cat.snippets == {}


def test_snippets_parse(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "master.pptx").write_bytes(b"")
    _write(
        pack,
        "layouts: []\n",
        """
snippets:
  - id: timeline-months
    source_idx: 17
    intent: 12-month roadmap
    anchors:
      title: "Timeline 4"
  - id: funnel-6-stages
    source_idx: 27
""",
    )
    cat = load_catalog(pack)
    assert cat.snippets["timeline-months"].source_idx == 17
    assert cat.snippets["timeline-months"].anchors == {"title": "Timeline 4"}
    assert cat.snippets["funnel-6-stages"].intent is None


def test_missing_master_raises(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    _write(pack, "layouts: []\n")
    with pytest.raises(FileNotFoundError):
        load_catalog(pack)

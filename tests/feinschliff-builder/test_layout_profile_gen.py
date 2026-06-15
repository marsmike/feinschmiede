"""Layout-picker frontmatter generation for decompiled brand-pack layouts.

Decompiled layouts carry no `---` frontmatter, so the /deck picker
(`feinschliff.layout_profile.build_profile_table(strict=False)`) silently
drops them. `layout_profile_gen` classifies a slotified layout from its DSL
text alone and emits a fence that `parse_profile` accepts — these tests pin
the classification heuristics, slot-role assignment, fence idempotency, and
the deck-map reduction.
"""
from __future__ import annotations

import base64
from pathlib import Path

import pytest
import yaml

from feinschliff.dsl.parser import parse_lines, split_frontmatter
from feinschliff.layout_profile import parse_profile
from feinschliff_builder.decompile.layout_profile_gen import (
    apply_profile,
    classify_layout,
    derive_deck_map,
    main as gen_main,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "feinschliff-builder"
REAL_COVER = (REPO_ROOT.parent / "feinschliff-extra" / "brands" / "scientific"
              / "layouts" / "cover.slide.dsl")

HEADER = "# auto-derived from PPTX+SVG hybrid — review before use\ncanvas 1920x1080\ntheme test\n\n"


def slot(n: int, default: str, *, x=152, y=260, style="title-l", pt=60,
         maxw=1600, maxh=200) -> str:
    # Mirrors real slotified output: the inner quotes are backslash-escaped
    # in the FILE, e.g.  "{{ text_1 | default(\"Annual Review\") }}"
    return (f'text {x},{y} style:{style} color:black size:{pt}pt '
            f'maxwidth:{maxw} maxheight:{maxh} '
            f'"{{{{ text_{n} | default(\\"{default}\\") }}}}"\n')


def footer_slots(start: int) -> str:
    return (
        slot(start, "Annual Review", x=1307, y=991, style="body-sm", pt=12,
             maxw=231, maxh=29)
        + slot(start + 1, "7", x=1810, y=991, style="body-sm", pt=12,
               maxw=100, maxh=29)
    )


def native(xml: str, name: str = "shape1") -> str:
    b64 = base64.b64encode(xml.encode("utf-8")).decode("ascii")
    return f'native {name} b64:"{b64}"\n'


CHART_XML = ('<p:graphicFrame xmlns:p="p"><a:graphic>'
             '<c:chart r:id="rId2"/></a:graphic></p:graphicFrame>')
TABLE_XML = ('<p:graphicFrame xmlns:p="p"><a:graphic>'
             '<a:tbl><a:tr/></a:tbl></a:graphic></p:graphicFrame>')
SMARTART_XML = ('<p:graphicFrame xmlns:p="p"><a:graphic>'
                '<dgm:relIds r:dm="rId1"/></a:graphic></p:graphicFrame>')
ILLUSTRATION_XML = '<p:sp xmlns:p="p"><p:spPr><a:custGeom/></p:spPr></p:sp>'

FULL_BLEED_PICTURE = ('picture 0,0 1920x1080 '
                      'path:"{{ image | default(\\"decompile/x/image.png\\") }}" '
                      'cover:true\n')


def illu_xml(x=0, y=0, cx=6096000, cy=3429000) -> str:
    """Decorative custGeom shape with root xfrm geometry in EMU. The default
    6096000x3429000 ext is exactly a quarter of the standard 12192000x6858000
    slide — comfortably above the 20 % area gate."""
    return (f'<p:sp xmlns:p="p" xmlns:a="a"><p:spPr><a:xfrm>'
            f'<a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/>'
            f'</a:xfrm><a:custGeom/></p:spPr></p:sp>')


def picture(name: str, w: int, h: int, x=100, y=100) -> str:
    return (f'picture {x},{y} {w}x{h} '
            f'path:"{{{{ {name} | default(\\"decompile/x/{name}.png\\") }}}}"\n')


def prose_slots(start: int, n: int) -> str:
    out = ""
    for i in range(start, start + n):
        out += slot(i, "Some longer prose paragraph here", x=100 + 300 * i,
                    y=600, style="body", pt=18, maxw=280, maxh=300)
    return out


def classify(dsl: str, *, name="some-layout", index=5, total=13, **kw) -> dict:
    return classify_layout(dsl, layout_name=name, slide_index=index,
                           total_slides=total, **kw)


# --- role heuristics ---------------------------------------------------------

def test_slide_one_is_title_primary_cover():
    dsl = HEADER + slot(1, "Annual Review") + slot(2, "Contoso Team", y=420, pt=24)
    p = classify(dsl, name="cover", index=1)
    assert p["role"] == "title-primary"
    assert p["family"] == "framing"
    assert p["variety_exempt"] is True
    assert p["ideal_count"] == [1, 2]


def test_agenda_by_title_default():
    dsl = (HEADER + slot(1, "Agenda", pt=40)
           + slot(2, "01. Intro\\n02. Results", y=500, style="body", pt=20, maxh=400)
           + footer_slots(3))
    p = classify(dsl, name="toc", index=2)
    assert p["role"] == "agenda"
    assert p["variety_exempt"] is True


def test_use_case_layout_names_classify_roles():
    """Master-derived packs name layouts by use case (title-2, chapter-1,
    end) — the name is authoritative even when slide position isn't
    (title-2 sits at index 2, end may not be the last slide)."""
    body = HEADER + slot(1, "Title", pt=30)
    assert classify(body, name="title-2", index=2, total=17)["role"] == "title-primary"
    assert classify(body, name="chapter-1", index=4, total=17)["role"] == "chapter-opener"
    assert classify(body, name="chapter-1", index=4, total=17)["family"] == "framing"
    assert classify(body, name="end", index=16, total=17)["role"] == "closer"
    # No false positives: 'subtitle-band' / 'legend' must not match title/end.
    assert classify(body, name="subtitle-band", index=5, total=17)["role"] != "title-primary"
    assert classify(body, name="legend", index=5, total=17)["role"] != "closer"


def test_reference_sheet_layout_names_classify_reference():
    """Template reference sheets (howto, design samples, small-elements)
    must not fall into position-based roles — index==total would make a
    'small-elements' sheet the deck closer."""
    body = HEADER + slot(1, "Small Elements", pt=20)
    p = classify(body, name="small-elements", index=17, total=17)
    assert p["role"] == "reference"
    assert p["family"] == "organizational"


def test_tiny_native_pic_is_mark_not_illustration_chrome():
    """A flattened logo mark (small native picture on every slide) must not
    trip the decorative-divider rule or the area gate — it is brand mark,
    not illustration chrome."""
    logo = ('<p:pic xmlns:p="p" xmlns:a="a"><p:spPr><a:xfrm>'
            '<a:off x="9849600" y="5760000"/><a:ext cx="684000" cy="207973"/>'
            '</a:xfrm></p:spPr></p:pic>')
    dsl = HEADER + native(logo, "logo") + slot(1, "Some title", pt=30)
    p = classify(dsl, name="some-layout")
    assert p["role"] != "chapter-opener"
    assert "chrome_subject" not in p
    assert "mark" in p["chrome_note"]


def test_agenda_by_layout_name():
    dsl = HEADER + slot(1, "Was uns erwartet", pt=40)
    assert classify(dsl, name="inhalt", index=2)["role"] == "agenda"


def test_quote_by_lone_quote_mark_default():
    dsl = (HEADER + slot(1, "“", pt=200, y=154)
           + slot(2, "Contoso was great to work with.", y=400, style="sub", pt=28)
           + footer_slots(3))
    p = classify(dsl, name="quote", index=7)
    assert p["role"] == "quote"
    assert p["family"] == "voice"
    assert p["ideal_count"] == [1, 2]


def test_closer_by_last_slide_and_by_title():
    dsl = HEADER + slot(1, "THANK YOU", pt=54, y=498) \
        + slot(2, "hello@adatum.com", y=952, style="body", pt=24)
    by_index = classify(dsl, name="end", index=13, total=13)
    assert by_index["role"] == "closer"
    assert by_index["variety_exempt"] is True
    by_title = classify(dsl, name="end", index=9, total=13)
    assert by_title["role"] == "closer"


def test_native_chart_is_data_comparison():
    dsl = HEADER + native(CHART_XML, "graphic1") + slot(1, "Growth by sector", pt=40)
    p = classify(dsl, name="growth-chart")
    assert p["role"] == "data-comparison"
    assert p["data_band"] == "chart"
    assert p["comparison"] is True
    assert p["family"] == "comparison"


def test_native_table_is_reference():
    dsl = HEADER + native(TABLE_XML, "graphic1") + slot(1, "Growth by sector", pt=40)
    p = classify(dsl, name="growth-table")
    assert p["role"] == "reference"
    assert p["data_band"] == "table"
    assert p["comparison"] is False


def test_native_smartart_is_concept_diagram():
    dsl = HEADER + native(SMARTART_XML, "graphic1") + slot(1, "Our process", pt=40)
    p = classify(dsl, name="growth-strategy")
    assert p["role"] == "concept-diagram"
    assert p["family"] == "process"
    assert p["data_band"] == "none"


def test_native_illustration_divider_is_chapter_opener():
    dsl = (HEADER + native(ILLUSTRATION_XML)
           + slot(1, "The Power of Communication", pt=36)
           + footer_slots(2))  # footer/page-number don't count as visible text
    p = classify(dsl, name="section-intro", index=4)
    assert p["role"] == "chapter-opener"
    assert p["fixed_chrome"] is True
    assert p["when_not_to_use"] == [
        "role=content-columns", "role=data-quantity", "role=data-comparison",
    ]
    assert p["ideal_count"] == [1, 2]
    assert "illustration" in p["chrome_note"]


def test_undecodable_native_defaults_to_illustration():
    dsl = (HEADER + 'native shape1 xml_file:"native/missing.xml"\n'
           + slot(1, "Divider", pt=36))
    p = classify(dsl, name="divider")  # no asset_root → cannot decode
    assert p["role"] == "chapter-opener"


BAKED_TEXT_ILLU_XML = (
    '<p:sp xmlns:p="p" xmlns:a="a"><p:spPr><a:custGeom/></p:spPr>'
    '<p:txBody><a:p><a:r><a:t>STEP 1</a:t></a:r></a:p></p:txBody></p:sp>'
)


def test_illustration_with_baked_text_sets_chrome_text():
    """Illustration chrome that carries its own <a:t> labels (e.g. a chevron
    process graphic with baked STEP texts) must be flagged — binding text
    slots over it overprints the baked labels (worldcup v4 slide-29)."""
    dsl = (HEADER + native(BAKED_TEXT_ILLU_XML)
           + prose_slots(1, 3) + footer_slots(4))
    p = classify(dsl)
    assert p["chrome_text"] is True
    assert "baked text" in p["chrome_note"]


def test_illustration_without_text_has_no_chrome_text():
    dsl = (HEADER + native(ILLUSTRATION_XML)
           + prose_slots(1, 3) + footer_slots(4))
    p = classify(dsl)
    assert "chrome_text" not in p


def test_graphic_frame_with_baked_text_sets_chrome_text():
    """<p:graphicFrame> natives (charts, SmartArt, tables) carrying literal
    <a:t> placeholder text must flag chrome_text — binding content slots over
    them overprints the baked labels (org-chart 'Placeholder', SmartArt step
    texts, table stub headings)."""
    xml = ('<p:graphicFrame xmlns:p="p"><a:graphic><c:chart r:id="rId2"/>'
           '<a:t>Placeholder</a:t></a:graphic></p:graphicFrame>')
    dsl = HEADER + native(xml, "graphic1") + slot(1, "Growth by sector", pt=40)
    p = classify(dsl)
    assert p["chrome_text"] is True
    assert "baked text" in p["chrome_note"]


def test_graphic_frame_with_template_runs_only_does_not_set_chrome_text():
    """A <p:graphicFrame> native whose <a:t> runs have already been rewritten
    to {{ text_N | default(…) }} template expressions by the slotify pass is
    bindable — those are not baked labels, so chrome_text must NOT fire."""
    # The native-text slotify pass rewrites baked runs to Jinja templates;
    # _has_baked_text explicitly skips runs that contain "{{".
    xml = ('<p:graphicFrame xmlns:p="p"><a:graphic>'
           '<a:t>{{ text_1 | default("Sample heading") }}</a:t>'
           '</a:graphic></p:graphicFrame>')
    dsl = HEADER + native(xml, "graphic1") + slot(1, "Growth by sector", pt=40)
    p = classify(dsl)
    assert "chrome_text" not in p


def test_illustration_with_baked_text_regression_still_sets_chrome_text():
    """Regression guard: extending the gate to graphic* must not break the
    existing illustration path — illustration chrome with literal <a:t> labels
    must still flag chrome_text."""
    dsl = (HEADER + native(BAKED_TEXT_ILLU_XML)
           + prose_slots(1, 3) + footer_slots(4))
    p = classify(dsl)
    assert p["chrome_text"] is True


def test_mark_sized_native_with_baked_text_still_sets_chrome_text():
    """Mark demotion must not silence the baked-text gate: a small chevron
    native that draws its own 'Step 1' still makes text slots un-rebindable."""
    chevron = ('<p:sp xmlns:p="p" xmlns:a="a"><p:spPr><a:xfrm>'
               '<a:off x="100" y="100"/><a:ext cx="600000" cy="200000"/>'
               '</a:xfrm><a:custGeom/></p:spPr>'
               '<p:txBody><a:p><a:r><a:t>Step 1</a:t></a:r></a:p></p:txBody></p:sp>')
    dsl = HEADER + native(chevron) + prose_slots(1, 3) + footer_slots(4)
    p = classify(dsl)
    assert p["chrome_text"] is True
    assert p["role"] != "chapter-opener"  # mark demotion still applies


def test_whitespace_only_baked_text_is_ignored():
    xml = ('<p:sp xmlns:p="p" xmlns:a="a"><p:spPr><a:custGeom/></p:spPr>'
           '<p:txBody><a:p><a:r><a:t> </a:t></a:r></a:p></p:txBody></p:sp>')
    dsl = (HEADER + native(xml) + prose_slots(1, 3) + footer_slots(4))
    p = classify(dsl)
    assert "chrome_text" not in p


def test_full_bleed_image_is_title_with_visual():
    dsl = HEADER + FULL_BLEED_PICTURE + slot(1, "Last year", pt=54)
    p = classify(dsl, name="last-year")
    assert p["role"] == "title-with-visual"
    assert p["family"] == "image-driven"
    assert "image" in p["image_queries"]


def test_numeric_short_body_slots_are_data_quantity():
    dsl = HEADER + slot(1, "Key figures", pt=40)
    for i, val in enumerate(("45%", "+30", "€2,4", "1.2"), start=2):
        dsl += slot(i, val, x=100 + 400 * i, y=600, style="body", pt=40,
                    maxw=380, maxh=200)
    p = classify(dsl, name="metrics")
    assert p["role"] == "data-quantity"
    assert p["data_band"] == "kpi"
    assert p["ideal_count"] == [4, 4]


def test_many_body_slots_fall_back_to_content_columns():
    dsl = HEADER + slot(1, "Summary", pt=40)
    for i in range(2, 5):
        dsl += slot(i, "Some longer prose paragraph here", x=100 + 500 * i,
                    y=500, style="body", pt=18, maxw=480, maxh=400)
    p = classify(dsl, name="summary")
    assert p["role"] == "content-columns"
    assert p["family"] == "organizational"
    assert p["ideal_count"] == [3, 3]


# --- slot roles ---------------------------------------------------------------

def test_slot_roles_and_char_capacity():
    dsl = (HEADER + slot(1, "Goals for Q1", pt=60, y=260)
           + slot(2, "Business priorities", y=600, style="body", pt=18,
                  maxw=800, maxh=300)
           + footer_slots(3))
    slots = classify(dsl, name="goals")["slots"]
    assert slots["text_1"]["role"] == "title"
    assert slots["text_2"]["role"] == "body"
    assert slots["text_3"]["role"] == "footer"
    assert slots["text_4"]["role"] == "page-number"
    assert all(s["chars"] > 0 for s in slots.values())
    assert slots["text_1"]["default"] == "Goals for Q1"


# --- frontmatter emission -------------------------------------------------------

def test_apply_profile_is_idempotent_and_keeps_body():
    dsl = HEADER + slot(1, "Annual Review")
    p = classify(dsl, name="cover", index=1)
    once = apply_profile(dsl, p)
    twice = apply_profile(once, p)
    assert once == twice
    assert once.startswith("---\n")
    assert once.endswith(dsl)  # body stays byte-identical after the fence


def test_generated_frontmatter_passes_parse_profile():
    dsl = (HEADER + native(CHART_XML, "graphic1") + FULL_BLEED_PICTURE
           + slot(1, "Growth", pt=40) + footer_slots(2))
    p = classify(dsl, name="growth-chart")
    fm, _body = split_frontmatter(apply_profile(dsl, p))
    assert fm is not None
    parsed = parse_profile(fm, source="growth-chart")
    assert parsed["role"] == "data-comparison"
    assert parsed["data"] == "chart"
    assert parsed["comp"] is True
    assert parsed["ideal_count"] == (1, 1)


# --- area-based fixed-chrome gate -------------------------------------------------

def test_area_gate_fires_for_big_illustration_with_many_text_slots():
    # The motivating failure: a garden-scene illustration beside a text
    # column classifies as content-columns (>2 text slots) and the picker
    # pairs soccer content with a washing-machine illustration. The 25 %
    # illustration share must gate it while KEEPING the role.
    dsl = (HEADER + native(illu_xml(), "garden")
           + slot(1, "Modern garden solutions", pt=40) + prose_slots(2, 4))
    p = classify(dsl, name="garden-columns")
    assert p["role"] == "content-columns"  # classification unchanged …
    assert p["fixed_chrome"] is True       # … but the layout is gated
    assert p["when_not_to_use"] == [
        "role=content-columns", "role=data-quantity", "role=data-comparison",
        "role=data-timeline", "role=concept-diagram",
    ]


def test_area_gate_ignores_small_illustration_and_non_illustration_kinds():
    small = native(illu_xml(cx=2438400, cy=2743200), "corner")  # 8 % area
    big_chart = native(  # chart kind never counts toward illustration area
        '<p:graphicFrame xmlns:p="p"><a:xfrm><a:off x="0" y="0"/>'
        '<a:ext cx="12192000" cy="6858000"/></a:xfrm>'
        '<a:graphic><c:chart r:id="rId2"/></a:graphic></p:graphicFrame>',
        "graphic1")
    dsl = (HEADER + small + big_chart
           + slot(1, "Growth", pt=40) + prose_slots(2, 4))
    p = classify(dsl, name="growth")
    assert p["role"] == "data-comparison"
    assert "fixed_chrome" not in p
    assert "when_not_to_use" not in p


def test_area_gate_decode_failure_falls_back_to_slot_count_rule():
    dsl = (HEADER + 'native shape1 xml_file:"native/missing.xml"\n'
           + slot(1, "Headline", pt=40) + prose_slots(2, 4))
    p = classify(dsl, name="busy")  # no asset_root → cannot decode geometry
    assert p["role"] == "content-columns"
    assert "fixed_chrome" not in p  # old rule: >2 visible slots → not gated


# --- semantic annotation fields ---------------------------------------------------

def test_semantic_annotation_fields_default_empty():
    p = classify(HEADER + slot(1, "Plain"), name="plain")
    assert p["description"] == ""
    assert "chrome_subject" not in p  # no illustration chrome
    p2 = classify(HEADER + native(ILLUSTRATION_XML) + slot(1, "Divider", pt=36),
                  name="divider")
    assert p2["description"] == ""
    assert p2["chrome_subject"] == ""
    p3 = classify(HEADER + native(CHART_XML, "graphic1") + slot(1, "Chart", pt=40),
                  name="chart")
    assert "chrome_subject" not in p3  # chart chrome is not an illustration


def test_image_slot_classes():
    dsl = (HEADER + FULL_BLEED_PICTURE              # share 1.0 → replace
           + picture("image2", 180, 24, x=1700, y=40)   # tiny logo → keep
           + picture("image3", 500, 400)                # mid photo → replace
           + picture("image4", 1800, 160, y=40)         # wide strip → keep
           + slot(1, "Team intro", pt=40))
    slots = classify(dsl, name="team")["slots"]
    assert slots["image"] == {"role": "image", "class": "replace"}
    assert slots["image2"]["class"] == "keep"
    assert slots["image3"]["class"] == "replace"
    assert slots["image4"]["class"] == "keep"  # share 0.14, aspect 11 > 6


# --- annotation preservation across re-runs ---------------------------------------

ANNOTATED_DSL = (HEADER + native(illu_xml(), "deko") + FULL_BLEED_PICTURE
                 + slot(1, "Garden stories", pt=40) + prose_slots(2, 4))


def _annotate_fence(fenced: str, **fields) -> str:
    """Simulate a vision-annotation pass: edit fields straight in the fence."""
    fm, _ = split_frontmatter(fenced)
    data = yaml.safe_load(fm)
    for key, val in fields.items():
        data[key] = val
    body = fenced.split("---\n", 2)[2]
    return "---\n" + yaml.safe_dump(data, sort_keys=False) + "---\n" + body


def test_reapply_preserves_annotations_and_regenerates_mechanics():
    p1 = classify(ANNOTATED_DSL, name="garden")
    once = apply_profile(ANNOTATED_DSL, p1)
    fm, _ = split_frontmatter(once)
    ann = yaml.safe_load(fm)
    ann["description"] = "Text column beside a garden scene"
    ann["chrome_subject"] = "terrace garden with potting bench"
    ann["slots"]["image"]["class"] = "keep"
    ann["role"] = "bogus-role"   # mechanical tampering — must regenerate
    ann["ideal_count"] = [9, 9]
    annotated = _annotate_fence(once, **ann)

    p2 = classify(annotated, name="garden")
    final = apply_profile(annotated, p2)
    out = yaml.safe_load(split_frontmatter(final)[0])
    # Annotations survive …
    assert out["description"] == "Text column beside a garden scene"
    assert out["chrome_subject"] == "terrace garden with potting bench"
    assert out["slots"]["image"]["class"] == "keep"
    # … mechanical fields regenerate …
    assert out["role"] == "content-columns"
    assert out["ideal_count"] == [4, 4]
    assert out["slots"]["text_1"]["role"] == "title"
    # … and the DSL body stays byte-identical.
    assert final.endswith(ANNOTATED_DSL)


def test_apply_profile_ignores_empty_annotations_in_old_fence():
    p = classify(ANNOTATED_DSL, name="garden")
    once = apply_profile(ANNOTATED_DSL, p)
    assert apply_profile(once, p) == once  # still idempotent with the merge


# --- element tree ------------------------------------------------------------------

def test_element_tree_records_reading_order_geometry_and_kinds():
    """Every slide element — native chrome, image slots, text slots — lands
    in `element_tree` as one compact line with role/class/kind + geometry,
    sorted into reading order (top→bottom, left→right). This is the
    structural 'what is where' a deck planner reads alongside description."""
    dsl = (HEADER + native(illu_xml(), "deko") + FULL_BLEED_PICTURE
           + slot(1, "Garden stories", pt=40) + prose_slots(2, 2))
    p = classify(dsl, name="garden")
    tree = p["element_tree"]
    assert len(tree) == 5  # 1 native + 1 image slot + 3 text slots
    assert "native illustration @0,0 960x540" in tree
    assert "image image class=replace @0,0 1920x1080" in tree
    title = "text text_1 role=title @152,260 1600x200 40pt"
    assert title in tree
    # reading order: the @0,0 background elements come before the title text
    assert tree.index(title) > tree.index("image image class=replace @0,0 1920x1080")


def test_element_tree_marks_baked_text_native():
    dsl = (HEADER + native(BAKED_TEXT_ILLU_XML)
           + prose_slots(1, 3) + footer_slots(4))
    p = classify(dsl)
    line = next(ln for ln in p["element_tree"] if ln.startswith("native"))
    assert "baked-text" in line


# --- when_to_use + curated family --------------------------------------------------

def test_when_to_use_annotation_slot_and_merge():
    """`when_to_use` is an annotation slot like description: emitted empty,
    non-empty values survive a generator re-run."""
    p = classify(HEADER + slot(1, "Plain"), name="plain")
    assert p["when_to_use"] == ""
    once = apply_profile(ANNOTATED_DSL, classify(ANNOTATED_DSL, name="garden"))
    annotated = _annotate_fence(
        once, when_to_use="Brand-moment divider for garden chapters")
    out = yaml.safe_load(split_frontmatter(
        apply_profile(annotated, classify(ANNOTATED_DSL, name="garden")))[0])
    assert out["when_to_use"] == "Brand-moment divider for garden chapters"


def test_curated_family_survives_rerun_only_with_marker():
    """A vision pass may overrule the heuristic slide-type (`family`) — but
    only an explicit `family_curated: true` survives regeneration; a bare
    hand-edit is mechanical tampering and reverts."""
    once = apply_profile(ANNOTATED_DSL, classify(ANNOTATED_DSL, name="garden"))
    tampered = _annotate_fence(once, family="process")
    out = yaml.safe_load(split_frontmatter(
        apply_profile(tampered, classify(ANNOTATED_DSL, name="garden")))[0])
    assert out["family"] == "organizational"
    assert "family_curated" not in out

    curated = _annotate_fence(once, family="process", family_curated=True)
    out2 = yaml.safe_load(split_frontmatter(
        apply_profile(curated, classify(ANNOTATED_DSL, name="garden")))[0])
    assert out2["family"] == "process"
    assert out2["family_curated"] is True


def test_annotate_cli_when_to_use_and_family(tmp_path):
    f = tmp_path / "garden.slide.dsl"
    f.write_text(apply_profile(ANNOTATED_DSL, classify(ANNOTATED_DSL, name="garden")),
                 encoding="utf-8")
    rc = gen_main(["annotate", str(f),
                   "--when-to-use", "Use for garden chapter intros",
                   "--family", "process"])
    assert rc == 0
    d = yaml.safe_load(split_frontmatter(f.read_text(encoding="utf-8"))[0])
    assert d["when_to_use"] == "Use for garden chapter intros"
    assert d["family"] == "process"
    assert d["family_curated"] is True
    # unknown family rejected, file untouched
    before = f.read_text(encoding="utf-8")
    assert gen_main(["annotate", str(f), "--family", "banana"]) == 2
    assert f.read_text(encoding="utf-8") == before


# --- annotate CLI ------------------------------------------------------------------

def test_annotate_cli_round_trip(tmp_path):
    f = tmp_path / "garden.slide.dsl"
    f.write_text(apply_profile(ANNOTATED_DSL, classify(ANNOTATED_DSL, name="garden")),
                 encoding="utf-8")
    rc = gen_main(["annotate", str(f),
                   "--description", "Garden scene with text column",
                   "--chrome-subject", "potting bench in a courtyard",
                   "--image-class", "image=keep"])
    assert rc == 0
    fenced = f.read_text(encoding="utf-8")
    d = yaml.safe_load(split_frontmatter(fenced)[0])
    assert d["description"] == "Garden scene with text column"
    assert d["chrome_subject"] == "potting bench in a courtyard"
    assert d["slots"]["image"]["class"] == "keep"
    assert fenced.endswith(ANNOTATED_DSL)  # body untouched
    # A later generator re-run keeps the CLI's annotations (merge semantics).
    refenced = apply_profile(fenced, classify(ANNOTATED_DSL, name="garden"))
    d2 = yaml.safe_load(split_frontmatter(refenced)[0])
    assert d2["description"] == "Garden scene with text column"
    assert d2["chrome_subject"] == "potting bench in a courtyard"
    assert d2["slots"]["image"]["class"] == "keep"


def test_annotate_cli_rejects_fenceless_file_and_bad_class(tmp_path, capsys):
    bare = tmp_path / "bare.slide.dsl"
    original = HEADER + slot(1, "X")
    bare.write_text(original, encoding="utf-8")
    assert gen_main(["annotate", str(bare), "--description", "x"]) == 2
    assert "frontmatter" in capsys.readouterr().err
    assert bare.read_text(encoding="utf-8") == original  # left untouched

    fenced = tmp_path / "fenced.slide.dsl"
    fenced.write_text(
        apply_profile(ANNOTATED_DSL, classify(ANNOTATED_DSL, name="garden")),
        encoding="utf-8")
    before = fenced.read_text(encoding="utf-8")
    assert gen_main(["annotate", str(fenced), "--image-class", "image=banana"]) == 2
    assert gen_main(["annotate", str(fenced), "--image-class", "nope=keep"]) == 2
    assert fenced.read_text(encoding="utf-8") == before


# --- deck map -------------------------------------------------------------------

def test_derive_deck_map_assigns_roles_in_slide_order():
    profiles = {
        "thanks": {"role": "closer", "slide_index": 13},
        "cover": {"role": "title-primary", "slide_index": 1},
        "toc": {"role": "agenda", "slide_index": 2},
        "divider-a": {"role": "chapter-opener", "slide_index": 3},
        "divider-b": {"role": "chapter-opener", "slide_index": 8},
        "voice": {"role": "quote", "slide_index": 7},
        "kpis": {"role": "data-quantity", "slide_index": 4},
        "columns": {"role": "content-columns", "slide_index": 5},
    }
    assert derive_deck_map(profiles) == {
        "cover": "cover",
        "agenda": "toc",
        "section": ["divider-a", "divider-b"],
        "quote": "voice",
        "closer": "thanks",
        "content": ["kpis", "columns"],
    }


def test_derive_deck_map_omits_missing_roles():
    profiles = {
        "cover": {"role": "title-primary", "slide_index": 1},
        "body": {"role": "content-columns", "slide_index": 2},
    }
    deck_map = derive_deck_map(profiles)
    assert deck_map == {"cover": "cover", "content": ["body"]}
    assert "agenda" not in deck_map and "quote" not in deck_map


# --- integration against a real decompiled layout ---------------------------------

@pytest.mark.skipif(not REAL_COVER.is_file(),
                    reason="feinschliff-extra scientific pack not present")
def test_real_scientific_cover_roundtrip(tmp_path):
    original = REAL_COVER.read_text(encoding="utf-8")
    # A previous generator run may already have fenced the file — strip so
    # the byte-identity assertion below targets the DSL body itself.
    orig_fm, _ = split_frontmatter(original)
    if orig_fm is not None:
        lines = original.splitlines(keepends=True)
        close = [i for i, ln in enumerate(lines) if ln.strip() == "---"][1]
        original = "".join(lines[close + 1:])
    target = tmp_path / "cover.slide.dsl"
    target.write_text(original, encoding="utf-8")

    profile = classify_layout(
        original, layout_name="cover", slide_index=1, total_slides=13,
        asset_root=REAL_COVER.parent.parent / "assets")
    assert profile["role"] == "title-primary"

    fenced = apply_profile(original, profile)
    target.write_text(fenced, encoding="utf-8")
    fm, body = split_frontmatter(fenced)
    assert fm is not None
    parse_profile(fm, source=str(target))
    # split_frontmatter blanks the fence region to keep parser line numbers
    # stable — modulo that padding, the body is the original text.
    assert body.lstrip("\n").rstrip("\n") == original.rstrip("\n")
    # And the fenced file still parses at compile_slide level.
    nodes, _diag = parse_lines(body)
    assert any(n.kind == "text" for n in nodes)

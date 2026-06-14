"""Pack-build box-sanity lint: statically impossible/narrow/overlapping slot
boxes become `slot_warnings` front-matter at decompile time — caught once
per pack, not once per deck. Geometry mirrors the World Cup incidents
(16pt label in a 27px box; two colliding chapter boxes) with NEUTRAL
synthetic content — never corporate-pack material."""
from pathlib import Path

from feinschliff_builder.decompile.layout_profile_gen import (
    apply_profile,
    classify_layout,
)

# 12in-deck pack tokens: px_per_pt = 1920*12700/10969625 ≈ 2.2229.
_TOKENS_12IN = """\
{
  "color": {"ink": {"$value": "#000000"}, "paper": {"$value": "#FFFFFF"}},
  "font-family": {"display": {"$value": ["DejaVu Sans"]},
                  "body": {"$value": ["DejaVu Sans"]}},
  "font-size": {"body": {"$value": "16px"}},
  "font-weight": {"regular": {"$value": 400}},
  "slide": {"width_emu": {"$value": "10969625"},
            "height_emu": {"$value": "6170613"}}
}
"""


def _brand(tmp_path: Path) -> Path:
    brand = tmp_path / "brands" / "synthpack"
    (brand / "assets").mkdir(parents=True)
    (brand / "tokens.json").write_text(_TOKENS_12IN, encoding="utf-8")
    return brand


def _classify(dsl: str, brand: Path) -> dict:
    return classify_layout(
        dsl, layout_name="synth", slide_index=1, total_slides=10,
        asset_root=brand / "assets", brand_dir=brand,
    )


def test_impossible_box_flagged(tmp_path):
    """16pt on a 12in deck is ~35.6px; one 1.2-line is ~43px — a 27px-tall
    box can never show a line (the slide-30 incident class)."""
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,500 size:16pt maxwidth:300 maxheight:27 '
           '"{{ text_1 | default(\\"Label\\") }}"\n')
    profile = _classify(dsl, brand)
    warnings = profile.get("slot_warnings", {})
    assert any(w.startswith("IMPOSSIBLE_BOX") for w in warnings.get("text_1", [])), warnings


def test_narrow_box_flagged(tmp_path):
    """< 8 chars per line at the resolved size → NARROW_BOX."""
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,500 size:16pt maxwidth:90 maxheight:200 '
           '"{{ text_1 | default(\\"Label\\") }}"\n')
    profile = _classify(dsl, brand)
    assert any(w.startswith("NARROW_BOX")
               for w in profile.get("slot_warnings", {}).get("text_1", []))


def test_overlapping_boxes_flagged_pairwise(tmp_path):
    """Two slot boxes intersecting as drawn (the chapter-2 incident class)."""
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,400 size:16pt maxwidth:800 maxheight:200 '
           '"{{ text_1 | default(\\"One\\") }}"\n'
           'text 300,450 size:16pt maxwidth:800 maxheight:200 '
           '"{{ text_2 | default(\\"Two\\") }}"\n')
    profile = _classify(dsl, brand)
    sw = profile.get("slot_warnings", {})
    assert any(w.startswith("SLOT_BOX_OVERLAP") for w in sw.get("text_1", []))
    assert any(w.startswith("SLOT_BOX_OVERLAP") for w in sw.get("text_2", []))


def test_clean_layout_has_no_warnings_key(tmp_path):
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,100 size:16pt maxwidth:900 maxheight:200 '
           '"{{ text_1 | default(\\"Fine\\") }}"\n'
           'text 100,400 size:16pt maxwidth:900 maxheight:200 '
           '"{{ text_2 | default(\\"Also fine\\") }}"\n')
    profile = _classify(dsl, brand)
    assert "slot_warnings" not in profile


def test_works_without_brand_dir(tmp_path):
    """No tokens → legacy 2px/pt scale; lint still runs, nothing crashes."""
    dsl = ('canvas 1920x1080\n'
           'text 100,500 size:16pt maxwidth:300 maxheight:20 '
           '"{{ text_1 | default(\\"Label\\") }}"\n')
    profile = classify_layout(
        dsl, layout_name="synth", slide_index=1, total_slides=10,
        asset_root=tmp_path / "assets",
    )
    # 16pt × 2.0 × 1.2 = 38.4px > 20px → impossible even at legacy scale.
    assert any(w.startswith("IMPOSSIBLE_BOX")
               for w in profile.get("slot_warnings", {}).get("text_1", []))


def test_apply_profile_writes_slot_warnings(tmp_path):
    """apply_profile passes slot_warnings through to the written front-matter."""
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,500 size:16pt maxwidth:300 maxheight:27 '
           '"{{ text_1 | default(\\"Label\\") }}"\n')
    profile = _classify(dsl, brand)
    assert "slot_warnings" in profile, "test pre-condition: profile must have warnings"
    result = apply_profile(dsl, profile)
    assert "slot_warnings:" in result


def test_narrow_box_exempts_page_number_role(tmp_path):
    """A page-number slot legitimately holds 1-3 chars — no NARROW_BOX."""
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,1005 size:12pt maxwidth:100 maxheight:200 '
           '"{{ text_1 | default(\\"2\\") }}"\n')
    profile = _classify(dsl, brand)
    assert not any(w.startswith("NARROW_BOX")
                   for w in profile.get("slot_warnings", {}).get("text_1", []))


def test_impossible_box_exempts_decorative_glyph(tmp_path):
    """An oversized 1-char display glyph overflows by design — no warning."""
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,200 size:200pt maxwidth:400 maxheight:209 '
           '"{{ text_1 | default(\\"”\\") }}"\n')
    profile = _classify(dsl, brand)
    assert not any(w.startswith("IMPOSSIBLE_BOX")
                   for w in profile.get("slot_warnings", {}).get("text_1", []))


def test_impossible_box_grace_tolerates_borderline(tmp_path):
    """A box a few % tighter than one line (native-bbox artifact) is silent;
    44pt line ≈ 117px in a 124px box (≈5% under the 10% grace) must NOT fire."""
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,100 size:44pt maxwidth:900 maxheight:124 '
           '"{{ text_1 | default(\\"Title line\\") }}"\n')
    profile = _classify(dsl, brand)
    assert not any(w.startswith("IMPOSSIBLE_BOX")
                   for w in profile.get("slot_warnings", {}).get("text_1", []))


def test_text_over_image_flagged(tmp_path):
    """Full-width text box crossing a right-half picture (slide-22 class).

    text 75,208 maxwidth:1835 maxheight:787 + picture 1006,0 914x1080
    The text box right edge (75+1835=1910) extends well past the picture
    left edge (1006) — TEXT_OVER_IMAGE must be reported for text_1.
    """
    brand = _brand(tmp_path)
    dsl = (
        'canvas 1920x1080\n'
        'picture 1006,0 914x1080 path:"{{ image2 | default(\\"placeholder.jpg\\") }}"\n'
        'text 75,208 size:16pt maxwidth:1835 maxheight:787 '
        '"{{ text_1 | default(\\"Body copy that wraps onto the photo\\") }}"\n'
    )
    profile = _classify(dsl, brand)
    warnings = profile.get("slot_warnings", {})
    assert any(w.startswith("TEXT_OVER_IMAGE")
               for w in warnings.get("text_1", [])), (
        f"Expected TEXT_OVER_IMAGE on text_1; got: {warnings}"
    )


def test_text_inside_fullbleed_image_not_flagged(tmp_path):
    """Title fully inside a full-bleed photo = intentional overlay (chapter-2 class).

    picture 0,0 1920x1080 + text 75,483 maxwidth:1835 maxheight:81
    The text box is entirely contained within the picture → NOT flagged.
    """
    brand = _brand(tmp_path)
    dsl = (
        'canvas 1920x1080\n'
        'picture 0,0 1920x1080 path:"{{ image2 | default(\\"placeholder.jpg\\") }}"\n'
        'text 75,483 size:30pt maxwidth:1835 maxheight:81 '
        '"{{ text_1 | default(\\"Chapter Title\\") }}"\n'
    )
    profile = _classify(dsl, brand)
    warnings = profile.get("slot_warnings", {})
    assert not any(w.startswith("TEXT_OVER_IMAGE")
                   for w in warnings.get("text_1", [])), (
        f"Unexpected TEXT_OVER_IMAGE on text_1 (fully contained overlay); got: {warnings}"
    )

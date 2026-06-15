"""Discovery-driven picker: profile coverage + parity + brand-only ranking.

These tests lock in the invariant that motivated the refactor: the picker's
universe is the on-disk universe. Every layout that discovery can find has a
valid affinity profile, so a layout can never exist on disk yet be
unpickable (the pre-refactor `_LAYOUTS` dict drifted from disk and left 8
bundled layouts unrankable).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from feinschliff.dsl.parser import parse_document_file, split_frontmatter
from feinschliff.layout_discovery import discover_layout_paths
from feinschliff.layout_picker import pick_layout
from feinschliff.layout_profile import (
    ProfileError,
    build_profile_table,
    load_profile,
    parse_profile,
)

_BUNDLED = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff" / "layouts"


def test_every_discovered_layout_has_a_valid_profile():
    """strict=True must not raise — every discovered layout is pickable."""
    paths = discover_layout_paths()
    table = build_profile_table(paths, strict=True)
    assert set(table) == set(paths)
    assert len(table) >= 50


def test_no_bundled_layout_is_orphaned_from_the_picker():
    """The exact failure mode the refactor fixes: a .slide.dsl on disk with
    no picker profile."""
    on_disk = {p.name[: -len(".slide.dsl")] for p in _BUNDLED.glob("*.slide.dsl")}
    table = build_profile_table(discover_layout_paths(), strict=True)
    missing = sorted(on_disk - set(table))
    assert missing == [], f"layouts on disk but unpickable: {missing}"


@pytest.mark.parametrize(
    "orphan",
    [
        "agenda-photo", "chart-photo", "end-image", "full-bleed-editorial",
        "kpi-photo", "photo-grid", "photo-strip-four", "v-model",
    ],
)
def test_formerly_orphan_layouts_now_rank(orphan):
    """The 8 layouts that were never in the old _LAYOUTS dict now score."""
    profile = load_profile(_BUNDLED / f"{orphan}.slide.dsl")
    ranked = pick_layout(
        role=profile["role"],
        concept_count=profile["ideal_count"][0],
        comparison=profile["comp"],
        data_quantity=3 if profile["data"] != "none" else None,
        top_k=60,
    )
    assert orphan in {r["layout"] for r in ranked}


def test_parity_known_layout_scoring_unchanged():
    """Scoring math is preserved: kpi-grid is the top data-quantity/kpi pick,
    and its score matches the legacy formula (role +3, count-in-band +2,
    data-band +2 = 7)."""
    ranked = pick_layout(role="data-quantity", concept_count=3, data_quantity=3, top_k=1)
    assert ranked[0]["layout"] == "kpi-grid"
    assert ranked[0]["score"] == 7.0


def test_variety_exempt_declared_in_frontmatter_is_honored():
    """title-orange declares variety_exempt: true → no consecutive-use
    penalty, while a non-exempt layout in the same role does take it."""
    def score_of(layout_id, history):
        ranked = pick_layout(
            role="title-primary", concept_count=1, top_k=60,
            layout_history=history,
        )
        return next(r["score"] for r in ranked if r["layout"] == layout_id)

    # Exempt layout: identical score whether or not it was just used.
    assert score_of("title-orange", None) == score_of("title-orange", ["title-orange"])
    # Non-exempt layout in the same role: variety penalty when it was the
    # last pick (cooldown curve: -3.0 / -2.0 / -1.0 / -0.5 across
    # positions -1..-4).
    assert score_of("action-title", ["action-title"]) == score_of("action-title", None) - 3.0


def test_parser_skips_fence_but_layout_still_renders():
    """A fenced layout parses to a normal Document (fence stripped)."""
    fm, _ = split_frontmatter((_BUNDLED / "kpi-grid.slide.dsl").read_text())
    assert fm is not None and "role:" in fm
    doc = parse_document_file(_BUNDLED / "kpi-grid.slide.dsl")
    assert doc is not None


def test_missing_profile_fails_loud(tmp_path):
    layout = tmp_path / "no-fence.slide.dsl"
    layout.write_text("canvas 1920x1080\ntheme feinschliff\n")
    with pytest.raises(ProfileError):
        load_profile(layout)


# ── content-metadata passthrough (decompiled brand packs) ────────────────────

_MINIMAL_FM = (
    "role: data-quantity\n"
    "ideal_count: [2, 4]\n"
    "data_band: kpi\n"
    "comparison: false\n"
)


def test_parse_profile_passes_through_content_metadata():
    """fixed_chrome / chrome_text / description / chrome_subject ride
    through verbatim."""
    profile = parse_profile(
        _MINIMAL_FM
        + "fixed_chrome: true\n"
        + "chrome_text: true\n"
        + "description: Workshop illustrations left, text column right\n"
        + "chrome_subject: courtyard planters\n"
        + "when_to_use: KPI walls for quarterly reviews\n"
        + "family: data\n"
        + "element_tree: ['text text_1 role=title @76,76 922x122 20pt']\n",
        source="t",
    )
    assert profile["fixed_chrome"] is True
    assert profile["chrome_text"] is True
    assert profile["description"] == "Workshop illustrations left, text column right"
    assert profile["chrome_subject"] == "courtyard planters"
    assert profile["when_to_use"] == "KPI walls for quarterly reviews"
    assert profile["family"] == "data"
    assert profile["element_tree"] == [
        "text text_1 role=title @76,76 922x122 20pt"
    ]


def test_parse_profile_content_metadata_absent_is_omitted():
    """Optional means optional: absent fields don't appear at all."""
    profile = parse_profile(_MINIMAL_FM, source="t")
    for key in ("fixed_chrome", "chrome_text", "description", "chrome_subject",
                "when_to_use", "family", "element_tree"):
        assert key not in profile


def test_parse_profile_content_metadata_wrong_type_is_ignored():
    """Type-or-ignore: mistyped content metadata is dropped, not an error —
    while the strict required-key validation stays intact."""
    profile = parse_profile(
        _MINIMAL_FM
        + "fixed_chrome: maybe\n"   # str, not bool
        + "chrome_text: sometimes\n"  # str, not bool
        + "description: [a, b]\n"   # list, not str
        + "chrome_subject: 7\n"     # int, not str
        + "when_to_use: [x]\n"      # list, not str
        + "family: 3\n"             # int, not str
        + "element_tree: {a: b}\n",  # dict, not list of str
        source="t",
    )
    for key in ("fixed_chrome", "chrome_text", "description", "chrome_subject",
                "when_to_use", "family", "element_tree"):
        assert key not in profile
    # Existing strictness is untouched.
    with pytest.raises(ProfileError):
        parse_profile("role: data-quantity\n", source="t")


def test_brand_only_layout_is_ranked(tmp_path):
    """A layout that exists ONLY in a brand pack must be a pick candidate —
    the gap that the dual-dict hack papered over."""
    brand_layouts = tmp_path / "layouts"
    brand_layouts.mkdir()
    (brand_layouts / "brand-special.slide.dsl").write_text(
        "---\n"
        "role: data-quantity\n"
        "ideal_count: [2, 4]\n"
        "data_band: kpi\n"
        "comparison: false\n"
        "---\n"
        "canvas 1920x1080\ntheme feinschliff\n"
    )
    # Merge toolkit ∪ brand, brand wins (mirrors BrandPack.layout_table).
    paths = dict(discover_layout_paths())
    paths["brand-special"] = brand_layouts / "brand-special.slide.dsl"
    table = build_profile_table(paths, strict=True)
    ranked = pick_layout(
        role="data-quantity", concept_count=3, data_quantity=3,
        top_k=60, profiles=table,
    )
    assert "brand-special" in {r["layout"] for r in ranked}

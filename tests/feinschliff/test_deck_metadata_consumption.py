"""Autonomous consumption of brand-layout content metadata by the deck
pipeline (feinschliff.deck.content_metadata):

1. deck-map skeleton picks — `deck-map.yaml` roles become rank-1 defaults
   at both picker call sites (LayoutPicker + plan_deck_layouts); explicit
   `layout:` pins win.
2. slot-role auto-binding — footer / page-number slots fill from
   deck-level vars / the slide index; explicit ctx (even "") wins.
3. replace-slot query auto-derivation — unbound `class: replace` image
   slots get a query from the slide's bound content; `keep` is never
   auto-bound; no provider → no binding.

Fixtures are synthetic tmp brand packs with neutral garden/office themes.
"""
from __future__ import annotations

import argparse
import shutil
import textwrap
from pathlib import Path

import yaml

from feinschmiede.brand import BrandPack
from feinschliff.deck.content_metadata import (
    DECK_MAP_BONUS,
    apply_deck_map_bonus,
    auto_bind_slots,
    deck_map_layouts_for_role,
    load_deck_map,
)
from feinschliff.deck.orchestrate import signals_from_slide
from feinschliff.deck.picker import LayoutPicker
from feinschliff.dsl.parser import parse_file
from feinschliff.layout_budget import plan_deck_layouts
from feinschliff.layout_profile import parse_profile

REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
FEINSCHLIFF_TOKENS = REPO_ROOT / "brands" / "feinschliff" / "tokens.json"


# ── fixture helpers ──────────────────────────────────────────────────────────

def _write_layout(layouts_dir: Path, name: str, frontmatter: dict, body: str) -> Path:
    layouts_dir.mkdir(parents=True, exist_ok=True)
    path = layouts_dir / f"{name}.slide.dsl"
    fence = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
    path.write_text("---\n" + fence + "---\n" + textwrap.dedent(body),
                    encoding="utf-8")
    return path


_COVER_FM = {
    "role": "title-primary",
    "ideal_count": [1, 2],
    "data_band": "none",
    "comparison": False,
    "variety_exempt": True,
}

_COVER_BODY = """\
    canvas 1920x1080
    text 160,260 style:title maxwidth:1600 "{{ text_1 }}"
    text 160,700 style:body maxwidth:1600 "{{ text_2 }}"
"""


def _garden_pack(tmp_path: Path, *, with_deck_map: bool = True) -> Path:
    """A minimal brand pack with a brand-local cover layout."""
    root = tmp_path / "brands" / "verdant-garden"
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy(FEINSCHLIFF_TOKENS, root / "tokens.json")
    _write_layout(root / "layouts", "garden-cover", _COVER_FM, _COVER_BODY)
    if with_deck_map:
        (root / "deck-map.yaml").write_text(
            yaml.safe_dump({"cover": "garden-cover", "content": []}),
            encoding="utf-8",
        )
    return root


# ── Feature 1: deck-map helpers ──────────────────────────────────────────────

def test_load_deck_map_missing_returns_none(tmp_path):
    assert load_deck_map(tmp_path) is None


def test_load_deck_map_reads_yaml_and_accepts_brandpack(tmp_path):
    root = _garden_pack(tmp_path)
    assert load_deck_map(root) == {"cover": "garden-cover", "content": []}
    pack = BrandPack.load(root)
    assert load_deck_map(pack) == {"cover": "garden-cover", "content": []}


def test_deck_map_layouts_for_role_maps_and_normalises():
    deck_map = {
        "cover": "garden-cover",
        "section": ["hedge-a", "hedge-b", 7],
        "closer": 42,
    }
    assert deck_map_layouts_for_role(deck_map, "title-primary") == ["garden-cover"]
    assert deck_map_layouts_for_role(deck_map, "chapter-opener") == ["hedge-a", "hedge-b"]
    assert deck_map_layouts_for_role(deck_map, "closer") == []  # mistyped → ignored
    # No `content:` in the deck-map → content-* roles still resolve empty.
    assert deck_map_layouts_for_role(deck_map, "content-columns") == []
    assert deck_map_layouts_for_role(None, "title-primary") == []


def test_deck_map_layouts_for_role_falls_back_to_content_list():
    # A brand that curates its content vocabulary needs the picker to
    # inherit that list for every non-framing role, otherwise toolkit
    # affinity scores silently outrank brand layouts.
    deck_map = {
        "cover": "garden-cover",
        "content": ["potting-grid", "herb-rows", 99],
    }
    assert deck_map_layouts_for_role(deck_map, "content-columns") == ["potting-grid", "herb-rows"]
    assert deck_map_layouts_for_role(deck_map, "content-narrative") == ["potting-grid", "herb-rows"]
    assert deck_map_layouts_for_role(deck_map, "data-timeline") == ["potting-grid", "herb-rows"]
    # Framing moments still go through the explicit map, not the fallback.
    assert deck_map_layouts_for_role(deck_map, "title-primary") == ["garden-cover"]
    # No `content:` key → unmapped roles resolve to [] (no spurious matches).
    assert deck_map_layouts_for_role({"cover": "garden-cover"}, "content-columns") == []


def test_apply_deck_map_bonus_puts_target_rank1_without_mutating():
    candidates = [
        {"layout": "atrium-title", "score": 5.0, "rationale": ["role"]},
        {"layout": "garden-cover", "score": 3.0, "rationale": ["role"]},
    ]
    out = apply_deck_map_bonus(
        candidates, role="title-primary", deck_map={"cover": "garden-cover"},
    )
    assert out[0]["layout"] == "garden-cover"
    assert out[0]["score"] == 3.0 + DECK_MAP_BONUS
    assert "deck-map" in out[0]["rationale"]
    # Inputs untouched (additive re-rank, not in-place mutation).
    assert candidates[1]["score"] == 3.0
    assert "deck-map" not in candidates[1]["rationale"]


# ── Feature 1: fan-out call site (plan_deck_layouts) ─────────────────────────

_PLAN_PROFILES = {
    # "atrium-title" sorts before "garden-cover", so on the tied race it
    # wins WITHOUT the deck-map bonus — the control for the test below.
    "atrium-title": {"role": "title-primary", "ideal_count": (1, 2),
                     "data": "none", "comp": False, "variety_exempt": True},
    "garden-cover": {"role": "title-primary", "ideal_count": (1, 2),
                     "data": "none", "comp": False, "variety_exempt": True},
    "potting-grid": {"role": "content-columns", "ideal_count": (2, 4),
                     "data": "none", "comp": False},
}
_PLAN_DECK_MAP = {"cover": "garden-cover", "content": ["potting-grid"]}


def test_plan_deck_layouts_deck_map_makes_cover_rank1():
    signals = [{"role": "title-primary"}]
    control = plan_deck_layouts(signals, profiles=_PLAN_PROFILES)
    assert control[0]["layout"] == "atrium-title"

    planned = plan_deck_layouts(
        signals, profiles=_PLAN_PROFILES, deck_map=_PLAN_DECK_MAP,
    )
    assert planned[0]["layout"] == "garden-cover"
    assert "deck-map" in planned[0]["rationale"]


def test_plan_deck_layouts_explicit_pin_wins_over_deck_map():
    signals = [{"role": "title-primary", "layout": "terrace-cover"}]
    planned = plan_deck_layouts(
        signals, profiles=_PLAN_PROFILES, deck_map=_PLAN_DECK_MAP,
    )
    assert planned[0]["layout"] == "terrace-cover"
    assert planned[0]["rationale"] == ["pinned"]


def test_signals_from_slide_carries_layout_pin():
    signals = signals_from_slide({"role": "title-primary", "layout": "garden-cover"})
    assert signals["layout"] == "garden-cover"
    assert signals_from_slide({"role": "quote"})["layout"] is None


# ── Feature 1: serial call site (LayoutPicker) ───────────────────────────────

def test_layout_picker_deck_map_puts_brand_cover_rank1(tmp_path):
    root = _garden_pack(tmp_path, with_deck_map=True)
    picker = LayoutPicker(brand=BrandPack.load(root), top_k=3)
    result = picker.candidates({"role": "title-primary"})
    assert result[0].layout_name == "garden-cover"
    assert "deck-map" in result[0].reason
    # And the path resolves brand-locally.
    assert result[0].layout_path == root / "layouts" / "garden-cover.slide.dsl"


def test_layout_picker_without_deck_map_brand_cover_not_boosted(tmp_path):
    root = _garden_pack(tmp_path, with_deck_map=False)
    picker = LayoutPicker(brand=BrandPack.load(root), top_k=1)
    result = picker.candidates({"role": "title-primary"})
    # Picker isolation: when the brand ships a non-empty layouts/, ONLY brand
    # layouts are in the pool (toolkit layouts are excluded). With no deck-map
    # bonus, the brand layout wins on bare role-match (+3) — no toolkit
    # layouts compete.
    assert result[0].layout_name == "garden-cover"
    # And no deck-map rationale (no bonus applied).
    assert "deck-map" not in result[0].reason


# ── Feature 1: plan-skeleton end-to-end wiring ───────────────────────────────

def test_plan_skeleton_emits_unpicked_skeleton(tmp_path, monkeypatch):
    """plan-skeleton no longer runs the deterministic picker — it emits
    `layout: null` per slide and the orchestrating LLM picks via the
    cascade in `skills/deck/references/picking.md`. The Python picker
    was blind to per-layout semantic annotations and mis-matched layouts
    that structurally fit but were semantically wrong."""
    from feinschliff.cli.deck_subcommands.plan_log import cmd_plan_skeleton

    root = _garden_pack(tmp_path)
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", str(root.parent))

    content_plan = tmp_path / "content_plan.yaml"
    content_plan.write_text(yaml.safe_dump({
        "brand": "verdant-garden",
        "slides": [
            {"index": 0, "title": "Opening the garden year", "role": "title-primary"},
            {"index": 1, "title": "Section divider", "role": "title-primary"},
        ],
    }), encoding="utf-8")

    out = tmp_path / "deck" / "plan.skeleton.yaml"
    args = argparse.Namespace(
        content_plan=str(content_plan), output=str(out),
        brand=None, out_pptx=None,
    )
    assert cmd_plan_skeleton(args) == 0

    skeleton = yaml.safe_load(out.read_text(encoding="utf-8"))
    slides = skeleton["slides"]
    assert all(s["layout"] is None for s in slides)
    assert all(s["_meta"]["layout_rationale"] == "cascade:pending" for s in slides)
    assert all(s["content"] == {} for s in slides)
    # Slide metadata still flows through so the orchestrator can read it.
    assert slides[0]["_meta"]["title"] == "Opening the garden year"
    assert slides[0]["_meta"]["role"] == "title-primary"


# ── Features 2+3: profile passthrough ────────────────────────────────────────

def test_parse_profile_passes_slots_and_image_queries_through():
    fm = textwrap.dedent("""\
        role: content-columns
        ideal_count: [1, 2]
        data_band: none
        comparison: false
        slots:
          text_1: {role: title, chars: 40}
          hero: {role: image, class: replace}
          mistyped: not-a-dict
        image_queries: {hero: office plants, mistyped: 7}
    """)
    profile = parse_profile(fm, source="test")
    assert profile["slots"] == {
        "text_1": {"role": "title", "chars": 40},
        "hero": {"role": "image", "class": "replace"},
    }
    assert profile["image_queries"] == {"hero": "office plants"}


def test_parse_profile_ignores_mistyped_slots_block():
    fm = textwrap.dedent("""\
        role: content-columns
        ideal_count: [1, 2]
        data_band: none
        comparison: false
        slots: [one, two]
        image_queries: nope
    """)
    profile = parse_profile(fm, source="test")
    assert "slots" not in profile
    assert "image_queries" not in profile


# ── Features 2+3: auto_bind_slots fixture ────────────────────────────────────

_OFFICE_FM = {
    "role": "content-columns",
    "ideal_count": [1, 2],
    "data_band": "none",
    "comparison": False,
    # Frontmatter declares text_3 before text_4, but text_4 renders at a
    # SMALLER x — the binding must order footers by x, not declaration.
    "slots": {
        "text_1": {"role": "title", "chars": 40, "default": "Office tour"},
        "text_2": {"role": "body", "chars": 200, "default": "Body"},
        "text_3": {"role": "footer", "chars": 30, "default": "Right footer"},
        "text_4": {"role": "footer", "chars": 30, "default": "Left footer"},
        "text_5": {"role": "page-number", "chars": 4, "default": "1"},
        "hero":   {"role": "image", "class": "replace"},
        "badge":  {"role": "image", "class": "keep"},
    },
    "image_queries": {"hero": "office plants", "badge": "badge mark"},
}

_OFFICE_BODY = """\
    canvas 1920x1080
    text 160,120 style:title maxwidth:1600 "{{ text_1 }}"
    text 160,320 style:body maxwidth:1600 "{{ text_2 }}"
    text 1500,990 style:body maxwidth:300 "{{ text_3 }}"
    text 100,990 style:body maxwidth:300 "{{ text_4 }}"
    text 1810,990 style:body maxwidth:100 "{{ text_5 }}"
    picture 1200,200 600x600 path:"{{ hero }}"
    picture 60,60 120x120 path:"{{ badge }}"
"""


def _office_layout(tmp_path: Path) -> tuple[Path, list]:
    path = _write_layout(tmp_path / "layouts", "office-tour", _OFFICE_FM, _OFFICE_BODY)
    nodes, _ = parse_file(path)
    return path, nodes


_DECK_VARS = {"footer_left": "Garden Co", "footer_right": "Spring 2026"}


# ── Feature 2: footer / page-number auto-binding ─────────────────────────────

def test_footer_slots_bind_by_x_and_page_number_binds_index(tmp_path):
    layout_path, nodes = _office_layout(tmp_path)
    ctx = auto_bind_slots(
        {}, layout_path=layout_path, layout_nodes=nodes,
        slide_index=4, deck_vars=_DECK_VARS,
    )
    assert ctx["text_4"] == "Garden Co"      # leftmost (x=100) ← footer_left
    assert ctx["text_3"] == "Spring 2026"    # rightmost (x=1500) ← footer_right
    assert ctx["text_5"] == "4"              # 1-based slide index
    assert "text_1" not in ctx and "text_2" not in ctx


def test_explicit_ctx_binding_wins_even_empty_string(tmp_path):
    layout_path, nodes = _office_layout(tmp_path)
    ctx = auto_bind_slots(
        {"text_3": "", "text_5": "VII"},
        layout_path=layout_path, layout_nodes=nodes,
        slide_index=2, deck_vars=_DECK_VARS,
    )
    assert ctx["text_3"] == ""       # explicit "" blanks the slot — kept
    assert ctx["text_5"] == "VII"    # explicit page number — kept
    assert ctx["text_4"] == "Garden Co"  # the unbound footer still binds


def test_single_footer_slot_gets_footer_right(tmp_path):
    fm = dict(_OFFICE_FM)
    fm["slots"] = {
        "text_1": {"role": "title", "chars": 40},
        "text_3": {"role": "footer", "chars": 30},
    }
    path = _write_layout(tmp_path / "layouts", "office-solo", fm, _OFFICE_BODY)
    nodes, _ = parse_file(path)
    ctx = auto_bind_slots(
        {}, layout_path=path, layout_nodes=nodes,
        slide_index=1, deck_vars=_DECK_VARS,
    )
    assert ctx["text_3"] == "Spring 2026"
    assert "footer_left" not in ctx


def test_layout_without_slots_metadata_returns_ctx_unchanged(tmp_path):
    fm = {k: v for k, v in _OFFICE_FM.items()
          if k not in ("slots", "image_queries")}
    path = _write_layout(tmp_path / "layouts", "office-plain", fm, _OFFICE_BODY)
    nodes, _ = parse_file(path)
    ctx = {"text_1": "Hello"}
    out = auto_bind_slots(
        ctx, layout_path=path, layout_nodes=nodes,
        slide_index=3, deck_vars=_DECK_VARS, image_provider_available=True,
    )
    assert out == ctx


def test_layout_without_frontmatter_returns_ctx_unchanged(tmp_path):
    path = tmp_path / "layouts" / "bare.slide.dsl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(_OFFICE_BODY), encoding="utf-8")
    nodes, _ = parse_file(path)
    ctx = {"text_1": "Hello"}
    assert auto_bind_slots(
        ctx, layout_path=path, layout_nodes=nodes,
        slide_index=1, deck_vars=_DECK_VARS,
    ) == ctx


# ── Feature 3: replace-slot query auto-derivation ────────────────────────────

def test_replace_slot_derives_query_from_title(tmp_path):
    layout_path, nodes = _office_layout(tmp_path)
    ctx = auto_bind_slots(
        {"text_1": "Watering the rooftop garden beds for summer"},
        layout_path=layout_path, layout_nodes=nodes,
        slide_index=1, image_provider_available=True,
    )
    # Stopwords/short words dropped, lowercased, ≤6 significant words.
    assert ctx["hero"] == "watering rooftop garden beds summer"


def test_keep_slot_is_never_auto_bound(tmp_path):
    layout_path, nodes = _office_layout(tmp_path)
    ctx = auto_bind_slots(
        {"text_1": "Watering the rooftop garden beds for summer"},
        layout_path=layout_path, layout_nodes=nodes,
        slide_index=1, image_provider_available=True,
    )
    assert "badge" not in ctx  # despite an image_queries entry for it


def test_replace_slot_falls_back_to_image_queries_hint(tmp_path):
    layout_path, nodes = _office_layout(tmp_path)
    ctx = auto_bind_slots(
        {}, layout_path=layout_path, layout_nodes=nodes,
        slide_index=1, image_provider_available=True,
    )
    assert ctx["hero"] == "office plants"


def test_replace_slot_unbound_without_provider(tmp_path):
    layout_path, nodes = _office_layout(tmp_path)
    ctx = auto_bind_slots(
        {"text_1": "Watering the rooftop garden beds for summer"},
        layout_path=layout_path, layout_nodes=nodes,
        slide_index=1, image_provider_available=False,
    )
    assert "hero" not in ctx and "badge" not in ctx


def test_explicit_image_binding_wins(tmp_path):
    layout_path, nodes = _office_layout(tmp_path)
    ctx = auto_bind_slots(
        {"hero": "assets/custom.png", "text_1": "Pruning the orchard rows"},
        layout_path=layout_path, layout_nodes=nodes,
        slide_index=1, image_provider_available=True,
    )
    assert ctx["hero"] == "assets/custom.png"

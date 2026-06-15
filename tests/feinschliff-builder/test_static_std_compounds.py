"""Regression tests — std compounds must resolve from the feinschmiede engine.

The builder used to derive the std compounds dir as
``Path(__file__).parents[2] / "compounds"`` (feinschliff-builder/compounds,
which does not exist); ``load_compounds`` silently skips missing dirs, so
slot budgets contributed by std compounds (kpi-cell's value/unit/key/delta)
vanished and SLOT_OVERFLOW checks inside them were silently skipped.
All callers now share :func:`feinschmiede.compounds_dir`.
"""
from __future__ import annotations

from pathlib import Path

from feinschliff_builder.verify.static import static_verify
from feinschmiede import compounds_dir


# Core plugin root (feinschliff) is the sibling directory; brands/layouts live there.
REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
BRAND_DIR = REPO_ROOT / "brands" / "feinschliff"
LAYOUTS_DIR = REPO_ROOT / "brands" / "feinschliff" / "layouts"


def test_compounds_dir_is_the_engine_compounds():
    """compounds_dir() points at an existing dir that ships kpi-cell.dsl."""
    d = compounds_dir()
    assert d.is_dir(), f"std compounds dir missing: {d}"
    assert (d / "kpi-cell.dsl").is_file()


def test_kpi_grid_budgets_include_std_compound_slots():
    """compute_slot_budgets on kpi-grid carries the kpi-cell slot budgets.

    With the broken parents[2] resolution the kpi-cell compound never
    loaded, so kpis[].value/unit/key/delta had no budgets at all.
    """
    from feinschliff.dsl.parser import parse_file
    from feinschmiede.dsl.tokens import load_tokens
    from feinschliff.dsl.expander import load_compounds_for_brand
    from feinschliff.slot_budget import compute_slot_budgets

    layout_nodes, _ = parse_file(LAYOUTS_DIR / "kpi-grid.slide.dsl")
    tokens = load_tokens(BRAND_DIR)
    compounds = load_compounds_for_brand(BRAND_DIR, std_dir=compounds_dir())
    budgets = compute_slot_budgets(layout_nodes, tokens, compounds=compounds)

    for slot in ("kpis[].value", "kpis[].unit", "kpis[].key", "kpis[].delta"):
        assert slot in budgets, (
            f"Expected std-compound slot {slot!r} in budgets, got: {sorted(budgets)}"
        )


def test_static_verify_flags_overflowing_kpi_value():
    """An over-budget kpis[0].value fires SLOT_OVERFLOW (previously silent)."""
    from feinschliff.defects import DefectKind

    long_value = "1,234,567,890,123 units total"
    plan = {
        "brand": "feinschliff",
        "out": "deck.pptx",
        "slides": [
            {
                "layout": "layouts/kpi-grid.slide.dsl",
                "content": {
                    "pgmeta": "Q1 2026",
                    "title": "Key figures",
                    "kpis": [
                        {"value": long_value, "unit": "%", "key": "Revenue", "delta": "+3 pp"},
                        {"value": "12", "unit": "M", "key": "Users", "delta": "+1 M"},
                    ],
                    "footer_left": "Corp",
                    "footer_right": "2026",
                },
            }
        ],
    }
    defects = static_verify(plan, BRAND_DIR)
    overflow = [
        d for d in defects
        if d.kind == DefectKind.SLOT_OVERFLOW and "kpis" in d.meta.get("slot", "")
    ]
    assert len(overflow) >= 1, (
        f"Expected ≥1 SLOT_OVERFLOW defect for an over-budget kpi value, got: {defects}"
    )
    assert overflow[0].slide_index == 1

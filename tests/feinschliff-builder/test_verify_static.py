"""Tests for lib/verify/static.py — pre-render static geometry verify.

These tests use real layouts from feinschliff/layouts/ so the slot budgets
are pixel-accurate (same as production). Hand-crafted plan dicts exercise
the three main code paths: clean, slot-overflow, and empty-placeholder.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from feinschliff_builder.verify.static import static_verify, validate
from feinschmiede.brand import BrandPack
from feinschmiede.diagnostics import DiagnosticBag, Severity


# Core plugin root (feinschliff) is the sibling directory; brands/layouts live there.
REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
BRANDS_DIR = REPO_ROOT / "brands"
BRAND_DIR = REPO_ROOT / "brands" / "feinschliff"
LAYOUTS_DIR = REPO_ROOT / "brands" / "feinschliff" / "layouts"
BRAND_PACK = BrandPack.load(BRAND_DIR)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plan(layout_rel: str, content: dict, brand: str = "feinschliff") -> dict:
    """Build a minimal plan dict with one slide, using a toolkit layout."""
    return {
        "brand": brand,
        "out": "deck.pptx",
        "slides": [
            {
                "layout": f"layouts/{layout_rel}",
                "content": content,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Import guard — the module must exist before tests run
# ---------------------------------------------------------------------------

def test_static_verify_importable():
    """feinschliff_builder.verify.static must be importable and export static_verify."""
    assert callable(static_verify)


def test_defect_kind_has_empty_placeholder():
    """DefectKind must carry EMPTY_PLACEHOLDER."""
    from feinschliff.defects import DefectKind
    assert hasattr(DefectKind, "EMPTY_PLACEHOLDER")
    assert DefectKind.EMPTY_PLACEHOLDER.value == "empty-placeholder"


# ---------------------------------------------------------------------------
# Happy path — clean plan → no defects
# ---------------------------------------------------------------------------

def test_clean_plan_returns_no_defects():
    """A properly filled end.slide.dsl plan produces zero defects.

    We use the ``end`` layout because it has only simple (non-array) slots:
    pgmeta, title, footnote, footer_left, footer_right.  Filling all of them
    should yield zero defects.
    """

    plan = _make_plan(
        "end.slide.dsl",
        {
            "pgmeta": "Q1 2026",
            "title": "Thank you",
            "footnote": "Acme Corp",
            "footer_left": "Acme Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    assert defects == [], f"Expected no defects, got: {defects}"


# ---------------------------------------------------------------------------
# slot-overflow
# ---------------------------------------------------------------------------

def test_overflow_plan_returns_slot_overflow_defect():
    """A title that overflows its pixel budget produces a SLOT_OVERFLOW defect.

    Uses executive-summary where action_title has max_lines=2, max_chars≈156-168.
    A 220+-char title wrapping to 3 lines must produce a SLOT_OVERFLOW defect.
    """
    from feinschliff.defects import DefectKind

    # action_title budget: max_lines=2, chars_per_line≈78-84.
    # A 220+-char title will wrap to 3 lines → overflow.
    long_title = (
        "We must urgently restructure our entire go-to-market approach because "
        "enterprise revenue has declined for three consecutive quarters while churn "
        "accelerated faster than new logo acquisition and expansion bookings could offset"
    )
    assert len(long_title) > 168, "test precondition: title must exceed char budget"

    plan = _make_plan(
        "executive-summary.slide.dsl",
        {
            "action_title": long_title,
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    overflow = [d for d in defects if d.kind == DefectKind.SLOT_OVERFLOW]
    assert len(overflow) >= 1, (
        f"Expected ≥1 SLOT_OVERFLOW defect for a very long title, got: {defects}"
    )
    assert overflow[0].slide_index == 1


# ---------------------------------------------------------------------------
# empty-placeholder
# ---------------------------------------------------------------------------

def test_empty_placeholder_plan_returns_defect():
    """A plan where a required slot is empty returns EMPTY_PLACEHOLDER.

    Uses end.slide.dsl: title is an interpolated slot.  Supplying an empty
    string triggers the EMPTY_PLACEHOLDER defect.
    """
    from feinschliff.defects import DefectKind

    plan = _make_plan(
        "end.slide.dsl",
        {
            "pgmeta": "Q1 2026",
            "title": "",              # empty → should fire
            "footnote": "Acme Corp",
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    ep = [d for d in defects if d.kind == DefectKind.EMPTY_PLACEHOLDER]
    assert len(ep) >= 1, (
        f"Expected ≥1 EMPTY_PLACEHOLDER defect for empty title, got: {defects}"
    )
    assert ep[0].slide_index == 1


def test_missing_slot_fires_empty_placeholder():
    """Completely absent required slot (not in content dict) also fires."""
    from feinschliff.defects import DefectKind

    # title not provided at all in end.slide.dsl
    plan = _make_plan(
        "end.slide.dsl",
        {
            "pgmeta": "Q1 2026",
            "footnote": "Acme Corp",
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    ep = [d for d in defects if d.kind == DefectKind.EMPTY_PLACEHOLDER]
    assert any(d.meta.get("slot") == "title" for d in ep), (
        f"Expected EMPTY_PLACEHOLDER for missing 'title', got: {ep}"
    )


# ---------------------------------------------------------------------------
# Combined: 1 overflow + 1 empty-placeholder → at least 2 defects
# ---------------------------------------------------------------------------

def test_combined_overflow_and_empty_placeholder():
    """Hand-crafted plan with one overflow AND one empty slot → both defect kinds.

    Uses executive-summary (real layout):
    - action_title with 220+ chars (3 wrapped lines) overflows the 2-line budget.
    - summary="" triggers EMPTY_PLACEHOLDER.
    """
    from feinschliff.defects import DefectKind

    long_title = (
        "Revenue declined for three consecutive quarters because enterprise churn "
        "accelerated faster than new logo acquisition could offset while pipeline "
        "coverage deteriorated across every major region and customer segment"
    )
    assert len(long_title) > 168, "test precondition: title must exceed char budget"

    plan = _make_plan(
        "executive-summary.slide.dsl",
        {
            "action_title": long_title,  # overflow
            "summary": "",               # empty-placeholder
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)

    kinds = {d.kind for d in defects}
    assert DefectKind.SLOT_OVERFLOW in kinds, (
        f"Missing SLOT_OVERFLOW in {defects}"
    )
    assert DefectKind.EMPTY_PLACEHOLDER in kinds, (
        f"Missing EMPTY_PLACEHOLDER in {defects}"
    )
    overflow_at_1 = [
        d for d in defects
        if d.kind == DefectKind.SLOT_OVERFLOW and d.slide_index == 1
    ]
    ep_at_1 = [
        d for d in defects
        if d.kind == DefectKind.EMPTY_PLACEHOLDER and d.slide_index == 1
    ]
    assert len(overflow_at_1) >= 1
    assert len(ep_at_1) >= 1


# ---------------------------------------------------------------------------
# Multi-slide plan — defects carry correct slide_index
# ---------------------------------------------------------------------------

def test_multi_slide_slide_index_is_correct():
    """slide_index in Defect must match the position in the plan.

    Slide 1 is clean; slide 2 has an empty title → EMPTY_PLACEHOLDER on
    slide 2 only.
    """
    from feinschliff.defects import DefectKind

    plan = {
        "brand": "feinschliff",
        "out": "deck.pptx",
        "slides": [
            {
                "layout": "layouts/end.slide.dsl",
                "content": {
                    "pgmeta": "Q1 2026",
                    "title": "Thank you",
                    "footnote": "Acme Corp",
                    "footer_left": "Corp",
                    "footer_right": "2026",
                },
            },
            {
                "layout": "layouts/end.slide.dsl",
                "content": {
                    "pgmeta": "Q1 2026",
                    "title": "",          # empty on slide 2
                    "footnote": "Acme Corp",
                    "footer_left": "Corp",
                    "footer_right": "2026",
                },
            },
        ],
    }
    defects = static_verify(plan, BRAND_DIR)
    ep = [d for d in defects if d.kind == DefectKind.EMPTY_PLACEHOLDER]
    assert any(d.slide_index == 2 for d in ep), (
        f"Expected EMPTY_PLACEHOLDER on slide 2, got: {ep}"
    )
    # Slide 1 must not produce an EMPTY_PLACEHOLDER
    ep_slide1 = [d for d in ep if d.slide_index == 1]
    assert ep_slide1 == [], f"Slide 1 should be clean, got: {ep_slide1}"


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------

def test_empty_placeholder_defects_are_warn_severity():
    """EMPTY_PLACEHOLDER defects must be WARN, not FATAL."""
    from feinschliff.defects import DefectKind, Severity

    plan = _make_plan(
        "end.slide.dsl",
        {"title": "", "footer_left": "Corp", "footer_right": "2026"},
    )
    defects = static_verify(plan, BRAND_DIR)
    ep = [d for d in defects if d.kind == DefectKind.EMPTY_PLACEHOLDER]
    assert ep, "Expected at least one EMPTY_PLACEHOLDER defect to check severity"
    for d in ep:
        assert d.severity == Severity.WARN, (
            f"Expected WARN for EMPTY_PLACEHOLDER, got {d.severity} for {d}"
        )


def test_slot_overflow_defects_are_fatal_severity():
    """SLOT_OVERFLOW defects must be FATAL now that real font metrics are in use."""
    from feinschliff.defects import DefectKind, Severity

    long_title = (
        "We must urgently restructure our entire go-to-market approach because "
        "enterprise revenue has declined for three consecutive quarters while churn "
        "accelerated faster than new logo acquisition and expansion bookings could offset"
    )
    assert len(long_title) > 168, "test precondition: title must exceed char budget"

    plan = _make_plan(
        "executive-summary.slide.dsl",
        {
            "action_title": long_title,
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    overflow = [d for d in defects if d.kind == DefectKind.SLOT_OVERFLOW]
    assert overflow, "Expected at least one SLOT_OVERFLOW defect to check severity"
    for d in overflow:
        assert d.severity == Severity.FATAL, (
            f"Expected FATAL for SLOT_OVERFLOW, got {d.severity} for {d}"
        )


def test_validate_slot_overflow_maps_to_error():
    """validate() must map SLOT_OVERFLOW (FATAL legacy) → ERROR in the DiagnosticBag."""
    from feinschmiede.diagnostics import Severity as NewSev
    from feinschliff.defects import DefectKind

    long_title = (
        "We must urgently restructure our entire go-to-market approach because "
        "enterprise revenue has declined for three consecutive quarters while churn "
        "accelerated faster than new logo acquisition and expansion bookings could offset"
    )
    plan = _make_plan(
        "executive-summary.slide.dsl",
        {
            "action_title": long_title,
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    bag = validate(plan, BRAND_PACK, plan_dir=REPO_ROOT)
    overflow = [d for d in bag if d.kind.value == DefectKind.SLOT_OVERFLOW.value]
    assert overflow, "Expected at least one SLOT_OVERFLOW defect in DiagnosticBag"
    for d in overflow:
        assert d.severity == NewSev.ERROR, (
            f"Expected ERROR severity in DiagnosticBag for SLOT_OVERFLOW; got {d.severity}"
        )


# ---------------------------------------------------------------------------
# CLI — verify-static command
# ---------------------------------------------------------------------------

def test_cli_verify_static_clean_exits_zero(tmp_path):
    """feinschliff deck verify-static on a clean plan exits 0."""
    import yaml

    plan = _make_plan(
        "end.slide.dsl",
        {
            "pgmeta": "Q1 2026",
            "title": "Thank you",
            "footnote": "Acme Corp",
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(yaml.safe_dump(plan), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "feinschliff.cli", "deck", "verify-static", str(plan_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Expected exit 0 for clean plan; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_cli_verify_static_defects_exits_one(tmp_path):
    """feinschliff deck verify-static on a bad plan exits 1."""
    import yaml

    plan = _make_plan(
        "end.slide.dsl",
        {"title": "", "footer_left": "Corp", "footer_right": "2026"},
    )
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(yaml.safe_dump(plan), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "feinschliff.cli", "deck", "verify-static", str(plan_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, (
        f"Expected exit 1 for defect plan; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_cli_verify_static_json_output(tmp_path):
    """--json flag emits a JSON array of defect dicts."""
    import yaml

    plan = _make_plan(
        "end.slide.dsl",
        {"title": "", "footer_left": "Corp", "footer_right": "2026"},
    )
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(yaml.safe_dump(plan), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli",
            "deck", "verify-static", str(plan_file), "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "kind" in data[0]
    assert "slide_index" in data[0]


# ---------------------------------------------------------------------------
# plan_dir parameter — layout relative to plan file's directory
# ---------------------------------------------------------------------------

def test_plan_dir_resolves_layout_relative_to_plan_file(tmp_path):
    """static_verify(plan_dir=...) finds a layout copied next to the plan file.

    Copies end.slide.dsl into a temp directory alongside a plan.yaml that
    references it as ``layouts/end.slide.dsl``.  Without plan_dir the resolver
    falls back to REPO_ROOT (where the layout also exists, so that would still
    pass), but here we use a layout name that does NOT exist under REPO_ROOT to
    prove the plan_dir path is actually taken.
    """

    # Create a subdirectory that mimics `layouts/` next to the plan
    layouts_dir = tmp_path / "layouts"
    layouts_dir.mkdir()
    src = LAYOUTS_DIR / "end.slide.dsl"
    dst = layouts_dir / "custom_end.slide.dsl"
    dst.write_bytes(src.read_bytes())

    plan = {
        "brand": "feinschliff",
        "out": "deck.pptx",
        "slides": [
            {
                "layout": "layouts/custom_end.slide.dsl",
                "content": {
                    "pgmeta": "Q1 2026",
                    "title": "Thank you",
                    "footnote": "Acme Corp",
                    "footer_left": "Corp",
                    "footer_right": "2026",
                },
            }
        ],
    }

    # Without plan_dir: layout not found under REPO_ROOT (name is custom_end)
    # → no defects but also no overflow checks (slide skipped silently).
    # With plan_dir=tmp_path: layout resolves → clean plan → no defects.
    defects = static_verify(plan, BRAND_DIR, plan_dir=tmp_path)
    assert defects == [], (
        f"Expected no defects when plan_dir resolves a custom layout; got: {defects}"
    )


# ---------------------------------------------------------------------------
# validate() — typed DiagnosticBag entry point
# ---------------------------------------------------------------------------

def _layout_name(layouts_dir: Path) -> str | None:
    """Return the stem of the first bundled layout, or None."""
    f = next(layouts_dir.glob("*.slide.dsl"), None)
    return f.stem if f else None


def test_validate_returns_diagnostic_bag():
    """validate() returns a DiagnosticBag, not a list."""
    name = _layout_name(LAYOUTS_DIR)
    if not name:
        import pytest
        pytest.skip("no bundled layouts")
    plan = _make_plan(f"layouts/{name}.slide.dsl",
                      {"title": "T", "eyebrow": "E", "body": "B"})
    result = validate(plan, BRAND_PACK, plan_dir=REPO_ROOT)
    assert isinstance(result, DiagnosticBag)


def test_validate_accumulates_into_existing_bag():
    """When an existing bag is supplied, validate appends to it and returns it."""
    name = _layout_name(LAYOUTS_DIR)
    if not name:
        import pytest
        pytest.skip("no bundled layouts")
    plan = _make_plan(f"layouts/{name}.slide.dsl", {"title": "T"})
    existing = DiagnosticBag()
    result = validate(plan, BRAND_PACK, existing, plan_dir=REPO_ROOT)
    assert result is existing  # same object returned


def test_validate_defects_have_valid_severity():
    """All defects in the bag have a recognised Severity value."""
    name = _layout_name(LAYOUTS_DIR)
    if not name:
        import pytest
        pytest.skip("no bundled layouts")
    plan = _make_plan(f"layouts/{name}.slide.dsl", {})
    bag = validate(plan, BRAND_PACK, plan_dir=REPO_ROOT)
    assert isinstance(bag, DiagnosticBag)
    for defect in bag:
        assert defect.severity in (Severity.ERROR, Severity.WARNING, Severity.INFO)


# ---------------------------------------------------------------------------
# SLOT_OVERFLOW meta fields — budget_chars and over_by
# ---------------------------------------------------------------------------

def test_slot_overflow_meta_contains_budget_and_over_by():
    """SLOT_OVERFLOW defect meta must carry budget_chars and over_by.

    Task B1 (shorten_slot apply-fix) relies on these fields to compute the
    target character count for in-place trimming.
    """
    from feinschliff.defects import DefectKind

    long_title = (
        "We must urgently restructure our entire go-to-market approach because "
        "enterprise revenue has declined for three consecutive quarters while churn "
        "accelerated faster than new logo acquisition and expansion bookings could offset"
    )
    assert len(long_title) > 168, "test precondition: title must exceed char budget"

    plan = _make_plan(
        "executive-summary.slide.dsl",
        {
            "action_title": long_title,
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    overflow = [d for d in defects if d.kind == DefectKind.SLOT_OVERFLOW]
    assert len(overflow) >= 1, f"Expected ≥1 SLOT_OVERFLOW defect; got: {defects}"

    d = overflow[0]
    assert "budget_chars" in d.meta, (
        f"SLOT_OVERFLOW meta must contain 'budget_chars'; got: {d.meta}"
    )
    assert "over_by" in d.meta, (
        f"SLOT_OVERFLOW meta must contain 'over_by'; got: {d.meta}"
    )
    assert isinstance(d.meta["budget_chars"], int), (
        f"budget_chars must be int; got {type(d.meta['budget_chars'])}"
    )
    assert isinstance(d.meta["over_by"], int), (
        f"over_by must be int; got {type(d.meta['over_by'])}"
    )
    assert d.meta["budget_chars"] > 0, "budget_chars must be positive"
    assert d.meta["over_by"] > 0, (
        f"over_by must be > 0 for an overflowing title; got {d.meta['over_by']}"
    )
    assert d.meta["over_by"] == max(0, len(long_title) - d.meta["budget_chars"]), (
        "over_by must equal max(0, len(value) - budget_chars)"
    )


# ---------------------------------------------------------------------------
# deck build --strict-static integration
# ---------------------------------------------------------------------------

def test_deck_build_strict_static_exits_nonzero_on_bad_plan(tmp_path):
    """deck build --strict-static aborts before render when defects exist."""
    import yaml

    plan = _make_plan(
        "end.slide.dsl",
        {"title": "", "footer_left": "Corp", "footer_right": "2026"},
    )
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(yaml.safe_dump(plan), encoding="utf-8")
    out_pptx = tmp_path / "out.pptx"

    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli",
            "deck", "build", str(plan_file),
            "-o", str(out_pptx),
            "--strict-static",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        f"Expected non-zero exit for --strict-static with defects; "
        f"got {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # The .pptx must NOT have been written (aborted before render).
    assert not out_pptx.exists(), (
        "deck.pptx should NOT be written when --strict-static aborts early"
    )


# ---------------------------------------------------------------------------
# Optional scalar slots — must NOT fire EMPTY_PLACEHOLDER
# ---------------------------------------------------------------------------

def test_optional_slots_dont_fire_empty_placeholder():
    """Well-known optional slots like 'eyebrow', 'so_what', 'pgmeta' must not fire."""
    from feinschliff.defects import DefectKind

    plan = _make_plan(
        "end.slide.dsl",
        {
            "title": "Thank you",
            "footer_left": "Corp",
            "footer_right": "2026",
            # pgmeta, footnote intentionally absent — both are optional
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    ep = [d for d in defects if d.kind == DefectKind.EMPTY_PLACEHOLDER]
    optional_ep = [
        d for d in ep
        if d.meta.get("slot") in ("pgmeta", "eyebrow", "kicker", "so_what",
                                   "footnote", "subtitle", "tracker")
    ]
    assert optional_ep == [], (
        f"Optional slots must not fire EMPTY_PLACEHOLDER; got: {optional_ep}"
    )


# ---------------------------------------------------------------------------
# Structural-array detection (Bug 2 fix)
# ---------------------------------------------------------------------------

def test_structural_array_slot_fires_empty_placeholder():
    """bar-chart.slide.dsl: missing 'bars' array fires EMPTY_PLACEHOLDER.

    The bar-chart layout has rect nodes using {{ bars[N].width*12 }} in
    positional args for sizing math.  When 'bars' is absent from content,
    this causes a render crash.  The structural-array heuristic must flag
    bars[].width* as a required slot so the defect surfaces pre-render.
    """
    from feinschliff.defects import DefectKind

    plan = _make_plan(
        "bar-chart.slide.dsl",
        {
            "action_title": "EV cost remains the top barrier",
            "footer_left": "Corp",
            "footer_right": "2026",
            # 'bars' intentionally absent — simulates the benchmark crash case
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    ep = [d for d in defects if d.kind == DefectKind.EMPTY_PLACEHOLDER]
    bars_ep = [d for d in ep if "bars" in d.meta.get("slot", "")]
    assert len(bars_ep) >= 1, (
        f"Expected ≥1 EMPTY_PLACEHOLDER for missing 'bars[]' structural array; "
        f"got ep defects: {ep}"
    )


def test_content_flexible_array_slot_does_not_fire():
    """agenda.slide.dsl: missing 'items' array does NOT fire EMPTY_PLACEHOLDER.

    The agenda layout interpolates items[] only in kw_args of the agenda-item
    compound call (not in rect/line pos_args), so the array is content-flexible.
    An author who leaves items[] empty gets blank agenda boxes — not a crash.
    """
    from feinschliff.defects import DefectKind

    plan = _make_plan(
        "agenda.slide.dsl",
        {
            "title": "Agenda",
            "footer_left": "Corp",
            "footer_right": "2026",
            # 'items' intentionally absent
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    ep = [d for d in defects if d.kind == DefectKind.EMPTY_PLACEHOLDER]
    items_ep = [d for d in ep if "items" in d.meta.get("slot", "")]
    assert items_ep == [], (
        f"Content-flexible 'items[]' array must NOT fire EMPTY_PLACEHOLDER; "
        f"got: {items_ep}"
    )


# ---------------------------------------------------------------------------
# deck build default static gate — fatal static defects block EVERY build
# ---------------------------------------------------------------------------
#
# Task 9: SLOT_OVERFLOW is FATAL (real font metrics made the predictor
# trustworthy), so an overflowing deck must NOT build by default — no
# --strict-static required. WARN-only results (empty-placeholder) must
# NOT abort a default build; promoting those stays --strict-static's job.

_OVERFLOW_TITLE = (
    "We must urgently restructure our entire go-to-market approach because "
    "enterprise revenue has declined for three consecutive quarters while churn "
    "accelerated faster than new logo acquisition and expansion bookings could offset"
)


def _overflow_plan(out_pptx: Path) -> dict:
    """executive-summary plan whose action_title exceeds its 2-line budget."""
    assert len(_OVERFLOW_TITLE) > 168, "test precondition: title must exceed budget"
    plan = _make_plan(
        "executive-summary.slide.dsl",
        {
            "action_title": _OVERFLOW_TITLE,
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    plan["out"] = str(out_pptx)
    return plan


def _run_deck_build(plan: dict, plan_file: Path, *extra_args: str) -> "subprocess.CompletedProcess":
    import yaml

    plan_file.write_text(yaml.safe_dump(plan, sort_keys=False), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli",
            "deck", "build", str(plan_file),
            *extra_args,
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def test_deck_build_default_aborts_on_slot_overflow(tmp_path):
    """Default `deck build` (no flags) refuses to build an overflowing deck."""
    out_pptx = tmp_path / "out.pptx"
    result = _run_deck_build(
        _overflow_plan(out_pptx), tmp_path / "plan.yaml", "-o", str(out_pptx),
    )
    assert result.returncode != 0, (
        f"Expected non-zero exit for default build of an overflowing deck; "
        f"got {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "slot-overflow" in (result.stderr + result.stdout), (
        f"slot-overflow defect must be reported.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert not out_pptx.exists(), (
        "deck.pptx must NOT be written when the overflow gate aborts"
    )


def test_deck_build_default_gate_not_bypassed_by_skip_content_lint(tmp_path):
    """--skip-content-lint skips content lints, NOT the fatal geometry gate.

    Regression guard for the pre-Task-9 hole: --skip-content-lint used to
    disable the only default-path overflow check, letting overflowing decks
    ship. The static gate is independent of the content lint.
    """
    out_pptx = tmp_path / "out.pptx"
    result = _run_deck_build(
        _overflow_plan(out_pptx), tmp_path / "plan.yaml",
        "-o", str(out_pptx), "--skip-content-lint",
    )
    assert result.returncode != 0, (
        f"Expected non-zero exit: the static overflow gate must run even with "
        f"--skip-content-lint; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "slot-overflow" in (result.stderr + result.stdout)
    assert not out_pptx.exists()


def test_deck_build_default_shortened_text_builds_fine(tmp_path):
    """The same deck with the offending text shortened builds clean (exit 0)."""
    out_pptx = tmp_path / "out.pptx"
    plan = _overflow_plan(out_pptx)
    plan["slides"][0]["content"]["action_title"] = "Enterprise revenue declined three quarters"
    result = _run_deck_build(plan, tmp_path / "plan.yaml", "-o", str(out_pptx))
    assert result.returncode == 0, (
        f"Expected exit 0 for the shortened deck; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert out_pptx.exists(), "deck.pptx must be written for a clean plan"


def test_deck_build_default_warn_only_static_defects_do_not_block(tmp_path):
    """WARN-only static results (empty-placeholder) do NOT abort default builds.

    Same plan that test_deck_build_strict_static_exits_nonzero_on_bad_plan
    uses to prove --strict-static aborts — without the flag it must build.
    """
    out_pptx = tmp_path / "out.pptx"
    plan = _make_plan(
        "end.slide.dsl",
        {"title": "", "footer_left": "Corp", "footer_right": "2026"},
    )
    plan["out"] = str(out_pptx)
    result = _run_deck_build(plan, tmp_path / "plan.yaml", "-o", str(out_pptx))
    assert result.returncode == 0, (
        f"Expected exit 0: empty-placeholder is WARN and must not block a "
        f"default build; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert out_pptx.exists()

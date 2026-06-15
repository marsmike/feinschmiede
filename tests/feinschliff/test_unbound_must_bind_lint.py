"""Unit tests for the 'unbound-must-bind-slot' pre-render content lint.

Verifies that ``check_unbound_must_bind_slots`` and the integrated
``validate_content`` call correctly flag chart slots with ``must_bind:true``
that are absent from the slide content dict.
"""
from __future__ import annotations

import pytest

from feinschliff.content_validator import (
    ContentDefect,
    check_unbound_must_bind_slots,
    validate_content,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _chart_budget(n: int) -> dict:
    """Return a minimal slot_budgets dict for chart N — all must_bind:true."""
    return {
        f"chart_{n}_values": {
            "kind": "list",
            "item_type": "number",
            "capacity": 3,
            "must_bind": True,
            "hint": "Numeric values. MUST override.",
        },
        f"chart_{n}_categories": {
            "kind": "list",
            "item_type": "string",
            "capacity": 3,
            "must_bind": True,
            "hint": "Category labels. MUST override.",
        },
        f"chart_{n}_colors": {
            "kind": "list",
            "item_type": "hex_color",
            "capacity": 3,
            "must_bind": False,
            "hint": "Optional hex colors.",
        },
    }


# ---------------------------------------------------------------------------
# check_unbound_must_bind_slots — direct unit tests
# ---------------------------------------------------------------------------

class TestCheckUnboundMustBindSlots:

    def test_no_budgets_returns_empty(self):
        result = check_unbound_must_bind_slots({}, slot_budgets={}, slide_index=1)
        assert result == []

    def test_no_must_bind_returns_empty(self):
        budgets = {
            "chart_1_colors": {
                "kind": "list",
                "item_type": "hex_color",
                "capacity": 3,
                "must_bind": False,
                "hint": "optional",
            }
        }
        result = check_unbound_must_bind_slots({}, slot_budgets=budgets, slide_index=1)
        assert result == []

    def test_unbound_must_bind_produces_fatal_defect(self):
        budgets = _chart_budget(1)
        ctx: dict = {}  # nothing bound
        defects = check_unbound_must_bind_slots(ctx, slot_budgets=budgets, slide_index=2)

        # Values and categories are must_bind:true → 2 defects; colors is false → 0
        kinds = [d.kind for d in defects]
        assert kinds.count("unbound-must-bind-slot") == 2

    def test_defect_slide_index_is_correct(self):
        budgets = _chart_budget(1)
        defects = check_unbound_must_bind_slots({}, slot_budgets=budgets, slide_index=5)
        assert all(d.slide_index == 5 for d in defects)

    def test_defect_severity_is_fatal(self):
        budgets = _chart_budget(1)
        defects = check_unbound_must_bind_slots({}, slot_budgets=budgets, slide_index=1)
        for d in defects:
            if d.kind == "unbound-must-bind-slot":
                assert d.severity == "fatal"

    def test_bound_values_clears_defect(self):
        budgets = _chart_budget(1)
        ctx = {
            "chart_1_values": [8.2, 3.2, 1.4],
            "chart_1_categories": ["Q1", "Q2", "Q3"],
        }
        defects = check_unbound_must_bind_slots(ctx, slot_budgets=budgets, slide_index=1)
        assert defects == []

    def test_empty_list_binding_counts_as_unbound(self):
        """An empty list is semantically unbound — stock data would still show."""
        budgets = _chart_budget(1)
        ctx = {"chart_1_values": [], "chart_1_categories": []}
        defects = check_unbound_must_bind_slots(ctx, slot_budgets=budgets, slide_index=1)
        kinds = [d.kind for d in defects]
        assert "unbound-must-bind-slot" in kinds

    def test_empty_string_binding_counts_as_unbound(self):
        budgets = _chart_budget(1)
        ctx = {"chart_1_values": "", "chart_1_categories": ""}
        defects = check_unbound_must_bind_slots(ctx, slot_budgets=budgets, slide_index=1)
        kinds = [d.kind for d in defects]
        assert "unbound-must-bind-slot" in kinds

    def test_text_slot_budgets_are_ignored(self):
        """Text slot budgets (chars_per_line style) never trigger must_bind."""
        from feinschliff.slot_budget import SlotBudget
        # A SlotBudget object (not a dict) has no must_bind key → skipped.
        # We test the guard in check_unbound_must_bind_slots: non-dict entries skip.
        budgets: dict = {
            "action_title": {"chars_per_line": 40, "max_lines": 2, "max_chars": 80},
        }
        defects = check_unbound_must_bind_slots({}, slot_budgets=budgets, slide_index=1)
        # "chars_per_line" budgets have no must_bind key → no defects
        assert defects == []

    def test_slot_name_appears_in_defect(self):
        budgets = {
            "chart_1_values": {
                "kind": "list",
                "item_type": "number",
                "capacity": 2,
                "must_bind": True,
                "hint": "x",
            }
        }
        defects = check_unbound_must_bind_slots({}, slot_budgets=budgets, slide_index=1)
        assert len(defects) == 1
        assert "chart_1_values" in defects[0].slot

    def test_multiple_charts_all_flag(self):
        budgets = {**_chart_budget(1), **_chart_budget(2)}
        defects = check_unbound_must_bind_slots({}, slot_budgets=budgets, slide_index=3)
        # 2 charts × 2 must_bind slots each = 4 defects
        assert sum(1 for d in defects if d.kind == "unbound-must-bind-slot") == 4


# ---------------------------------------------------------------------------
# Integration via validate_content
# ---------------------------------------------------------------------------

class TestValidateContentChartSlots:

    def test_validate_content_flags_unbound_chart_slot(self):
        budgets = _chart_budget(1)
        defects = validate_content({}, slide_index=1, slot_budgets=budgets)
        kinds = [d.kind for d in defects]
        assert "unbound-must-bind-slot" in kinds

    def test_validate_content_clean_when_chart_slots_bound(self):
        budgets = _chart_budget(1)
        ctx = {
            "chart_1_values": [10.0, 20.0, 30.0],
            "chart_1_categories": ["Jan", "Feb", "Mar"],
        }
        defects = validate_content(ctx, slide_index=1, slot_budgets=budgets)
        kinds = [d.kind for d in defects]
        assert "unbound-must-bind-slot" not in kinds

    def test_validate_content_without_slot_budgets_no_chart_lint(self):
        """When slot_budgets is not provided, no chart lints fire."""
        defects = validate_content({"chart_1_values": None}, slide_index=1)
        assert defects == []

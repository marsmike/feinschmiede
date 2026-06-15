"""Unit tests for chart slot budget entries in slot_budgets_for_layout.

Tests that ``_chart_slot_budgets_from_nodes`` and ``slot_budgets_for_layout``
emit the correct ``chart_N_*`` slot entries when a layout DSL body contains
``native`` lines carrying ``chart_categories`` / ``chart_values`` / ``chart_colors``
kw-args (as produced by ``slotify_native_charts``).
"""
from __future__ import annotations

import base64
import json

import pytest

from feinschliff.deck.orchestrate import _chart_slot_budgets_from_nodes
from feinschliff.dsl.parser import DSLNode


def _b64(obj) -> str:
    return base64.b64encode(json.dumps(obj).encode()).decode("ascii")


def _jinja_default(slot_name: str, default_list) -> str:
    """Reproduce the Jinja template string slotify_native_charts emits."""
    b64 = _b64(default_list)
    return f"{{{{ {slot_name} | default('{b64}') }}}}"


def _native_chart_node(n: int, categories, values, colors) -> DSLNode:
    """Build a DSLNode that mimics a slotified native chart line."""
    return DSLNode(
        kind="native",
        pos_args=["graphicN"],
        kw_args={
            "b64": "FAKEB64==",
            "parts_file": f"native/chart{n}.json",
            "chart_categories": _jinja_default(f"chart_{n}_categories", categories),
            "chart_values": _jinja_default(f"chart_{n}_values", values),
            "chart_colors": _jinja_default(f"chart_{n}_colors", colors),
        },
        line_no=10,
    )


# ---------------------------------------------------------------------------
# _chart_slot_budgets_from_nodes — unit tests
# ---------------------------------------------------------------------------

class TestChartSlotBudgetsFromNodes:

    def test_no_native_nodes_returns_empty(self):
        nodes = [
            DSLNode(kind="text", pos_args=["title"], kw_args={}, line_no=1),
        ]
        result = _chart_slot_budgets_from_nodes(nodes)
        assert result == {}

    def test_native_without_chart_kwargs_is_ignored(self):
        node = DSLNode(
            kind="native",
            pos_args=["g1"],
            kw_args={"b64": "ABC", "parts_file": "x.json"},
            line_no=5,
        )
        assert _chart_slot_budgets_from_nodes([node]) == {}

    def test_single_chart_emits_three_slots(self):
        cats = ["Q1", "Q2", "Q3"]
        vals = [8.2, 3.2, 1.4]
        cols = ["FF6840", "FF8666", "FFA38C"]
        node = _native_chart_node(1, cats, vals, cols)
        result = _chart_slot_budgets_from_nodes([node])

        assert set(result.keys()) == {
            "chart_1_values", "chart_1_categories", "chart_1_colors"
        }

    def test_chart_1_values_slot_shape(self):
        cats = ["Q1", "Q2"]
        vals = [8.2, 3.2]
        cols = ["", ""]
        node = _native_chart_node(1, cats, vals, cols)
        result = _chart_slot_budgets_from_nodes([node])

        v = result["chart_1_values"]
        assert v["kind"] == "list"
        assert v["item_type"] == "number"
        assert v["capacity"] == 2
        assert v["must_bind"] is True
        assert "Baked default" in v["hint"]

    def test_chart_1_categories_slot_shape(self):
        cats = ["Category 1", "Category 2", "Category 3"]
        vals = [1.0, 2.0, 3.0]
        cols = ["", "", ""]
        node = _native_chart_node(1, cats, vals, cols)
        result = _chart_slot_budgets_from_nodes([node])

        c = result["chart_1_categories"]
        assert c["kind"] == "list"
        assert c["item_type"] == "string"
        assert c["capacity"] == 3
        assert c["must_bind"] is True

    def test_chart_1_colors_must_bind_false(self):
        node = _native_chart_node(1, ["A", "B"], [1.0, 2.0], ["", ""])
        result = _chart_slot_budgets_from_nodes([node])

        col = result["chart_1_colors"]
        assert col["must_bind"] is False

    def test_capacity_matches_list_length(self):
        cats = ["Jan", "Feb", "Mar", "Apr", "May"]
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        cols = ["", "", "", "", ""]
        node = _native_chart_node(1, cats, vals, cols)
        result = _chart_slot_budgets_from_nodes([node])

        assert result["chart_1_categories"]["capacity"] == 5
        assert result["chart_1_values"]["capacity"] == 5
        assert result["chart_1_colors"]["capacity"] == 5

    def test_two_charts_emit_six_slots(self):
        n1 = _native_chart_node(1, ["Q1", "Q2"], [8.2, 3.2], ["", ""])
        n2 = _native_chart_node(2, ["A", "B", "C"], [1.0, 2.0, 3.0], ["", "", ""])
        result = _chart_slot_budgets_from_nodes([n1, n2])

        assert "chart_1_values" in result
        assert "chart_1_categories" in result
        assert "chart_1_colors" in result
        assert "chart_2_values" in result
        assert "chart_2_categories" in result
        assert "chart_2_colors" in result

    def test_counter_is_per_node_monotonic(self):
        n1 = _native_chart_node(1, ["Q1"], [8.2], [""])
        n2 = _native_chart_node(2, ["Q1", "Q2"], [1.0, 2.0], ["", ""])
        # The function ignores the N in kw_args; it uses its own counter.
        result = _chart_slot_budgets_from_nodes([n1, n2])
        # Both chart_1 and chart_2 should exist (from the counter, not the kw N).
        assert "chart_1_values" in result
        assert "chart_2_values" in result

    def test_non_native_nodes_are_skipped(self):
        nodes = [
            DSLNode(kind="text", pos_args=[], kw_args={"label": "title"}, line_no=1),
            DSLNode(kind="picture", pos_args=[], kw_args={}, line_no=2),
            _native_chart_node(1, ["A"], [1.0], [""]),
        ]
        result = _chart_slot_budgets_from_nodes(nodes)
        assert list(result.keys()) == [
            "chart_1_values", "chart_1_categories", "chart_1_colors"
        ]

    def test_empty_list_capacity_is_zero(self):
        """An empty base64 list (e.g. W10= = '[]') gives capacity 0."""
        cats = []
        vals = [8.2, 3.2]
        cols = []
        node = _native_chart_node(1, cats, vals, cols)
        result = _chart_slot_budgets_from_nodes([node])
        assert result["chart_1_categories"]["capacity"] == 0
        assert result["chart_1_values"]["capacity"] == 2

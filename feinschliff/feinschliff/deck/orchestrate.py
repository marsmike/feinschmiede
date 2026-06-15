"""Deck orchestration helpers extracted from cli/deck.py.

Business-logic functions that are independently testable and reusable outside
the CLI:

- :func:`signals_from_slide` — extract layout-picker signals from a
  content-plan slide entry.
- :func:`patch_set_hash` — stable hash of an autofix patch set for
  oscillation detection.

DSL-era functions (build_primitives_for_layout, build_refurbished_deck,
compose_from_brief, slot_budgets_for_layout, resolve_layout_path) have been
removed with the DSL pipeline. The master-template renderer
(``feinschliff render-master`` / ``feinschmiede.master_template``) replaces
the DSL build path.

``cli/deck.py`` delegates to these functions; callers outside the CLI
can import them directly.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# ── constants ─────────────────────────────────────────────────────────────────

# Maps `diagram_kind` hints from content_plan into the layout picker's
# preferred role.
DIAGRAM_KIND_TO_ROLE: dict[str, str] = {
    "concept": "content-with-visual",
    "chart":   "data-quantity",
    "process": "data-timeline",
    "compare": "data-comparison",
}


# ── patch_set_hash ────────────────────────────────────────────────────────────

def patch_set_hash(patches: list) -> str:
    """Stable hash of an autofix patch set — used for oscillation detection.

    Two cycles that would apply identical changes produce the same hash so the
    autofix loop can detect oscillation and halt before wasting iterations.
    """
    items = sorted(
        (p.slide_index, p.action, str(sorted((p.payload or {}).items())))
        for p in patches
    )
    return hashlib.sha256(repr(items).encode()).hexdigest()


# ── _slot_lengths_from_slide ──────────────────────────────────────────────────

def _slot_lengths_from_slide(slide: dict[str, Any]) -> dict[str, int]:
    """Derive a conservative slot-name → char-count mapping from a content-plan slide.

    Only maps fields whose names correspond 1:1 to canonical slot names used
    in layout frontmatter and slot-binding code (see
    ``feinschliff.deck.content_metadata.warn_overbudget_slots``).  Unmapped
    fields are silently ignored — a sparse result is correct; overcounting
    would penalise layouts that aren't actually over-budget.

    Current mappings:
        ``title``    → ``"title"`` slot   (present in nearly every layout)
        ``subtitle`` → ``"subtitle"`` slot (declared in layouts that have one)
    """
    out: dict[str, int] = {}
    title = slide.get("title")
    if isinstance(title, str) and title:
        out["title"] = len(title)
    subtitle = slide.get("subtitle")
    if isinstance(subtitle, str) and subtitle:
        out["subtitle"] = len(subtitle)
    return out


# ── signals_from_slide ────────────────────────────────────────────────────────

def signals_from_slide(slide: dict[str, Any]) -> dict[str, Any]:
    """Extract layout-picker / layout-budget kwargs from a content-plan slide.

    Centralised here so per-slide and deck-wide pickers agree on which
    fields feed selection.

    Parameters
    ----------
    slide:
        A single entry from the ``slides`` list of a content plan.

    Returns
    -------
    dict
        Keyword-argument dict accepted by :func:`feinschliff.layout_picker.pick_layout`,
        plus an optional ``layout`` pin passthrough consumed by
        :func:`feinschliff.layout_budget.plan_deck_layouts` (an explicitly
        pinned slide bypasses the picker — and any deck-map default).
    """
    role = slide.get("role") or slide.get("purpose") or (
        DIAGRAM_KIND_TO_ROLE.get(str(slide.get("diagram_kind") or ""))
        or "content-columns"
    )
    # slot_lengths: prefer an explicitly provided dict; fall back to the
    # conservative field→slot derivation so callers don't need to pre-compute.
    explicit_lengths = slide.get("slot_lengths")
    slot_lengths: dict[str, int] | None = (
        explicit_lengths
        if isinstance(explicit_lengths, dict) and explicit_lengths
        else (_slot_lengths_from_slide(slide) or None)
    )
    return {
        "role":            role,
        "concept_count":   slide.get("concept_count"),
        "data_quantity":   slide.get("data_quantity"),
        "comparison":      slide.get("comparison"),
        "narrative_role":  slide.get("narrative_role"),
        "narrative_act":   slide.get("narrative_act"),
        "time_axis_role":  slide.get("time_axis_role"),
        "audience_mode":   slide.get("audience_mode"),
        "diagram_kind":       slide.get("diagram_kind"),
        "diagram_complexity": slide.get("diagram_complexity"),
        "layout":             slide.get("layout"),
        "slot_lengths":       slot_lengths,
    }


# ── resolve_layout_path ───────────────────────────────────────────────────────

def resolve_layout_path(brand_root: Path, layout_name: str) -> Path | None:
    """Return the layout path for *layout_name*.

    Checks brand-local ``layouts/`` first, then sibling brand-prefixed paths,
    then falls through to the stub ``layout_discovery.find_layout`` (which
    always returns None in the master-template era — kept for test monkeypatching
    compatibility).
    """
    from feinschliff import layout_discovery

    brand_local = brand_root / "layouts" / f"{layout_name}.slide.dsl"
    if brand_local.is_file():
        return brand_local
    cross = layout_discovery.resolve_brand_prefixed(brand_root, layout_name)
    if cross is not None:
        return cross
    found = layout_discovery.find_layout(layout_name)
    return found.path if found is not None else None


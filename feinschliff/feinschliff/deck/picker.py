"""LayoutPicker — OO wrapper around :func:`feinschliff.layout_picker.pick_layout`.

Provides a class-based interface for layout selection, keeping the existing
:func:`~feinschliff.layout_picker.pick_layout` function as the scoring engine.

Usage::

    from feinschmiede.brand.pack import BrandPack
    from feinschliff.deck.picker import LayoutPicker, LayoutMatch

    pack = BrandPack.load(Path("brands/feinschliff"))
    picker = LayoutPicker(brand=pack)

    match = picker.pick({"role": "content-columns", "concept_count": 3})
    print(match.layout_name, match.score, match.reason)

    candidates = picker.candidates({"role": "data-timeline"})
    for c in candidates:
        print(c.layout_name, c.score, c.reason)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from feinschliff import layout_discovery
from feinschliff.deck.content_metadata import (
    apply_deck_map_bonus,
    deck_map_layouts_for_role,
    load_deck_map,
)
from feinschliff.layout_picker import pick_layout

# How many candidates to fetch from `pick_layout` when a deck-map default
# exists for the slide's role, so the deck-map layout is visible to the
# re-rank even when the caller asked for a small top_k. Matches the
# budget planner's `_CANDIDATE_WINDOW` rationale (largest role bucket
# plus headroom).
_DECK_MAP_WINDOW = 20


# ── layout discovery (was BrandPack.find_layout / .layout_table) ──────────────
#
# These helpers used to live on ``feinschmiede.brand.pack.BrandPack`` but pulled
# in office-side ``feinschliff.layout_discovery`` — an engine→office back-edge.
# They now live here, on the office side, reading the brand's local
# ``layouts_path`` and overlaying it onto toolkit discovery (brand-local wins).
# Calls go through the ``layout_discovery`` module (not bound names) so tests
# can monkeypatch ``feinschliff.layout_discovery.find_layout``.

def _resolve_layout_path(layouts_path: Path | None, name: str) -> Path | None:
    """Brand-local ``layouts/`` wins over toolkit discovery; else None.

    A ``<brand>-<stem>`` name is also resolved against sibling brand packs
    under the same ``brands/`` parent (see
    :func:`feinschliff.layout_discovery.resolve_brand_prefixed`), so plans
    can address a specific brand's layout unambiguously when two packs
    ship the same stem (e.g. ``acme-slide-25`` vs ``globex-slide-25``).
    """
    if layouts_path is not None:
        candidate = layouts_path / f"{name}.slide.dsl"
        if candidate.is_file():
            return candidate
        cross = layout_discovery.resolve_brand_prefixed(layouts_path.parent, name)
        if cross is not None:
            return cross
    found = layout_discovery.find_layout(name)
    if found is not None:
        return found.path
    return None


def _brand_layout_table(layouts_path: Path | None) -> dict[str, Path]:
    """Layout pool for picker scoring.

    When the brand ships a non-empty ``layouts/`` directory (brand-owned
    layouts), the pool contains ONLY those brand-local layouts — toolkit
    overlay layouts are excluded. This structural enforcement prevents
    brand-chrome leaks: the content-assembly LLM cannot accidentally pick
    a toolkit layout when the brand owns its full layout vocabulary.

    When ``layouts_path`` is None or empty (no brand-local layouts), the
    pool is empty. Each brand owns its full layout vocabulary; port DSL
    templates manually when a brand needs a layout from the toolkit.
    """
    suffix = ".slide.dsl"
    if layouts_path is not None:
        brand_local = {
            candidate.name[: -len(suffix)]: candidate
            for candidate in sorted(layouts_path.glob(f"*{suffix}"))
        }
        if brand_local:
            # Non-empty brand layouts/ → brand-owned pool only.
            return brand_local
    # No brand-local layouts (or empty layouts/) → empty pool.
    # Each brand owns its layout vocabulary; copy/port DSL templates manually
    # when a brand needs layouts from the toolkit.
    return {}


# ── LayoutMatch ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LayoutMatch:
    """A single layout candidate returned by :class:`LayoutPicker`.

    Attributes
    ----------
    layout_name:
        The bare layout identifier, e.g. ``"title-orange"``.
    layout_path:
        Full path to the ``*.slide.dsl`` file, or ``None`` when the
        layout hasn't been resolved against a brand root yet.
    score:
        Numeric affinity score (higher is better).
    reason:
        Human-readable rationale string listing the signals that
        contributed to the score.
    """
    layout_name: str
    layout_path: Path | None
    score: float
    reason: str


# ── LayoutPicker ─────────────────────────────────────────────────────────────

class LayoutPicker:
    """Typed layout picker backed by :func:`feinschliff.layout_picker.pick_layout`.

    Parameters
    ----------
    brand:
        The :class:`~feinschmiede.brand.pack.BrandPack` whose layout pool is
        searched when resolving :attr:`LayoutMatch.layout_path`.  When
        ``None``, ``layout_path`` in returned matches will also be ``None``.
    top_k:
        Default number of candidates returned by :meth:`candidates`.
    """

    def __init__(self, brand: Any = None, *, top_k: int = 3) -> None:
        self.brand = brand
        self.top_k = top_k
        self._profile_table_cache: dict[str, dict] | None = None
        self._deck_map_cache: dict | None = None
        self._deck_map_loaded = False

    # ── helpers ───────────────────────────────────────────────────────────

    def _profile_table(self) -> dict[str, dict] | None:
        """Affinity profiles for this brand's full layout universe.

        Built from the brand's layout table (toolkit ∪ brand overrides ∪
        brand-only layouts) so brand-only layouts are *ranked*, not merely
        resolvable by name. Cached per instance. Returns ``None`` when there
        is no brand — :func:`pick_layout` then falls back to its cached
        toolkit-only default table.
        """
        if self.brand is None:
            return None
        if self._profile_table_cache is None:
            from feinschliff.layout_profile import build_profile_table

            self._profile_table_cache = build_profile_table(
                _brand_layout_table(self.brand.layouts_path), strict=False
            )
        return self._profile_table_cache

    def _deck_map(self) -> dict | None:
        """The brand's ``deck-map.yaml`` role→layout table, loaded lazily.

        ``None`` when there is no brand or the brand ships no deck-map.
        """
        if self.brand is None:
            return None
        if not self._deck_map_loaded:
            self._deck_map_loaded = True
            self._deck_map_cache = load_deck_map(self.brand)
        return self._deck_map_cache

    def _resolve_path(self, layout_name: str) -> Path | None:
        """Return the filesystem path for *layout_name*.

        Checks the brand's local layouts first, then the toolkit pool.
        Returns ``None`` when not found anywhere.
        """
        if self.brand is None:
            return None
        # Brand-local layouts/ first, then the toolkit pool.
        return _resolve_layout_path(self.brand.layouts_path, layout_name)

    @staticmethod
    def _to_match(candidate: dict, layout_path: Path | None) -> LayoutMatch:
        reason_raw = candidate.get("rationale") or ["—"]
        if isinstance(reason_raw, list):
            reason = ", ".join(reason_raw)
        else:
            reason = str(reason_raw)
        return LayoutMatch(
            layout_name=candidate["layout"],
            layout_path=layout_path,
            score=float(candidate.get("score", 0.0)),
            reason=reason,
        )

    # ── public API ────────────────────────────────────────────────────────

    def candidates(
        self,
        slot_hint: dict[str, Any],
        *,
        top_k: int | None = None,
    ) -> list[LayoutMatch]:
        """Return up to *top_k* ranked :class:`LayoutMatch` instances.

        *slot_hint* is the same signal dict accepted by
        :func:`feinschliff.layout_picker.pick_layout`:

        .. code-block:: python

            {
                "role": "content-columns",
                "concept_count": 3,
                "data_quantity": None,
                "comparison": False,
                "narrative_role": "so-what",
                "narrative_act": "resolution",
                "time_axis_role": None,
                "audience_mode": "presentation",
                "diagram_kind": None,
                "diagram_complexity": None,
                "layout_history": ["title-orange", "two-column-cards"],
            }
        """
        k = top_k if top_k is not None else self.top_k
        # Deck-map default: when the brand's deck-map.yaml names a layout
        # for this slide's role (cover / agenda / section / quote / closer),
        # fetch a wider window so the deck-map layout is visible, then
        # re-rank with the additive bonus. NOT a hard override — explicit
        # `layout:` pins bypass the picker, and when_not_to_use / the
        # fixed-chrome guard can still sink the layout.
        deck_map = self._deck_map()
        role = slot_hint.get("role")
        has_deck_map_default = bool(deck_map_layouts_for_role(deck_map, role))
        fetch_k = max(k, _DECK_MAP_WINDOW) if has_deck_map_default else k
        raw = pick_layout(
            role=slot_hint.get("role"),
            concept_count=slot_hint.get("concept_count"),
            data_quantity=slot_hint.get("data_quantity"),
            comparison=slot_hint.get("comparison"),
            narrative_role=slot_hint.get("narrative_role"),
            narrative_act=slot_hint.get("narrative_act"),
            time_axis_role=slot_hint.get("time_axis_role"),
            audience_mode=slot_hint.get("audience_mode"),
            diagram_kind=slot_hint.get("diagram_kind"),
            diagram_complexity=slot_hint.get("diagram_complexity"),
            layout_history=slot_hint.get("layout_history"),
            slot_lengths=slot_hint.get("slot_lengths"),
            predecessor=slot_hint.get("predecessor"),
            top_k=fetch_k,
            profiles=self._profile_table(),
        )
        if has_deck_map_default:
            raw = apply_deck_map_bonus(raw, role=role, deck_map=deck_map)[:k]
        return [
            self._to_match(c, self._resolve_path(c["layout"]))
            for c in raw
        ]

    def pick(self, slot_hint: dict[str, Any]) -> LayoutMatch:
        """Return the best :class:`LayoutMatch` for *slot_hint*.

        Equivalent to ``candidates(slot_hint, top_k=1)[0]``.

        Raises :exc:`ValueError` when no layout scores positively (rare —
        usually indicates a badly-formed slot_hint without a valid ``role``).
        """
        candidates = self.candidates(slot_hint, top_k=1)
        if not candidates:
            raise ValueError(
                f"LayoutPicker.pick: no layout matched signals {slot_hint!r}"
            )
        return candidates[0]

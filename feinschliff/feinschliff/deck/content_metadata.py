"""Brand-layout content-metadata consumption for the deck pipeline.

Decompiled brand packs ship planning metadata next to their layouts:

- ``<brand>/deck-map.yaml`` — names the pack's cover / agenda / section /
  quote / closer layouts (written by the builder's ``slotify`` CLI).
- Per-layout frontmatter ``slots:`` — per-slot ``role`` (title / body /
  footer / page-number / eyebrow / source-note / image), ``chars``, and
  for image slots ``class: keep|replace``; plus a top-level
  ``image_queries`` slot → provider-query hint map.

This module is what makes the pipeline consume that metadata
*autonomously* (deterministic code, not planning-LLM prose):

- :func:`load_deck_map` + :func:`apply_deck_map_bonus` — the deck-map
  roles become rank-1 **defaults** at the picker call sites
  (:class:`feinschliff.deck.picker.LayoutPicker` and
  :func:`feinschliff.layout_budget.plan_deck_layouts`). The bonus is
  additive (+4, rationale ``deck-map``), never a hard override — a
  ``when_not_to_use`` hit or the fixed-chrome guard can still sink the
  layout, and an explicit ``layout:`` pin bypasses the picker entirely.
- :func:`auto_bind_slots` — at ``deck build`` time, ``footer`` slots
  auto-bind from the plan's deck-level ``vars:`` (``footer_left`` →
  leftmost footer slot, ``footer_right`` → rightmost; a single footer
  slot takes ``footer_right``), ``page-number`` slots bind the slide's
  1-based index, and unbound ``class: replace`` image slots get a
  provider query derived from the slide's bound title/body text (falling
  back to the frontmatter ``image_queries`` hint). Explicit plan
  bindings — including an explicit ``""`` — always win; ``class: keep``
  slots are never auto-bound; image queries are only bound when an image
  provider is configured (otherwise the slot stays unbound so the
  template default / gem fallback applies instead of a dead path).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# Reuses the slot-extraction regex logic of the budget walker so both agree
# on what counts as "the text node rendering slot X".
from feinschliff.slot_budget import _extract_single_slot

# ── deck-map (Feature: skeleton picks) ───────────────────────────────────────

# Slide role (picker signal) → deck-map key. The framing moments
# (cover / agenda / section / quote / closer) map to single-purpose
# keys. Every other role (`content-columns`, `content-narrative`,
# `data-timeline`, etc.) falls back to the deck-map's `content` list
# inside `deck_map_layouts_for_role` — a brand pack that curates its
# content vocabulary deserves the same bias as one that pins its cover,
# otherwise a toolkit affinity score silently outranks the brand's own
# layouts. (Corporate / auto-decompiled packs typically hit this because
# their per-layout affinity profiles are weaker than the toolkit's
# hand-crafted ones.)
_ROLE_TO_DECK_MAP_KEY: dict[str, str] = {
    "title-primary":  "cover",
    "agenda":         "agenda",
    "chapter-opener": "section",
    "quote":          "quote",
    "closer":         "closer",
}
_CONTENT_FALLBACK_KEY = "content"

# Additive rank bonus for the deck-map default. +4 outranks the +3 role
# match (so the brand's own cover beats a generic toolkit title layout on
# an otherwise-equal race) but stays additive — `when_not_to_use` hits
# (-3 each) and the fixed-chrome guard (-6) can still sink the layout.
DECK_MAP_BONUS = 4.0


def load_deck_map(brand: Any) -> dict | None:
    """Read ``<brand>/deck-map.yaml`` and return it as a dict, or ``None``.

    *brand* may be a :class:`~feinschmiede.brand.BrandPack` (or anything with
    a ``root`` attribute) or a plain :class:`~pathlib.Path` to the brand
    directory. Tolerant by design: a missing, unreadable, or non-mapping
    file returns ``None`` — the deck-map is an optional planning hint,
    never a build-breaker.
    """
    # NB: plain Paths must short-circuit — `Path.root` is the filesystem
    # root attribute ("/"), not the brand directory.
    if isinstance(brand, (str, Path)):
        root = brand
    else:
        root = getattr(brand, "root", None)
    if root is None:
        return None
    try:
        path = Path(root) / "deck-map.yaml"
        if not path.is_file():
            return None
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (TypeError, OSError, yaml.YAMLError):
        return None
    return raw if isinstance(raw, dict) and raw else None


def deck_map_layouts_for_role(deck_map: dict | None, role: str | None) -> list[str]:
    """Layout names the deck-map declares for *role* (possibly empty).

    ``cover`` / ``agenda`` / ``quote`` / ``closer`` are single names;
    ``section`` is a list (a pack may ship several dividers). Any role
    outside the framing-moments map falls back to the deck-map's
    ``content`` list — content roles (``content-columns``,
    ``content-narrative``, ``data-timeline``, etc.) inherit the brand's
    curated content vocabulary. Mistyped entries are dropped
    (type-or-ignore, like the frontmatter metadata).
    """
    if not deck_map or not role:
        return []
    # Picker signal names (`title-primary`) → explicit deck-map keys.
    # Otherwise: if the role itself matches a deck-map key (the planner
    # emits literal `cover` / `closer`), use it. Else fall back to the
    # brand's curated `content` list.
    key = _ROLE_TO_DECK_MAP_KEY.get(role)
    if key is None:
        key = role if role in deck_map else _CONTENT_FALLBACK_KEY
    val = deck_map.get(key)
    if isinstance(val, str) and val:
        return [val]
    if isinstance(val, list):
        return [v for v in val if isinstance(v, str) and v]
    return []


def apply_deck_map_bonus(
    candidates: list[dict],
    *,
    role: str | None,
    deck_map: dict | None,
    bonus: float = DECK_MAP_BONUS,
) -> list[dict]:
    """Re-rank picker *candidates* with the deck-map default bonus.

    Candidates whose layout the deck-map names for *role* gain *bonus*
    points and a ``deck-map`` rationale entry; the list is re-sorted with
    the picker's tiebreak (score desc, layout name asc). Input dicts are
    not mutated. When the deck-map has no entry for *role*, the list is
    returned unchanged.
    """
    target_list = deck_map_layouts_for_role(deck_map, role)
    targets = set(target_list)
    if not targets:
        return candidates
    out: list[dict] = []
    matched: set[str] = set()
    for cand in candidates:
        if cand["layout"] in targets:
            cand = dict(cand)
            cand["score"] = cand["score"] + bonus
            cand["rationale"] = [*(cand.get("rationale") or []), "deck-map"]
            matched.add(cand["layout"])
        out.append(cand)
    # When pick_layout's affinity window misses a deck-map target (auto-
    # generated brand layouts often have weak role profiles and fall
    # outside the top-K), synthesize a candidate so the brand's curated
    # choice still wins on the +bonus alone. Order preserves deck-map list
    # order so callers see deterministic insertion.
    for name in target_list:
        if name not in matched:
            out.append({
                "layout":    name,
                "score":     bonus,
                "rationale": ["deck-map"],
            })
    out.sort(key=lambda c: (-c["score"], c["layout"]))
    return out


# ── slot auto-binding (deck build) ───────────────────────────────────────────

# Word filter for derived image queries: letter runs only (no digits),
# minimum 3 chars, minus high-frequency function words that survive the
# length cut.
_QUERY_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_QUERY_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "into", "onto", "over", "that",
    "this", "these", "those", "are", "was", "were", "will", "has", "have",
    "had", "how", "why", "what", "when", "where", "who", "not", "all",
    "per", "our", "your", "their", "its", "you",
})
_QUERY_MAX_WORDS = 6


def _derive_query(text: str, *, limit: int = _QUERY_MAX_WORDS) -> str:
    """First ~*limit* significant words of *text*, lowercased, or ``""``."""
    words = [
        w.lower() for w in _QUERY_WORD_RE.findall(text)
        if len(w) >= 3 and w.lower() not in _QUERY_STOPWORDS
    ]
    return " ".join(words[:limit])


def _query_from_bound_content(ctx: dict, slots: dict) -> str | None:
    """Derive a provider query from the slide's bound title (else body) text."""
    for wanted in ("title", "body"):
        for name, meta in slots.items():
            if not isinstance(meta, dict) or meta.get("role") != wanted:
                continue
            value = ctx.get(name)
            if not isinstance(value, str):
                continue
            query = _derive_query(value)
            if query:
                return query
    return None


def _slot_x_positions(layout_nodes: Any) -> dict[str, float]:
    """Map slot name → x of the text node rendering it (design px).

    Used to order multiple footer slots left-to-right. Slots whose node
    geometry can't be read sort last, keeping their declaration order.
    """
    xs: dict[str, float] = {}
    for node in layout_nodes or ():
        if getattr(node, "kind", None) != "text" or not node.label or not node.pos_args:
            continue
        slot = _extract_single_slot(node.label)
        if slot is None or slot in xs:
            continue
        try:
            xs[slot] = float(str(node.pos_args[0]).split(",", 1)[0])
        except ValueError:
            continue
    return xs


def auto_bind_slots(
    ctx: dict,
    *,
    layout_path: Path,
    layout_nodes: Any = None,
    slide_index: int,
    deck_vars: dict | None = None,
    image_provider_available: bool = False,
) -> dict:
    """Return *ctx* augmented with auto-bound slot values.

    Reads the layout's frontmatter ``slots:`` metadata (via
    :func:`feinschliff.layout_profile.load_profile`) and binds:

    - ``role: footer`` slots from deck-level vars — ``footer_left`` →
      leftmost footer slot (by the rendering text node's x), ``footer_right``
      → rightmost; a single footer slot takes ``footer_right``. A
      slide-level ctx var of the same name overrides the deck-level one.
    - ``role: page-number`` slots → the slide's 1-based index.
    - ``role: image`` slots with ``class: replace`` → a provider query
      derived from the slide's bound title/body text, falling back to the
      frontmatter ``image_queries`` hint — only when
      *image_provider_available* (an unresolvable bound path would 404
      without a provider; unbound keeps the template default).

    A slot already present in *ctx* — even bound to ``""`` — is never
    touched. Layouts without a frontmatter profile or without ``slots:``
    metadata return *ctx* unchanged.
    """
    from feinschliff.layout_profile import ProfileError, load_profile

    try:
        profile = load_profile(Path(layout_path))
    except (ProfileError, OSError):
        return ctx
    slots = profile.get("slots")
    if not isinstance(slots, dict) or not slots:
        return ctx

    deck_vars = deck_vars if isinstance(deck_vars, dict) else {}
    out = dict(ctx)

    def _bind(slot: str, value: Any) -> None:
        # Explicit plan/ctx binding wins — including an explicit "".
        if value is None or slot in out:
            return
        out[slot] = value

    # footer_left / footer_right → footer slots, ordered left-to-right.
    footers = [
        n for n, m in slots.items()
        if isinstance(m, dict) and m.get("role") == "footer"
    ]
    if footers:
        xs = _slot_x_positions(layout_nodes)
        footers.sort(key=lambda n: xs.get(n, float("inf")))
        left = out.get("footer_left", deck_vars.get("footer_left"))
        right = out.get("footer_right", deck_vars.get("footer_right"))
        if len(footers) == 1:
            _bind(footers[0], right)
        else:
            _bind(footers[0], left)
            _bind(footers[-1], right)

    # page-number slots → 1-based slide index.
    for name, meta in slots.items():
        if isinstance(meta, dict) and meta.get("role") == "page-number":
            _bind(name, str(slide_index))

    # `class: replace` image slots → derived provider query. `keep` (and
    # unclassified) slots are never auto-bound; without a provider the
    # slot stays unbound so the template default / gem fallback applies.
    if image_provider_available:
        queries = profile.get("image_queries")
        queries = queries if isinstance(queries, dict) else {}
        derived = _query_from_bound_content(out, slots)
        for name, meta in slots.items():
            if not isinstance(meta, dict) or meta.get("role") != "image":
                continue
            if meta.get("class") != "replace":
                continue
            hint = queries.get(name)
            query = derived or (hint if isinstance(hint, str) and hint else None)
            _bind(name, query)

    return out


def warn_overbudget_slots(ctx: dict, *, layout_path, slide_index: int) -> None:
    """Cheap pre-gate: compare bound slot lengths against the layout's
    front-matter `chars` budgets and print an OVERBUDGET warning per breach.
    Advisory only — the authoritative check is the textfit overflow gate."""
    import sys
    from pathlib import Path

    from feinschliff.layout_profile import ProfileError, load_profile

    try:
        profile = load_profile(Path(layout_path))
    except (ProfileError, OSError):
        return
    for name, meta in (profile.get("slots") or {}).items():
        chars = meta.get("chars") if isinstance(meta, dict) else None
        value = ctx.get(name)
        if (isinstance(chars, int) and chars > 0
                and isinstance(value, str) and len(value) > chars):
            print(
                f"deck build: WARN: OVERBUDGET slot={name} bound={len(value)} "
                f"chars budget={chars} (slide {slide_index})",
                file=sys.stderr,
            )

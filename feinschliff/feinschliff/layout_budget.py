"""Two-pass deck layout planning with a usage budget.

The default `pick_layout()` scores one slide at a time. Once a layout
wins on raw affinity, it tends to win every comparable slide in the
deck — so a 6-slide section of three-column content keeps picking the
same two or three layouts even though eight are eligible.

This module adds a second pass that walks the deck in order and
re-ranks `pick_layout` candidates with a *usage-budget bonus*: layouts
that haven't been used yet get a +1.5 bump; ones used once get +0.75;
twice → +0.5; etc. The bonus is comparable in scale to existing
affinity components, so it flips ties and near-ties toward under-used
layouts but never overrides a clearly stronger candidate.

The bonus is intentionally inert for "singleton" layouts that appear at
most once per deck (cover, agenda, end) — nothing competes with them,
so reweighting only adds noise. Consecutive-repetition is still
discouraged by `pick_layout`'s own `layout_history` penalty; this
module is about *deck-wide* coverage, not adjacent-slide variety.
"""

from __future__ import annotations

from collections import Counter

from feinschliff.layout_picker import pick_layout

# Maximum bonus a never-used layout receives. Calibrated against the
# affinity weights in `feinschliff.layout_picker.pick_layout` (canonical source
# of all scoring components — role / concept / data / narrative /
# comparison / audience / narrative_act / time_axis_role / diagram_kind
# / diagram_complexity / when_not_to_use). A +1.5 bonus is large enough
# to flip a tied or near-tied race between two compatible candidates,
# but smaller than the +3 role-match weight so a clearly mismatched
# layout never wins on bonus alone.
_MAX_BUDGET_BONUS = 1.5

# Layouts that appear at most once per deck. Reweighting them adds no
# coverage benefit (nothing else competes), and could in pathological
# cases push the picker away from a structural choice the deck needs.
#
# Related but distinct from `feinschliff.layout_picker._VARIETY_EXEMPT`. That
# set covers everything the picker's adjacent-slide variety penalty
# should skip (also includes title slides + chapter variants).
# `_SINGLETON_LAYOUTS` is a strict subset: chapter-orange / chapter-ink
# / title-orange / title-ink ARE NOT singletons here on purpose — a
# multi-chapter deck has multiple chapter openers, and the budget
# bonus is what alternates between the orange and ink variants (see
# `test_three_chapter_openers_alternate_orange_and_ink`). Keep the two
# sets in sync only at the "appears at most once" entries (agenda /
# end / full-bleed-cover).
#
# The photo variants of the singleton slides (agenda-photo, end-image)
# are singletons too — at most one agenda / closer per deck. Without this
# they'd collect the under-used-layout budget bonus and outrank the plain
# agenda / end on a generic request, silently defaulting decks to a photo
# variant that needs imagery the slide may not have.
_SINGLETON_LAYOUTS = frozenset({
    "agenda", "agenda-photo", "end", "end-image", "full-bleed-cover",
})

# How many candidates we examine per slide. The picker's default top_k
# is 3, but for budget-aware reranking we need to see every viable
# layout so an under-used one can climb. 20 covers the largest role
# bucket (data-comparison has 10 members) with headroom.
_CANDIDATE_WINDOW = 20


def _budget_bonus(layout_id: str, usage_count: int) -> float:
    """Diminishing-returns bonus for under-used layouts.

    usage 0 → +1.5, usage 1 → +0.75, usage 2 → +0.50, usage 3 → +0.375,
    asymptotically 0. Singleton layouts get 0.
    """
    if layout_id in _SINGLETON_LAYOUTS:
        return 0.0
    return _MAX_BUDGET_BONUS / (usage_count + 1)


def plan_deck_layouts(
    slide_signals: list[dict],
    *,
    candidate_window: int = _CANDIDATE_WINDOW,
    profiles: dict[str, dict] | None = None,
    deck_map: dict | None = None,
    visual_style: str | None = None,
) -> list[dict]:
    """Pick a layout for every slide using two-pass budget planning.

    Parameters
    ----------
    slide_signals
        One dict per slide, in deck order. Each dict carries the kwargs
        accepted by `feinschliff.layout_picker.pick_layout` (`role`,
        `concept_count`, `data_quantity`, `comparison`, `narrative_role`,
        `narrative_act`, `time_axis_role`, `audience_mode`,
        `diagram_kind`). Missing keys are treated as `None`. An optional
        `layout` key pins that slide: the pinned layout is used verbatim
        (rationale `["pinned"]`, no picker call) while still counting
        toward usage and history bookkeeping.
    candidate_window
        How many candidates per slide to consider for budget reranking.
        Defaults to 20 so every member of the largest role bucket
        (data-comparison, 10) is visible.
    profiles
        Optional `{name: affinity-profile}` table passed through to
        `pick_layout`. Brand-aware callers (e.g. `deck plan-skeleton`)
        pass the brand-merged table so brand-only layouts are ranked.
    deck_map
        Optional brand `deck-map.yaml` dict. When the slide's role maps
        to a deck-map entry (cover / agenda / section / quote / closer),
        that layout gets the additive
        :data:`feinschliff.deck.content_metadata.DECK_MAP_BONUS` so it
        ranks first by default — never a hard override.
    visual_style
        Optional deck-brief ``visual_style`` value passed through to
        `pick_layout` unchanged for every slide. ``None`` is the neutral
        default (no change to existing scoring). See
        :func:`feinschliff.layout_picker.pick_layout` for the full
        enum and per-value semantics.

    Returns
    -------
    list of dicts, one per slide, in input order:
        {
          "layout":          chosen layout id,
          "base_score":      affinity score before the budget bonus,
          "budget_bonus":    bonus applied to the winning candidate,
          "rationale":       list of rationale strings (picker + budget),
        }

    Each slide is picked with `predecessor=` set to the prior slide's
    signal kwargs plus its chosen ``layout`` id, so adjacency rules
    (``follows_not`` / ``follows_well``) in layout frontmatter can be
    evaluated against what actually precedes the slide — pinned and
    fallback picks included.

    A slide with no viable candidates falls back to `text-picture`. The
    fallback is recorded in the returned assignment but NOT counted
    against `text-picture`'s deck-wide usage budget or appended to the
    picker's `layout_history` — it's a synthetic, not-really-chosen pick,
    so a later slide that genuinely qualifies for `text-picture` should
    receive its full unused-layout bonus.
    """
    from feinschliff.deck.content_metadata import apply_deck_map_bonus

    usage: Counter[str] = Counter()
    history: list[str] = []
    assignments: list[dict] = []
    predecessor_signals: dict | None = None

    for signals in slide_signals:
        pinned = signals.get("layout")
        if isinstance(pinned, str) and pinned:
            # Explicit `layout:` pin — bypasses the picker (and any
            # deck-map default) entirely, but still counts toward usage
            # and history so later slides rotate around it. The pinned
            # slide is still the visual predecessor for the next slide.
            assignments.append({
                "layout":       pinned,
                "base_score":   0.0,
                "budget_bonus": 0.0,
                "rationale":    ["pinned"],
            })
            history.append(pinned)
            usage[pinned] += 1
            # Build predecessor from this slide's declared signals + the
            # pinned layout id so adjacency rules on the next slide fire.
            predecessor_signals = {
                "role":           signals.get("role"),
                "narrative_act":  signals.get("narrative_act"),
                "narrative_role": signals.get("narrative_role"),
                "layout":         pinned,
            }
            continue

        kwargs = {
            "role":            signals.get("role"),
            "concept_count":   signals.get("concept_count"),
            "data_quantity":   signals.get("data_quantity"),
            "comparison":      signals.get("comparison"),
            "narrative_role":  signals.get("narrative_role"),
            "narrative_act":   signals.get("narrative_act"),
            "time_axis_role":  signals.get("time_axis_role"),
            "audience_mode":   signals.get("audience_mode"),
            "diagram_kind":       signals.get("diagram_kind"),
            "diagram_complexity": signals.get("diagram_complexity"),
            "slot_lengths":       signals.get("slot_lengths") or None,
        }
        candidates = pick_layout(
            **kwargs,
            layout_history=history,
            predecessor=predecessor_signals,
            top_k=candidate_window,
            profiles=profiles,
            visual_style=visual_style,
        )
        if deck_map is not None:
            # Deck-map default: additive bonus on the brand's declared
            # cover / agenda / section / quote / closer layout for this
            # role, applied before the budget re-rank so the bonus flows
            # into the adjusted score.
            candidates = apply_deck_map_bonus(
                candidates, role=signals.get("role"), deck_map=deck_map,
            )
        if not candidates:
            # Fallback: no signals matched any layout. The fallback pick
            # (text-picture) IS the visual predecessor for the next slide —
            # it sits in the deck and its position affects adjacency.
            # Skip usage/history bookkeeping (not a genuine affinity pick)
            # so a later genuine text-picture slide still sees its full
            # unused-layout bonus, but do update predecessor_signals.
            assignments.append({
                "layout":       "text-picture",
                "base_score":   0.0,
                "budget_bonus": 0.0,
                "rationale":    ["fallback:no-candidates"],
            })
            predecessor_signals = {**kwargs, "layout": "text-picture"}
            continue

        # Re-rank with the budget bonus. Sort key matches the picker's
        # original tiebreak (alphabetical layout id) so two candidates
        # with identical adjusted scores resolve deterministically.
        reranked = []
        for cand in candidates:
            bonus = _budget_bonus(cand["layout"], usage[cand["layout"]])
            reranked.append({
                "layout":       cand["layout"],
                "base_score":   cand["score"],
                "budget_bonus": bonus,
                "adjusted":     cand["score"] + bonus,
                "rationale":    cand["rationale"],
            })
        reranked.sort(key=lambda c: (-c["adjusted"], c["layout"]))

        winner = reranked[0]
        rationale = list(winner["rationale"])
        if winner["budget_bonus"] > 0:
            rationale.append(
                f"budget-bonus(+{winner['budget_bonus']:.2f},"
                f"used={usage[winner['layout']]})"
            )

        assignments.append({
            "layout":       winner["layout"],
            "base_score":   winner["base_score"],
            "budget_bonus": winner["budget_bonus"],
            "rationale":    rationale,
        })
        history.append(winner["layout"])
        usage[winner["layout"]] += 1
        predecessor_signals = {**kwargs, "layout": winner["layout"]}

    return assignments

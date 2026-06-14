"""Structured layout picker.

Maps a small set of content signals to a ranked list of candidate
toolkit layouts. The signals come from the brief / planner; the scores
come from a static affinity table.

Signals
-------
role            str   data-role enum (title-primary, title-with-visual,
                     chapter-opener, agenda, data-quantity, data-comparison,
                     data-timeline, content-columns, content-with-visual,
                     quote, reference, closer)
concept_count   int   how many parallel concepts the slide carries (1..8)
data_quantity   int   how many data points / cells the slide carries
comparison      bool  is this slide comparing things?
narrative_role  str   optional narrative-role hint (e.g. "so-what",
                     "context", "evidence", "summary") — scored against
                     layouts that declare a matching `narrative_role`
                     affinity in their profile.
narrative_act   str   optional SCR-shape hint (situation | complication |
                     resolution) — populated by the storyline gate per
                     slide. Consumed by feinschliff_builder.verify.deck.narrative_arc
                     and by Phase 4 layouts (recommendation, next-steps).
                     Scored against Phase 4 layouts that declare a
                     `narrative_act` affinity; neutral against legacy
                     layouts (no penalty, no bonus).
time_axis_role  str   optional time-axis hint (strategic | chronological |
                     tactical) — disambiguates gantt vs roadmap vs
                     timeline. Scored against Phase 4 layouts that
                     declare a `time_axis_role` affinity; neutral
                     against legacy layouts.
audience_mode   str   optional deck-level density preference (presentation
                     | discussion). When `presentation`, layouts at the
                     low end of their ideal_count range get a small
                     bonus (sparser fits read better live). When
                     `discussion`, layouts at the high end get the bonus
                     (denser fits are fine in a read-along).
layout_history  list  optional list of recently-used layout IDs (most
                     recent last). Encourages visual variety: the last
                     layout used loses 0.5 points, the second-to-last
                     loses 0.25. Structural layouts (title slides, chapter
                     openers, agenda, end) are exempt — they don't rotate.
slot_lengths    dict  optional mapping of slot name → int character count
                     for the content being placed. Layouts whose declared
                     per-slot `chars` budget (from frontmatter) would be
                     exceeded receive a soft penalty proportional to the
                     overage. Never a hard rejection — the downstream
                     textfit gate and autoshrink remain authoritative.
                     Absent budgets (no `chars` key in the profile slot)
                     and absent slot_lengths entries are both treated as
                     unknown and skipped — only the intersection is scored.
predecessor     dict  optional previous slide's signals dict, including its
                     chosen `layout` id. Evaluated against this layout's
                     `follows_not` / `follows_well` frontmatter predicates
                     (`signal=value` syntax). Each follows_not hit: −1.5.
                     Each follows_well hit: +0.75. Additive, soft — never
                     a hard block. Pinned layouts bypass the picker and
                     are not affected.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

# Allowed enum values for the three Phase 3 signals. Validated fail-loud
# in pick_layout so typos surface as ValueError today rather than
# silently failing to score against Phase 4 affinity entries.
_VALID_NARRATIVE_ACTS = frozenset({"situation", "complication", "resolution"})
_VALID_TIME_AXIS_ROLES = frozenset({"strategic", "chronological", "tactical"})
_VALID_AUDIENCE_MODES = frozenset({"presentation", "discussion"})
# diagram_complexity steers the picker between the narrow (`excalidraw-diagram`
# / `svg-infographic`) and full-slide (`*-full`) diagram layouts. `deep`
# prefers the full layouts; `simple|medium` prefer the narrow ones.
_VALID_DIAGRAM_COMPLEXITY = frozenset({"simple", "medium", "deep"})

# Scale factor for the per-slot character-budget penalty. The maximum
# possible penalty (all budgeted slots 100 %+ over, averaged) is
# −_BUDGET_PENALTY_SCALE. Calibrated to sit below the role-match weight
# (+3) so structural fitness always wins; budgets break ties.
_BUDGET_PENALTY_SCALE = 2.0

# Structural layouts that anchor every deck — they don't rotate by content
# and should never be penalised for consecutive use.
_VARIETY_EXEMPT = frozenset({
    "title-orange", "title-ink", "full-bleed-cover",
    "chapter-orange", "chapter-ink", "agenda", "end",
})

# Content-bearing caller roles that must not land on `fixed_chrome` layouts
# (decompiled brand layouts whose decoration is carried verbatim — no room
# to reflow dense content around it). Framing roles (covers, chapter
# openers, quotes, closers) are deliberately NOT listed: those are exactly
# the brand moments fixed-chrome layouts exist for.
_FIXED_CHROME_GUARD_ROLES = frozenset({
    "content-columns", "data-quantity", "data-comparison",
    "data-timeline", "concept-diagram",
})


# Per-layout affinity profile. Each layout declares its profile in a YAML
# frontmatter fence at the top of its `.slide.dsl` file (parsed by
# `feinschliff.layout_profile`):
#   role            : the canonical data-role it serves
#   ideal_count     : sweet spot for concept_count (range, inclusive)
#   data ("data_band" in the fence) : "none" | "kpi" | "table" | "chart"
#   comp ("comparison" in the fence): True if built for comparison
#   narrative_role  : optional — preferred narrative role string (+2)
#   narrative_act   : optional — preferred SCR act (+1)
#   time_axis_role  : optional — preferred time-axis (+1)
#   variety_exempt  : optional — structural layout, exempt from the
#                     consecutive-use variety penalty
#   when_not_to_use : optional — list of "<signal>=<value>" demotions
#
# Score is computed as the sum of:
#   role match            +3
#   concept_count in band +2
#   concept_count near    +1 (one off)
#   data band match       +2
#   comparison flag match +1
#   narrative_role match  +2
#   narrative_act match   +1
#   time_axis_role match  +1
#   audience_mode bonus   +0.5 (sparser fit when presentation, denser
#                                when discussion; any layout, scaled
#                                against its ideal_count range)
#   slot budget penalty   −0..−2.0 (averaged per-slot overage fraction,
#                                scaled by _BUDGET_PENALTY_SCALE; only
#                                the intersection of declared chars budgets
#                                and provided slot_lengths is evaluated)
#   follows_not penalty   −1.5/hit (predecessor signal matches a
#                                follows_not predicate; additive across
#                                multiple hits; never a hard block)
#   follows_well bonus    +0.75/hit (predecessor signal matches a
#                                follows_well predicate; additive)
#   fixed-chrome guard    -6   (profile `fixed_chrome: true` vs a
#                                content/data caller role — see
#                                _FIXED_CHROME_GUARD_ROLES)
#   baked-text guard      -6   (profile `chrome_text: true` vs the same
#                                roles — chrome draws its own labels,
#                                text slots must not be rebound)
# Negative if role mismatched.
#
# The scoring table is no longer hand-maintained here: it is derived at
# runtime from the *discovered* layout set, so the picker's universe is the
# on-disk universe by construction (toolkit + plugin + env + user layouts,
# and — via the brand-aware `feinschliff.deck.picker.LayoutPicker` — brand
# overrides and brand-only layouts). A layout on disk can never be unpickable.


@lru_cache(maxsize=1)
def _default_profile_table() -> dict[str, dict]:
    """The picker table for the no-brand case: every discovered toolkit
    layout's affinity profile, keyed by name.

    Built lazily (first ``pick_layout`` call) and cached for the process.
    ``strict=False`` so a single malformed third-party layout drops out of
    the candidate set rather than failing every deck build; the toolkit's
    own bundled layouts are held to ``strict=True`` by the test suite.
    """
    from feinschliff.layout_discovery import discover_layout_paths
    from feinschliff.layout_profile import build_profile_table

    return build_profile_table(discover_layout_paths(), strict=False)


# Layouts that came in with Phase 4 — used by tests + docs to draw the
# line between "legacy scoring" (inert against new signals) and "Phase 4
# scoring" (affinity-driven by narrative_role / narrative_act /
# time_axis_role). The list lives in source-of-truth here so callers
# don't drift. Membership criterion: any layout whose frontmatter
# declares one of those affinity fields belongs here, or the
# legacy-inertness invariant in tests breaks.
_PHASE4_LAYOUTS = frozenset({
    "recommendation",
    "next-steps",
    "risk-register",
    "risk-matrix",
    "roadmap",
    "timeline",
    "excalidraw-diagram",
    "key-takeaways",
    "executive-summary",
    "pyramid",
    "action-title",
})


def _classify_data(data_quantity: int | None) -> str:
    if data_quantity is None or data_quantity == 0:
        return "none"
    if data_quantity <= 4:
        return "kpi"
    if data_quantity <= 25:
        return "table"
    return "chart"


def pick_layout(
    role: str | None = None,
    concept_count: int | None = None,
    data_quantity: int | None = None,
    comparison: bool | None = None,
    narrative_role: str | None = None,
    *,
    narrative_act: str | None = None,
    time_axis_role: str | None = None,
    audience_mode: str | None = None,
    diagram_kind: Literal["concept", "chart"] | None = None,
    diagram_complexity: Literal["simple", "medium", "deep"] | None = None,
    layout_history: list | None = None,
    slot_lengths: dict[str, int] | None = None,
    predecessor: dict | None = None,
    top_k: int = 3,
    profiles: dict[str, dict] | None = None,
) -> list[dict]:
    """Return up to `top_k` candidate layouts ranked by affinity score.

    Each entry is a dict {layout, score, rationale}.

    `narrative_act`, `time_axis_role`, and `audience_mode` are now
    active scoring inputs:
    - `narrative_act` / `time_axis_role` contribute +1 each when they
      match a Phase 4 layout's declared affinity. Legacy layouts don't
      declare these fields, so they remain neutral against the signals
      (no bonus, no penalty).
    - `audience_mode` shifts the concept_count preference: +0.5 to
      layouts whose ideal_count low end is within 1 of `concept_count`
      when `presentation` (sparser), or whose high end is within 1
      when `discussion` (denser).

    `narrative_role` (the legacy signal) also gets a +2 affinity bonus
    when it matches a Phase 4 layout's declared `narrative_role`.
    Layouts without a declared `narrative_role` stay neutral against it.

    `layout_history` is an optional list of recently-used layout IDs
    (most recent last). It applies a small variety penalty so the same
    layout is not picked on consecutive slides: the immediately preceding
    layout loses 0.5 points, the one before that loses 0.25. Structural
    layouts (title slides, chapter openers, agenda, end) are exempt
    from this penalty since they never rotate. The penalty never
    eliminates a layout — it only breaks ties in favour of variety.

    `slot_lengths` is an optional ``{slot_name: char_count}`` dict
    carrying the measured length of the content going into each slot.
    Layouts whose frontmatter declares an integer ``chars`` budget for a
    slot receive a soft score penalty proportional to how far the content
    exceeds that budget (averaged across the intersection of declared
    budgets and provided lengths, capped at 100 % per slot, scaled by
    ``_BUDGET_PENALTY_SCALE``). Layouts with no declared budgets are
    unaffected. The penalty is never a hard rejection.

    `predecessor` is the previous slide's signals dict, including its
    chosen ``layout`` id. When provided, each candidate layout's
    ``follows_not`` / ``follows_well`` frontmatter predicates are matched
    against it: each ``follows_not`` hit subtracts 1.5; each
    ``follows_well`` hit adds 0.75. Adjustments are additive and soft —
    they shift rank but never hard-block a layout.

    `profiles` is the ``{name: affinity-profile}`` table to score against.
    When ``None`` (the default), the cached toolkit-only table built from
    the discovered layout set is used. The brand-aware
    :class:`feinschliff.deck.picker.LayoutPicker` passes a brand-merged
    table so brand overrides and brand-only layouts are ranked too.
    """
    if narrative_act is not None and narrative_act not in _VALID_NARRATIVE_ACTS:
        raise ValueError(
            f"narrative_act: {narrative_act!r} not in "
            f"{sorted(_VALID_NARRATIVE_ACTS)}"
        )
    if time_axis_role is not None and time_axis_role not in _VALID_TIME_AXIS_ROLES:
        raise ValueError(
            f"time_axis_role: {time_axis_role!r} not in "
            f"{sorted(_VALID_TIME_AXIS_ROLES)}"
        )
    if audience_mode is not None and audience_mode not in _VALID_AUDIENCE_MODES:
        raise ValueError(
            f"audience_mode: {audience_mode!r} not in "
            f"{sorted(_VALID_AUDIENCE_MODES)}"
        )
    if diagram_complexity is not None and diagram_complexity not in _VALID_DIAGRAM_COMPLEXITY:
        raise ValueError(
            f"diagram_complexity: {diagram_complexity!r} not in "
            f"{sorted(_VALID_DIAGRAM_COMPLEXITY)}"
        )

    # Inference: if the caller didn't pass `diagram_complexity` but
    # `concept_count` is high enough to suggest a dense diagram, set
    # complexity=deep so the full-slide layouts get the affinity bonus.
    # This keeps the existing narrow `excalidraw-diagram` favored for the
    # 2-8 node case and steers naturally toward `excalidraw-diagram-full`
    # for richer architectures.
    if diagram_complexity is None and concept_count is not None and concept_count >= 8:
        diagram_complexity = "deep"

    data_band = _classify_data(data_quantity)
    cc = concept_count or 0

    table = profiles if profiles is not None else _default_profile_table()

    scored: list[dict] = []
    for layout_id, profile in table.items():
        score = 0.0
        rationale_parts: list[str] = []

        if role and profile["role"] == role:
            score += 3
            rationale_parts.append("role")
        elif role:
            score -= 1

        lo, hi = profile["ideal_count"]
        if cc:
            if lo <= cc <= hi:
                score += 2
                rationale_parts.append(f"count={cc}∈[{lo},{hi}]")
            elif lo - 1 <= cc <= hi + 1:
                score += 1
                rationale_parts.append(f"count={cc}~[{lo},{hi}]")

        if data_band != "none" and profile["data"] == data_band:
            score += 2
            rationale_parts.append(f"data={data_band}")

        if comparison is not None and profile["comp"] == comparison:
            score += 1
            rationale_parts.append("comp")

        # Phase 4 affinity scoring: a layout that declares one of these
        # optional fields gets a bonus when the caller's signal matches.
        # Layouts without the field (legacy) silently skip — no penalty,
        # so the existing scoring contract holds for them.
        if narrative_role and profile.get("narrative_role") == narrative_role:
            score += 2
            rationale_parts.append(f"narr-role={narrative_role}")
        if narrative_act and profile.get("narrative_act") == narrative_act:
            score += 1
            rationale_parts.append(f"narr-act={narrative_act}")
        if time_axis_role and profile.get("time_axis_role") == time_axis_role:
            score += 1
            rationale_parts.append(f"time-axis={time_axis_role}")

        # audience_mode bonus: nudges sparser layouts in presentation
        # mode, denser in discussion. Applied to ALL layouts (legacy +
        # Phase 4), keyed on the layout's ideal_count range vs the
        # caller's concept_count — no per-layout schema field needed.
        # Only fires when both concept_count and audience_mode are set.
        if audience_mode and cc:
            if audience_mode == "presentation" and lo - 1 <= cc <= lo + 1:
                score += 0.5
                rationale_parts.append("audience=presentation/sparser")
            elif audience_mode == "discussion" and hi - 1 <= cc <= hi + 1:
                score += 0.5
                rationale_parts.append("audience=discussion/denser")

        # Programmatic when_not_to_use enforcement. Each entry in
        # profile["when_not_to_use"] is "<signal_name>=<value>" (e.g.
        # "narrative_role=closing"). Any matching signal subtracts 3 points,
        # enough to fall below an otherwise-equal candidate. Penalty is
        # additive across multiple matches.
        neg_rules = profile.get("when_not_to_use", []) or []
        caller_signals = {
            "role": role,
            "concept_count": concept_count,
            "data_quantity": data_quantity,
            "comparison": comparison,
            "narrative_role": narrative_role,
            "narrative_act": narrative_act,
            "time_axis_role": time_axis_role,
            "audience_mode": audience_mode,
            "diagram_kind": diagram_kind,
        }
        neg_hits = []
        caller_signals["diagram_complexity"] = diagram_complexity
        for rule in neg_rules:
            if "=" not in rule:
                continue
            sig, expected = rule.split("=", 1)
            actual = caller_signals.get(sig.strip())
            if str(actual).lower() == expected.strip().lower():
                score -= 3
                neg_hits.append(rule)
        if neg_hits:
            rationale_parts.append(f"negative-guidance:{','.join(neg_hits)}")

        # Adjacency (sequencing) scoring: evaluate this layout's follows_not /
        # follows_well predicates against the predecessor slide's signals dict
        # (which carries role, narrative_act, and layout of the prior slide).
        # Each follows_not hit: −1.5. Each follows_well hit: +0.75. Additive,
        # soft — ranking bias only, never a hard block.
        adjacency_hit = False
        if predecessor is not None:
            pred_signals = dict(predecessor)
            follows_not_rules = profile.get("follows_not") or []
            for rule in follows_not_rules:
                if "=" not in rule:
                    continue
                sig, expected = rule.split("=", 1)
                if str(pred_signals.get(sig.strip())).lower() == expected.strip().lower():
                    score -= 1.5
                    adjacency_hit = True
                    rationale_parts.append(f"follows-not:{rule}")
            follows_well_rules = profile.get("follows_well") or []
            for rule in follows_well_rules:
                if "=" not in rule:
                    continue
                sig, expected = rule.split("=", 1)
                if str(pred_signals.get(sig.strip())).lower() == expected.strip().lower():
                    score += 0.75
                    rationale_parts.append(f"follows-well:{rule}")

        # Slot budget penalty: steers toward layouts whose declared per-slot
        # char budgets fit the content being placed. Only the intersection of
        # slots with an int `chars` budget in the profile AND a length in
        # slot_lengths is evaluated — absence means unknown constraints, not
        # a violation. A budgeted slot is matched by its name OR by its
        # declared `role` (decompiled brand packs name slots text_1, text_2…
        # and carry the semantic role in `slots.*.role` — callers supply
        # lengths keyed by semantic name, e.g. "title"). Max penalty
        # (−_BUDGET_PENALTY_SCALE) sits below the role-match weight (+3):
        # structural fitness wins, budgets break ties.
        if slot_lengths:
            budgeted_slots: dict[str, tuple[int, int]] = {}
            for name, meta in (profile.get("slots") or {}).items():
                if not (
                    isinstance(meta, dict)
                    and isinstance(meta.get("chars"), int)
                    and meta["chars"] > 0
                ):
                    continue
                length = slot_lengths.get(name)
                if not isinstance(length, int):
                    length = slot_lengths.get(meta.get("role"))
                if isinstance(length, int):
                    budgeted_slots[name] = (meta["chars"], length)
            if budgeted_slots:
                overage_parts: list[str] = []
                total_overage = 0.0
                for sname, (chars, length) in budgeted_slots.items():
                    raw = max(0, length - chars) / chars
                    capped = min(raw, 1.0)
                    total_overage += capped
                    if capped > 0:
                        pct = int(round(capped * 100))
                        overage_parts.append(f"{sname}+{pct}%")
                penalty = (total_overage / len(budgeted_slots)) * _BUDGET_PENALTY_SCALE
                if penalty > 0:
                    score -= penalty
                    rationale_parts.append(
                        f"over-budget({', '.join(overage_parts)})"
                    )

        # Fixed-chrome guard: a decompiled brand layout that carries its
        # source decoration verbatim (`fixed_chrome: true`) cannot host
        # dense content — sink it hard whenever the caller asks for a
        # content/data role. Additive like every other signal (NOT a hard
        # drop): a pinned `layout:` bypasses the picker entirely, and
        # framing roles (cover / chapter / quote / closer) are unaffected.
        guard_hit = (
            bool(profile.get("fixed_chrome"))
            and role in _FIXED_CHROME_GUARD_ROLES
        )
        if guard_hit:
            score -= 6.0
            rationale_parts.append("fixed-chrome-guard")

        # Baked-text guard: native chrome that draws its own <a:t> labels
        # (`chrome_text: true`) — binding the overlapping text slots would
        # overprint them. Same additive sink for content/data roles as the
        # fixed-chrome guard, with its own tag so the planner sees why.
        baked_hit = (
            bool(profile.get("chrome_text"))
            and role in _FIXED_CHROME_GUARD_ROLES
        )
        if baked_hit:
            score -= 6.0
            rationale_parts.append("baked-text-guard")

        # Variety penalty: nudge recently-used layouts down so the deck
        # avoids visual monotony (Presenton principle: adjacent slides
        # should differ unless necessary). Structural layouts are exempt —
        # either by the static `_VARIETY_EXEMPT` set or by declaring
        # `variety_exempt: true` in their frontmatter profile.
        #
        # Cooldown is a 4-slide window with decaying weight so the same
        # layout type really sits out a few slides before re-entering the
        # race. The strongest hit (-3.0 at the most-recent position)
        # exceeds the full +3 role-match bonus — a back-to-back repeat
        # only survives when there is genuinely no alternative. Calibrated
        # against the brand-content deck-map bonus (+4) + role match (+3)
        # + concept-count fit (+2) + description bonus (+1.5) stack that
        # otherwise lets the same brand-content-list layout win every
        # turn in a thin-pool brand pack.
        exempt = layout_id in _VARIETY_EXEMPT or profile.get("variety_exempt")
        if layout_history and not exempt:
            # Walk the tail of the history; further-back hits cost less.
            for back, penalty in ((1, 3.0), (2, 2.0), (3, 1.0), (4, 0.5)):
                if (len(layout_history) >= back
                        and layout_history[-back] == layout_id):
                    score -= penalty
                    rationale_parts.append(
                        "variety-penalty(last)" if back == 1
                        else f"variety-penalty(-{back})")
                    break

        # Image-default bonus: presentations are a visual medium, so when
        # a content slide can carry an image the picker should prefer the
        # layout that does. Without this, alphabetical tiebreaks among
        # same-role / same-deck-map content-columns siblings systematically
        # favour the text-only `content-N` line over the image-bearing
        # `slide-NN` siblings (the v3 CookIt symptom: 5 text-only + 2
        # image-bearing in 11 slides). Suppress for framing roles (cover,
        # agenda, quote, closer) where text-only chrome is the design.
        #
        # Density-aware: a layout's image-slot count is part of the signal,
        # so 2I/3I/7I layouts can win where 1I would not. Capped at +2.5
        # so role/concept fit still dominates. When the slide has a
        # concept_count signal AND it matches the layout's image-slot
        # count (one image per concept = side-by-side comparison /
        # product gallery / team intro), an additional +1.0 lands the
        # right composition.
        _layout_slots = profile.get("slots") or {}
        _img_count = (
            sum(1 for meta in _layout_slots.values()
                if isinstance(meta, dict) and meta.get("role") == "image")
            if isinstance(_layout_slots, dict) else 0
        )
        _content_role = role in (
            "content-columns", "content-narrative", "data-comparison",
            "data-quantity", "data-timeline", "concept-diagram", "evidence",
            "situation", "complication", "recommendation",
        )
        if _img_count and _content_role and not exempt:
            # Uniform +1.5 for any image-bearing layout — picks should
            # rotate across the 1I/2I/3I/7I spectrum, not concentrate on
            # the densest.
            score += 1.5
            rationale_parts.append(f"image-default(+1.5, {_img_count}I)")
            # Concept-count match: one image per concept is a strong
            # composition signal (side-by-side comparison, gallery, team
            # intro). +2.0 is decisive — it overcomes the density gap
            # between competing image-bearing siblings, so the layout
            # whose image count actually matches the content wins.
            if concept_count and _img_count == concept_count:
                score += 0.5
                rationale_parts.append("image-count==concept-count(+0.5)")

        # diagram_kind affinity: steers toward the canonical diagram layout
        # for the requested kind. Applied after existing scoring so it
        # overrides ties without disturbing the base signals.
        if diagram_kind == "concept":
            if layout_id in ("excalidraw-diagram", "excalidraw-diagram-full"):
                score += 3
                rationale_parts.append("diagram_kind=concept")
            elif profile["data"] == "chart":
                score -= 2
                rationale_parts.append("diagram_kind=concept/anti-chart")
        elif diagram_kind == "chart":
            if layout_id in ("svg-infographic", "svg-infographic-full"):
                score += 2
                rationale_parts.append("diagram_kind=chart")

        # diagram_complexity affinity: +2 when the layout's declared
        # complexity matches the caller's signal (deep → -full layouts,
        # simple/medium → narrow layouts). Layouts without a declared
        # complexity field stay neutral.
        if diagram_complexity and profile.get("diagram_complexity") == diagram_complexity:
            score += 2
            rationale_parts.append(f"diagram_complexity={diagram_complexity}")
        elif diagram_complexity == "deep" and profile.get("diagram_complexity") == "simple":
            # Explicit deep request actively *demotes* the narrow layouts so
            # the picker doesn't fall back to them when the user asked for
            # depth and the ideal_count is borderline.
            score -= 1
            rationale_parts.append("diagram_complexity=deep/anti-narrow")

        # Surface the layout's content description (decompiled brand packs
        # declare what the slide chrome depicts) in the rationale, so a
        # planning LLM reading pick output sees what's on the slide — and
        # its curated when-to-use guidance right next to it.
        desc = profile.get("description")
        if isinstance(desc, str) and desc:
            rationale_parts.append(f"desc:{desc[:80]}")
        use = profile.get("when_to_use")
        if isinstance(use, str) and use:
            rationale_parts.append(f"use:{use[:80]}")

        # Include layouts with positive score, OR layouts that received a
        # when_not_to_use penalty / adjacency demotion / fixed-chrome guard /
        # baked-text guard — so the planning agent can read the demotion
        # rationale even though the layout ranked low.
        if score > 0 or neg_hits or adjacency_hit or guard_hit or baked_hit:
            scored.append({
                "layout": layout_id,
                "score": score,
                "rationale": rationale_parts if rationale_parts else ["—"],
            })

    scored.sort(key=lambda c: (-c["score"], c["layout"]))
    # Debug trace — when FEINSCHLIFF_DEBUG_PICKER=1 set, emit the considered
    # set + scores + rationale. Tightly scoped: small N (top_k usually 3-20)
    # and one line per candidate, so even verbose runs stay readable.
    import os as _os
    import sys as _sys
    if _os.environ.get("FEINSCHLIFF_DEBUG_PICKER"):
        sig = f"role={role!r} concept_count={concept_count} data_quantity={data_quantity}"
        print(f"[picker] {sig} → {len(scored)} candidates", file=_sys.stderr)
        for c in scored[:top_k]:
            print(f"  {c['score']:+.2f}  {c['layout']:30s}  {c['rationale']}",
                  file=_sys.stderr)
    return scored[:top_k]

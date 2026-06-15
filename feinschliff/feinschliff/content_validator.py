"""Pre-render content lints: catch title-length, action-verb-leading, and
slot-overflow issues before render budget is burned.

Runs after content YAML load, before slot interpolation. Operates on the
plain dict of slot values, with no python-pptx dependency. Cheap and
deterministic — the LLM-judged checks live in lib/verify/.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Literal

from feinschliff.slot_budget import SlotBudget  # needed at runtime for isinstance check


# Matches common numeric anchors in so_what text: integers, decimals,
# percentages, magnitude suffixes (k/M/B), currency prefixes, ratios,
# and multipliers. Any match means the text has a concrete quantity anchor.
_NUMERIC_ANCHOR_RE = re.compile(
    r'(?:'
    r'[$€£¥]\s*\d'       # currency-prefixed value
    r'|\d+(?:[.,]\d+)*(?:\s*[%kKmMbBxX]|\b)'  # number with optional suffix
    r'|\d+\s*:\s*\d+'    # ratio (3:1, 2:1)
    r')'
)


@dataclass
class ContentDefect:
    kind: str           # "title-length" | "action-verb-leading" | "vague-so-what" | "slot-collision"
    slide_index: int    # 1-based
    slot: str           # e.g. "title", "actions[0].verb"
    message: str
    severity: Literal["fatal", "warn"] = "fatal"  # "fatal" (aborts build) | "warn" (logged, build continues)

    def __str__(self) -> str:
        return f"slide {self.slide_index} [{self.kind}] {self.slot}: {self.message}"


_MAX_TITLE_WORDS = 15
_MAX_TITLE_LINES = 2


def _check_title_length(
    title: str,
    slide_index: int,
    *,
    slot: str = "title",
) -> list[ContentDefect]:
    """Enforce ≤15 words AND ≤2 manual lines on a title string."""
    out: list[ContentDefect] = []
    stripped = title.strip()
    if not stripped:
        return out  # empty title: skip — downstream renders it as empty box

    word_count = len(stripped.split())
    if word_count > _MAX_TITLE_WORDS:
        out.append(ContentDefect(
            kind="title-length",
            slide_index=slide_index,
            slot=slot,
            message=f"title too long: {word_count} words (max {_MAX_TITLE_WORDS})",
        ))

    line_count = stripped.count("\n") + 1
    if line_count > _MAX_TITLE_LINES:
        out.append(ContentDefect(
            kind="title-length",
            slide_index=slide_index,
            slot=slot,
            message=f"title spans {line_count} lines (max {_MAX_TITLE_LINES})",
        ))

    return out


# The conventional Feinschliff title slot is `action_title` for most content
# layouts; `title` is the literal for covers / end / agenda. Both are checked
# for length. (Plain `name` for full-bleed-cover and friends if needed — add
# here as new layout conventions surface.)
_TITLE_SLOT_KEYS = ("title", "action_title")


_IMPERATIVES_BASE = frozenset(s.lower() for s in [
    # consulting-deck action verbs — curated from McKinsey / BCG / Bain
    # recommendation + next-steps slides.
    "Grow", "Minimize", "Improve", "Optimize", "Drive", "Build", "Launch",
    "Eliminate", "Reduce", "Expand", "Develop", "Establish", "Implement",
    "Streamline", "Accelerate", "Scale", "Consolidate", "Pilot",
    "Roll", "Deploy", "Migrate", "Cut", "Increase", "Decrease", "Initiate",
    "Hire", "Train", "Acquire", "Define", "Align", "Audit", "Document",
    "Test", "Validate", "Ship", "Measure", "Track", "Monitor", "Identify",
    "Investigate", "Analyze", "Review", "Approve", "Negotiate", "Procure",
    "Finalize", "Communicate", "Engage", "Onboard", "Refactor", "Rebuild",
    "Sunset", "Retire", "Replace", "Adopt", "Create", "Add", "Remove",
    "Update", "Refresh", "Redesign", "Restructure", "Reorganize", "Centralize",
    "Decentralize", "Standardize", "Automate", "Codify", "Enable", "Empower",
    "Invest", "Divest", "Partner", "Collaborate", "Coordinate", "Outsource",
    "Insource", "Prioritize", "Focus", "Concentrate", "Allocate", "Reallocate",
    "Move", "Shift", "Transition", "Convert", "Transform", "Modernize",
])


def _imperatives() -> frozenset[str]:
    """Effective imperative whitelist — base + env-var additions."""
    extra = os.environ.get("FEINSCHLIFF_EXTRA_IMPERATIVES", "")
    if not extra:
        return _IMPERATIVES_BASE
    return _IMPERATIVES_BASE | frozenset(s.strip().lower() for s in extra.split(",") if s.strip())


_ACTION_SLOTS = ("actions", "recommendations", "mitigations")


# Pyramid Principle: a claim is supported by 2-3 arguments. Below 2 = no
# triangulation; above 3 = MECE breakdown failure. McKinsey rule.
_PYRAMID_MIN = 2
_PYRAMID_MAX = 3

# Miller's chunking range. Below 3 doesn't justify a list; above 9 exceeds
# working-memory capacity. Universal in key-takeaways / recommendation
# slides.
_CHUNK_MIN = 3
_CHUNK_MAX = 9


# Layout → slot routing for the structural validators. A validator only
# fires when the current slide's layout is in its routing table; the table
# value is the list-slot name to inspect on the content ctx. This keeps the
# checks layout-aware so they don't trip on coincidentally-named slots in
# unrelated layouts.
#
# pyramid-arity: the Phase 4 `recommendation` layout is now active. Its
# `recommendations` slot is 2-3 per schema — exactly the McKinsey/Pyramid
# Principle bound. `executive-summary.insights`/`next_steps` remain off
# the table because their 3-5 schemas conflict with the 2-3 Pyramid bound.
_PYRAMID_ARITY_LAYOUTS: dict[str, str] = {
    "recommendation": "recommendations",
}

# chunking-3-to-9: `key-takeaways` is the canonical chunked-list slide;
# its list slot is named `cards` (2-4 per schema — the 2-card case will
# legitimately trip chunking, which is the desired Miller behavior).
# `recommendation` routes here too for symmetry: 3-9 is wider than the
# layout's 2-3 schema, so this is a no-op for valid content but pins the
# behavior should someone pass 10+ recommendations.
_CHUNKING_LAYOUTS: dict[str, str] = {
    "key-takeaways": "cards",
    "recommendation": "recommendations",
}


# Layouts whose `so_what:` slot carries the LLM-derived takeaway from a
# data/chart. The vague-so-what lint only fires on these — the slot itself
# is a *convention*, not a required schema field, so for any other layout
# we leave a stray `so_what` key alone.
_SO_WHAT_LAYOUTS = frozenset({
    "bar-chart", "line-chart", "kpi-grid", "scorecard",
    "stacked-bar", "waterfall",
})


# Corporate-speak vagueness — the curated set that surfaces in weak "so what"
# claims. The check intentionally errs conservative: we count occurrences in
# the so_what text and only fire when there are ≥2 vague words AND no
# concrete anchor (digit / proper-noun) in the same sentence.
_VAGUE_SO_WHAT_KEYWORDS = frozenset(s.lower() for s in [
    "improve", "improving", "improved",
    "optimize", "optimizing", "optimized", "optimization",
    "leverage", "leveraging", "leveraged",
    "enhance", "enhancing", "enhanced",
    "streamline", "streamlining", "streamlined",
    "synergy", "synergies",
    "drive", "driving",  # too generic — "drive growth", "drive change"
    "enable", "enabling", "enabled",
    "facilitate", "facilitating",
    "support", "supporting",
    "robust", "scalable", "best-in-class", "world-class",
    "transform", "transformation", "transformative",
    "innovate", "innovative", "innovation",
    "value", "value-add",  # "delivers value"
    "solution", "solutions",  # "is a solution for..."
    "next-generation", "cutting-edge",
    # Extended set (Presenton-informed — common LLM clichés in data takeaways)
    "game-changing", "game-changer",
    "paradigm", "paradigm-shift",
    "holistic", "ecosystem",
    "unlock", "unlocking", "unlocked",
    "empower", "empowering", "empowered",
    "accelerate", "accelerating",  # without a magnitude = vague
    "maximize", "maximizing", "maximized",
    "impactful", "meaningful", "actionable",
    "seamless", "frictionless",
    "disrupt", "disruption", "disruptive",
])

# Filler words that dilute the signal in data-slide takeaways.
# A so_what with ≥2 of these reads as padding, not insight.
# Unlike the vague-so-what check, this fires regardless of a numeric anchor
# because fillers weaken even concrete sentences ("Revenue very significantly
# grew by 12%" is weaker than "Revenue grew 12%").
_FILLER_WORDS = frozenset(s.lower() for s in [
    "very", "really", "quite", "rather", "somewhat", "basically",
    "actually", "generally", "essentially", "literally", "truly",
    "incredibly", "extremely", "highly", "absolutely",
])


def _first_word(text: str) -> str:
    s = text.strip()
    if not s:
        return ""
    return s.split()[0]


def _check_action_verb_leading(
    items: list,
    *,
    slot_name: str,
    slide_index: int,
) -> list[ContentDefect]:
    """For each item, require the first word be in the imperative whitelist."""
    out: list[ContentDefect] = []
    whitelist = _imperatives()
    for i, item in enumerate(items):
        if isinstance(item, str):
            first = _first_word(item).lower().rstrip(",.;:")
            slot = f"{slot_name}[{i}]"
            target = item
        elif isinstance(item, dict) and "verb" in item:
            first = _first_word(str(item["verb"])).lower().rstrip(",.;:")
            slot = f"{slot_name}[{i}].verb"
            target = str(item["verb"])
        else:
            continue  # unknown shape — skip
        if not first:
            continue
        if first not in whitelist:
            out.append(ContentDefect(
                kind="action-verb-leading",
                slide_index=slide_index,
                slot=slot,
                message=(f"item does not begin with an imperative verb: "
                         f"{target!r} (first token: {first!r})"),
            ))
    return out


def _check_pyramid_arity(
    arguments: list,
    *,
    slot_name: str,
    slide_index: int,
) -> list[ContentDefect]:
    """Enforce 2-3 supporting arguments (Pyramid Principle)."""
    n = len(arguments)
    if _PYRAMID_MIN <= n <= _PYRAMID_MAX:
        return []
    return [ContentDefect(
        kind="pyramid-arity",
        slide_index=slide_index,
        slot=slot_name,
        message=(f"{slot_name} slot has {n} item(s); Pyramid Principle "
                 f"requires {_PYRAMID_MIN}-{_PYRAMID_MAX}"),
    )]


def _check_chunking(
    items: list,
    *,
    slot_name: str,
    slide_index: int,
) -> list[ContentDefect]:
    """Enforce 3-9 items (Miller's chunking range)."""
    n = len(items)
    if _CHUNK_MIN <= n <= _CHUNK_MAX:
        return []
    return [ContentDefect(
        kind="chunking-3-to-9",
        slide_index=slide_index,
        slot=slot_name,
        message=(f"{slot_name} slot has {n} entry(s); chunking range is "
                 f"{_CHUNK_MIN}-{_CHUNK_MAX}"),
    )]


def _check_so_what_vagueness(
    so_what: str,
    *,
    slide_index: int,
) -> list[ContentDefect]:
    """Flag so_what text containing only vague corporate-speak keywords.

    Fires if 2+ vague keywords appear AND no concrete numeric/proper-noun
    anchor is present. The check is intentionally conservative — false
    negatives are acceptable; false positives erode trust.
    """
    text = so_what.strip()
    if not text:
        return []

    # Tokenize: whitespace-split, lowercase, strip trailing punctuation.
    tokens = [t.lower().rstrip(",.;:!?\"'") for t in text.split()]
    vague_count = sum(1 for t in tokens if t in _VAGUE_SO_WHAT_KEYWORDS)
    if vague_count < 2:
        return []

    # Numeric anchor: percentage, currency, ratio, magnitude suffix, or any
    # bare digit sequence. The regex catches "$1M", "45%", "3x", "2:1", "12k"
    # as well as plain "12". More robust than the previous `any(ch.isdigit())`
    # scan, which would fire on ordinal words like "Q1" or "2nd" — those are
    # still anchors, so the regex correctly captures them too.
    if _NUMERIC_ANCHOR_RE.search(text):
        return []

    # Proper-noun anchor: any non-first token starting with an uppercase letter
    # AND longer than 3 chars. Filters common sentence-start caps and short
    # initials (Q1, US, CEO) that are already covered by the numeric regex.
    raw_tokens = text.split()
    for tok in raw_tokens[1:]:
        clean = tok.strip(",.;:!?\"'")
        if len(clean) > 3 and clean[:1].isupper():
            return []

    return [ContentDefect(
        kind="vague-so-what",
        slide_index=slide_index,
        slot="so_what",
        message=(f"so_what reads as corporate-speak with {vague_count} "
                 f"vague keyword(s) and no concrete numeric or named-entity "
                 f"anchor: {so_what!r}"),
    )]


def _autoshrink_fitted_pt(value: str, budget: "SlotBudget") -> float:
    """Compute the fitted font size (pt) the emitter would use for an
    autoshrink slot — mirrors check_slot_overflow's rescue exactly so
    both callers share the same math and can't drift.

    Uses the inset-reduced envelope (pptx_emit subtracts insets from the
    fit budget) and the same 10pt floor.
    """
    from feinschliff.textfit import autoshrink_size as _autoshrink
    inset_w = max(1, budget.width_emu - budget.inset_w_emu)
    inset_h = max(1, budget.height_emu - budget.inset_h_emu)
    return _autoshrink(
        value, font=budget.font_family, max_size_pt=budget.font_size_pt,
        min_size_pt=10, bold=budget.bold, width_emu=inset_w,
        height_emu=inset_h, line_height=budget.line_height,
    )


def check_slot_overflow(
    value: str,
    *,
    slot: str,
    budget: SlotBudget,
    slide_index: int,
) -> list[ContentDefect]:
    """Fire when *value* will not fit in its DSL text box.

    Uses the same ``textfit.fits()`` helper as the autoshrink emitter, so the
    prediction matches what the renderer would do. Catches the most common
    overflow classes before a single pixel is rendered:

    - Title at a large font size (act-title 56px) wrapping to 2+ lines when
      only 1 line was budgeted.
    - Body text exceeding ``maxheight`` and spilling into adjacent elements.
    - KPI values with 3 digits overflowing a narrow maxwidth.

    Only fires when ``budget.height_px > 0`` (unconstrained slots are skipped).

    Note: the primary fit check uses the raw box (the tuned-corpus envelope);
    only the autoshrink rescue is inset-aware, mirroring the emitter's actual
    shrink budget — predictions err pessimistic there, which converts silent
    under-shrink into a visible defect.
    """
    if not value or not value.strip():
        return []
    if budget.height_px <= 0:
        return []

    from feinschliff.textfit import fits as _fits  # local import — no hard dep at module level

    ok = _fits(
        value,
        font=budget.font_family,
        size_pt=budget.font_size_pt,
        bold=budget.bold,
        width_emu=budget.width_emu,
        height_emu=budget.height_emu,
        line_height=budget.line_height,
    )
    if ok:
        return []

    # Autoshrink rescue: the emitter will shrink to fit (10pt floor) using the
    # INSET-REDUCED envelope (pptx_emit subtracts inset_w/h_emu from the fit
    # budget). Use the same reduced box here so a slot that overflows the raw
    # box at 10pt but only barely passes the raw rescue cannot slip through
    # silently — a "raw-pass, inset-fail" case is a real defect.
    floor_note = ""
    if budget.autoshrink:
        fitted = _autoshrink_fitted_pt(value, budget)
        inset_w = max(1, budget.width_emu - budget.inset_w_emu)
        inset_h = max(1, budget.height_emu - budget.inset_h_emu)
        if _fits(value, font=budget.font_family, size_pt=fitted,
                 bold=budget.bold, width_emu=inset_w,
                 height_emu=inset_h, line_height=budget.line_height):
            return []
        floor_note = " Overflows even at the 10pt autoshrink floor."

    # Compute estimated lines for a helpful message and wrap-overflow guard.
    from feinschliff.textfit import measure_height_emu as _measure
    actual_h = _measure(
        value,
        font=budget.font_family,
        size_pt=budget.font_size_pt,
        bold=budget.bold,
        width_emu=budget.width_emu,
        line_height=budget.line_height,
    )
    line_h = budget.font_size_pt * budget.line_height * 12700  # EMU per line
    est_lines = max(1, round(actual_h / line_h)) if line_h > 0 else "?"

    # Skip vertical-clipping-only cases: the text fits on 1 line horizontally
    # but the single line is taller than maxheight. PowerPoint clips downward
    # cleanly and designers intentionally use this pattern (e.g. kpi-value at
    # 120px in an 80px box). Only fire when the text *wraps* to more lines
    # than the box can contain — that's the class of defect that causes real
    # visual damage (overlapping neighbours, spill into footer, etc.).
    if isinstance(est_lines, int) and est_lines <= budget.max_lines:
        return []

    hyphen_hint = (
        " Avoid hyphenated compounds in this narrow slot."
        if budget.chars_per_line <= 25 else ""
    )
    return [ContentDefect(
        kind="slot-overflow",
        slide_index=slide_index,
        slot=slot,
        message=(
            f"text wraps to ~{est_lines} line(s) but box holds {budget.max_lines} "
            f"at {budget.style} {budget.size_px:.0f}px "
            f"({budget.width_px:.0f}×{budget.height_px:.0f}px, "
            f"~{budget.chars_per_line} chars/line). "
            f"Shorten to ≤{budget.max_chars} chars.{floor_note}{hyphen_hint}"
        ),
    )]


def _rects_intersect(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    *,
    epsilon: float = 1.0,
) -> bool:
    """Return True when rectangles *a* and *b* overlap by more than *epsilon* px.

    Each rect is (x, y, width, height) in design-px. The epsilon guard
    prevents spurious hits from numerical adjacency (e.g. two boxes sharing
    exactly one edge pixel).
    """
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax + epsilon < bx + bw and bx + epsilon < ax + aw
            and ay + epsilon < by + bh and by + epsilon < ay + ah)


def check_slot_collisions(
    ctx: dict,
    *,
    slot_budgets: "dict[str, SlotBudget]",
    chrome_bboxes: list[list[float]] | None,
    slide_index: int,
) -> list[ContentDefect]:
    """Predict each bound slot's wrapped height, grow its rect, and flag
    pairwise slot/slot and slot/chrome intersections. Severity 'warn' in
    release 1 — promotion to fatal is a one-line change once the
    false-positive rate over the repo brands is known.

    Only bound slots (those with a value in *ctx*) are grown and checked.
    Unbound slots are skipped — the pack-build lint owns declared-box
    overlap analysis without content. However, declared-box overlaps
    (pack-lint territory) also fire here once both slots are bound — bound
    content makes the overlap real.

    Requires SlotBudget.x_px/y_px from the DSL 'X,Y' positional; budgets
    without coordinates anchor at the origin and will false-positive.
    """
    from feinschliff.textfit import measure_height_emu as _measure

    rects: list[tuple[str, tuple[float, float, float, float]]] = []
    for norm_path, raw_path, value in iter_slot_values(ctx):
        budget = slot_budgets.get(norm_path)
        if budget is None or not value.strip():
            continue
        if budget.autoshrink:
            # autoshrink slots render at the fitted size — predict the rect
            # the emitter actually draws, mirroring check_slot_overflow's
            # rescue.
            fitted_pt = _autoshrink_fitted_pt(value, budget)
            h_emu = _measure(
                value, font=budget.font_family, size_pt=fitted_pt,
                bold=budget.bold, width_emu=budget.width_emu,
                line_height=budget.line_height,
            )
        else:
            h_emu = _measure(
                value, font=budget.font_family, size_pt=budget.font_size_pt,
                bold=budget.bold, width_emu=budget.width_emu,
                line_height=budget.line_height,
            )
        h_px = max(budget.height_px, h_emu / budget.emu_per_px)
        rects.append((raw_path, (budget.x_px, budget.y_px, budget.width_px, h_px)))

    defects: list[ContentDefect] = []
    for i, (slot_a, rect_a) in enumerate(rects):
        for slot_b, rect_b in rects[i + 1:]:
            if _rects_intersect(rect_a, rect_b):
                defects.append(ContentDefect(
                    kind="slot-collision", slide_index=slide_index, slot=slot_a,
                    message=(f"predicted text rect of '{slot_a}' intersects "
                             f"'{slot_b}' ({rect_a[2]:.0f}x{rect_a[3]:.0f}px at "
                             f"{rect_a[0]:.0f},{rect_a[1]:.0f})"),
                    severity="warn",
                ))
    for slot_name, rect in rects:
        for bbox in chrome_bboxes or []:
            if len(bbox) == 4 and _rects_intersect(rect, tuple(map(float, bbox))):
                defects.append(ContentDefect(
                    kind="slot-collision", slide_index=slide_index, slot=slot_name,
                    message=(f"predicted text rect of '{slot_name}' overlaps baked "
                             f"chrome at {bbox[0]:.0f},{bbox[1]:.0f} "
                             f"{bbox[2]:.0f}x{bbox[3]:.0f}px"),
                    severity="warn",
                ))
    return defects


def _check_filler_words(
    so_what: str,
    *,
    slide_index: int,
) -> list[ContentDefect]:
    """Flag so_what text padded with meaningless intensifiers.

    Fires when ≥2 filler words appear. Unlike the vague-so-what check,
    a numeric anchor does NOT clear this defect — "Revenue very extremely
    grew by 12%" is still weaker than "Revenue grew 12%". Two or more
    fillers in a single sentence is the threshold for a defect signal;
    one stray filler is noise.
    """
    text = so_what.strip()
    if not text:
        return []

    tokens = [t.lower().rstrip(",.;:!?\"'") for t in text.split()]
    found = [t for t in tokens if t in _FILLER_WORDS]
    if len(found) < 2:
        return []

    return [ContentDefect(
        kind="filler-word",
        slide_index=slide_index,
        slot="so_what",
        message=(f"so_what contains {len(found)} filler word(s) that dilute "
                 f"the claim — remove or replace with specifics: "
                 f"{found!r}"),
    )]


def iter_slot_values(
    ctx: dict, prefix: str = "", raw_prefix: str = "",
) -> list[tuple[str, str, str]]:
    """Flatten *ctx* into ``(normalised_path, raw_path, str_value)`` triples.

    Walks dicts and lists recursively. The *normalised* path collapses array
    indices to ``[]`` so it matches the keys returned by
    ``compute_slot_budgets``; the *raw* path preserves the original indices
    (``cells[2].heading``) for diagnostic messages. Only string leaf values
    are emitted.
    """
    out: list[tuple[str, str, str]] = []
    if isinstance(ctx, dict):
        for k, v in ctx.items():
            norm_child = f"{prefix}.{k}" if prefix else k
            raw_child = f"{raw_prefix}.{k}" if raw_prefix else k
            out.extend(iter_slot_values(v, norm_child, raw_child))
    elif isinstance(ctx, list):
        for i, v in enumerate(ctx):
            out.extend(iter_slot_values(v, f"{prefix}[]", f"{raw_prefix}[{i}]"))
    elif isinstance(ctx, str):
        out.append((prefix, raw_prefix, ctx))
    return out


def check_unbound_must_bind_slots(
    ctx: dict,
    *,
    slot_budgets: dict,
    slide_index: int,
) -> list[ContentDefect]:
    """Flag chart slots with ``must_bind: true`` that are not bound in *ctx*.

    Each slot budget entry that carries ``must_bind: true`` represents a slot
    whose baked default data will ship verbatim unless the deck plan overrides
    it.  This is almost always wrong for chart data (stock "Q1: 8.2" values).

    Only fires for slot names whose budget dict has the ``must_bind`` key set
    to ``True`` — text slot budgets use ``chars_per_line`` / ``max_lines`` /
    ``max_chars`` and will never trigger this check.
    """
    defects: list[ContentDefect] = []
    for slot_name, budget in slot_budgets.items():
        if not isinstance(budget, dict):
            continue
        if not budget.get("must_bind"):
            continue
        # The slot is bound if ctx has a non-None, non-empty value for it.
        value = ctx.get(slot_name)
        bound = value is not None and value != "" and value != []
        if not bound:
            defects.append(ContentDefect(
                kind="unbound-must-bind-slot",
                slide_index=slide_index,
                slot=slot_name,
                message=(
                    f"slot '{slot_name}' has must_bind:true but is not bound "
                    f"in content — baked stock data will ship. "
                    f"Hint: {budget.get('hint', '')}"
                ),
                severity="fatal",
            ))
    return defects


def validate_content(
    ctx: dict,
    *,
    slide_index: int = 1,
    layout: str | None = None,
    slot_budgets: dict | None = None,
    chrome_bboxes: list | None = None,
) -> list[ContentDefect]:
    """Walk the content dict; return all defects.

    `layout` is the bare layout name (e.g. "executive-summary", with no
    path or `.slide.dsl` suffix). The structural validators
    (pyramid-arity, chunking-3-to-9) only fire when the layout is in
    their routing table; callers that don't pass a layout get the
    title-length + action-verb-leading checks only.

    `slot_budgets` is an optional dict mapping normalised slot paths to
    :class:`~feinschliff.slot_budget.SlotBudget` objects. When supplied, each string
    slot value in `ctx` is checked against its budget via
    ``check_slot_overflow``; this fires the ``slot-overflow`` defect class
    before any render budget is spent.

    `chrome_bboxes` is an optional list of ``[x, y, w, h]`` rectangles
    (design-px ints) read from the layout front-matter's ``chrome_bboxes``
    key. When supplied together with *slot_budgets*, ``check_slot_collisions``
    predicts whether any grown slot rect intersects baked chrome.
    """
    defects: list[ContentDefect] = []

    for title_slot in _TITLE_SLOT_KEYS:
        title = ctx.get(title_slot)
        if isinstance(title, str):
            defects.extend(_check_title_length(title, slide_index, slot=title_slot))

    for slot in _ACTION_SLOTS:
        items = ctx.get(slot)
        if isinstance(items, list):
            defects.extend(_check_action_verb_leading(
                items, slot_name=slot, slide_index=slide_index,
            ))

    if layout in _PYRAMID_ARITY_LAYOUTS:
        slot_name = _PYRAMID_ARITY_LAYOUTS[layout]
        items = ctx.get(slot_name)
        if isinstance(items, list):
            defects.extend(_check_pyramid_arity(
                items, slot_name=slot_name, slide_index=slide_index,
            ))

    if layout in _CHUNKING_LAYOUTS:
        slot_name = _CHUNKING_LAYOUTS[layout]
        items = ctx.get(slot_name)
        if isinstance(items, list):
            defects.extend(_check_chunking(
                items, slot_name=slot_name, slide_index=slide_index,
            ))

    if layout in _SO_WHAT_LAYOUTS:
        so_what = ctx.get("so_what")
        if isinstance(so_what, str):
            defects.extend(_check_so_what_vagueness(
                so_what, slide_index=slide_index,
            ))
            defects.extend(_check_filler_words(
                so_what, slide_index=slide_index,
            ))

    if slot_budgets:
        # Check unbound must-bind slots (chart_N_* with must_bind:true)
        # before the text-overflow checks so the fatal defect surfaces first.
        defects.extend(check_unbound_must_bind_slots(
            ctx, slot_budgets=slot_budgets, slide_index=slide_index,
        ))
        for norm_path, raw_path, value in iter_slot_values(ctx):
            budget = slot_budgets.get(norm_path)
            if budget is not None and isinstance(budget, SlotBudget):
                defects.extend(check_slot_overflow(
                    value, slot=raw_path, budget=budget, slide_index=slide_index,
                ))
        defects.extend(check_slot_collisions(
            ctx, slot_budgets=slot_budgets, chrome_bboxes=chrome_bboxes,
            slide_index=slide_index,
        ))

    return defects



def format_defects(defects_by_slide: dict[int, list[ContentDefect]]) -> str:
    """Human-readable summary for printing after content validation."""
    if not defects_by_slide:
        return "content validator: clean — no content lint defects."
    lines = [
        f"content validator: {sum(len(v) for v in defects_by_slide.values())} "
        f"defect(s) across {len(defects_by_slide)} slide(s)"
    ]
    for slide_idx in sorted(defects_by_slide):
        for d in defects_by_slide[slide_idx]:
            lines.append(f"  {d}")
    return "\n".join(lines)


def emit_defects_and_abort_message(
    defects_by_slide: dict[int, list[ContentDefect]],
    *,
    cli_name: str,
) -> None:
    """Print formatted defects + a stderr abort line.

    cli_name appears in the abort message — e.g. "build" → "feinschliff
    build: aborting — content lint failures."
    """
    print(format_defects(defects_by_slide), file=sys.stderr)
    print(f"feinschliff {cli_name}: aborting — content lint failures. "
          "Fix the content YAML and re-run.", file=sys.stderr)

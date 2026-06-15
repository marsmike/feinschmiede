# Layout picking — progressive disclosure over the brand manifest

This document replaces the "single-call to `feinschmiede.layout_picker.pick_layout`" approach for picking layouts when the brand pack ships per-layout semantic annotations (`description`, `primary_message`, `when_to_use`, `when_not_to_use`, `chrome_subject`). Today's decompiled packs (`feinschliff-builder brand describe-layouts --compact`) carry all five fields populated.

The orchestrating Claude does the picking. The CLI just gives it cheap access to the metadata, one projection at a time.

## Why progressive disclosure

A single dump of the full manifest can run 100KB+ on a 99-layout pack. That fits, but it's wasteful for every slide. Worse, it asks the model to apply five filters at once — and the rationale for any one choice gets lost in the noise.

Progressive disclosure splits the cascade into named passes, each reading **one field** across the **survivors** from the previous pass. The result is cheap (each call is 1-3 KB), the rationale is recoverable (you can replay the cascade and see why a layout was dropped), and the model never has to juggle five filters simultaneously.

## The CLI surface

All passes use `feinschliff-builder brand describe-layouts`:

```bash
# All layouts, every field — the verbose form. Use rarely (intake / debug).
feinschliff-builder brand describe-layouts --brand-pack <pack>

# All layouts, just the LLM-decision fields. Use for the first pass.
feinschliff-builder brand describe-layouts --brand-pack <pack> --compact

# Project to one field across all layouts. Use for the first triage pass.
feinschliff-builder brand describe-layouts --brand-pack <pack> \
    --fields current_primary_message

# Project to one field across the survivors of an earlier pass.
feinschliff-builder brand describe-layouts --brand-pack <pack> \
    --fields current_when_not_to_use \
    --stems slide-30,slide-83,slide-87,slide-91
```

`--stems` and `--fields` compose. `--fields` always returns `stem` as the join key so the cascade can chain.

## The cascade (per slide)

For each slide in the deck plan:

### Pass 1 — concept match (primary_message)

Fetch `current_primary_message` for every layout in the pack. Read each one. Keep the layouts whose primary message semantically aligns with this slide's intent (read from `content_plan.json` — the slide's title + first body line is a strong signal of intent).

**Heuristic — be generous here.** A 99-layout pack should yield 10-20 plausible candidates, not 2-3. Pass 2 will tighten.

### Pass 2 — anti-pattern filter (when_not_to_use)

Fetch `current_when_not_to_use` for just the Pass 1 survivors (`--stems <list>`). For each, check whether the slide's situation matches any of the disqualifying reasons. Drop those.

Common disqualifiers from real annotations:
- "no image available" — drop if the slide has no `image_query` in its plan
- "more than 4 bullets" — drop if the slide has 5+ body items
- "dense data table" — drop if the slide carries chart/table data
- "outside the framing/cover position" — drop if this slide is mid-arc

### Pass 3 — shape filter (ideal_count + slot_inventory)

Fetch `ideal_count` and `slot_inventory` for the Pass 2 survivors. Filter:

- `concept_count` (from the slide's content) must fall within `ideal_count[0]..ideal_count[1]`. Allow ±1 tolerance when the layout sits clearly above ideal.
- `slot_inventory.text_slots` must be ≥ the number of text bindings the slide wants.
- `slot_inventory.image_slots` must be ≥ the number of images the slide wants. Drop image-zero layouts if the slide has photos to bind.

### Pass 4 — variety (layout_history)

Reject any layout you've already used N times in this deck where N is the deck-level cap. Default N=2 for content-role layouts, N=1 for framing-role (cover, agenda, closer).

### Pass 5 — final affinity (optional)

For tie-breaking among the Pass 4 survivors, call the deterministic picker:

```bash
feinschliff deck pick --signals '{"role": "...", "concept_count": N, ...}' --top-k 5
```

Use it as a sanity check / rerank, not as the primary signal. The LLM-driven cascade is the authoritative pick.

## Logging — `pick_trace.md`

Every cascade decision **must** be logged so the next person (you, tomorrow) can see why a layout won. After all slides are picked, write `out/pick_trace.md` alongside the rest of the deck artifacts. Format:

```markdown
# Pick trace — <deck title>

## Slide 4 — "Performance Line CX 2026 — 100 Nm, lighter, quieter"

Intent: showcase one product capability with hero photo + 4 supporting bullets.

**Pass 1 (primary_message)** — 99 → 14 candidates
- kept: slide-04, slide-05, slide-09, slide-30, slide-37, slide-83, slide-84,
  slide-86, slide-87, slide-91, slide-92, slide-93, slide-94, slide-95
- dropped: framing-only layouts (slide-01..03), table-only (slide-13..28),
  data-comparison layouts (slide-54..66), closers (slide-99)

**Pass 2 (when_not_to_use)** — 14 → 6 candidates
- slide-84 — "no image available" → kept (we have a query)
- slide-86 — "more than 4 bullets" → DROPPED (we have 4 bullets, edge case)
- slide-91 — "outside framing position" → DROPPED (mid-arc)
- slide-92, 93, 94, 95 — "no image available" → kept (we have a query)
- slide-04, 05, 09, 30, 37, 83, 84 → kept

**Pass 3 (ideal_count + slot_inventory)** — 6 → 3 candidates
- slide-84 ideal_count [4,4], has 4 image slots → MATCH (4 bullets, 4 images)
- slide-83 ideal_count [4,4], 1 image slot → match (4 bullets, 1 image)
- slide-87 ideal_count [4,6], 5 image slots → match (overshoots image count)

**Pass 4 (variety)** — slide-84 already used twice in this deck → DROPPED
**Pass 5 (final pick)** — slide-83 wins over slide-87 because the deck plan
has only 1 image query (not 5).

→ **slide-83**
```

The trace is plain Markdown — readable by humans, easy to grep, cheap to extend. It is the only place the cascade's reasoning lives; if you don't write it, you can't learn from past picks.

## Reading the trace later

When a deck builds poorly, the first artifact to inspect is `pick_trace.md`. A miss usually surfaces as:

- Pass 1 admitted too few candidates → annotations are too narrow; the brand pack's `primary_message` needs richer phrasings
- Pass 2 dropped the right layout for the wrong reason → `when_not_to_use` is over-broad; revise the annotation
- Pass 3 admitted a layout whose chrome doesn't fit → `slot_inventory` lacks an explicit chart/table dimension the slide needed
- Pass 5 reranked away from the orchestrator's choice → the deterministic picker's heuristic signals disagree; check `picker_report.json` for the affinity breakdown

Each of those is a fixable trail — at the annotation level (brand pack edit) or the framework level (extend the CLI projection / picker signal). The trace makes the iteration loop honest.

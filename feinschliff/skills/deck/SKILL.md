---
name: deck
description: Build or polish a brand-compliant PowerPoint deck via the master-template renderer. Use when the user asks to create a deck, make a presentation, or polish a rough .pptx.
---

# deck — Feinschliff master-template deck builder

Creates / polishes / critiques presentations. The brand pack ships a `master.pptx` + `layouts.yaml` + `snippets.yaml`; this skill composes a list of `FillPlan` / `ClonePlan` objects against that catalog, then calls `feinschmiede.master_template.render`. The master is the source of styling truth — typography, brand colors, footer chrome, slide-number conventions all inherit from it.

Brand resolves: `--brand` → `FEINSCHLIFF_BRAND` → `feinschliff`.

## Quick Start

```
/deck "Q1 2026 update: 62k employees, +5.1% revenue, 40 factories"
```

See [`references/quick-start.md`](references/quick-start.md) for examples.

## Modes

- **create** — `/deck "brief"` → new deck.
- **plan** — `/deck plan "brief"` → paper draft, no render.
- **polish** — `/deck polish rough.pptx` → `--mode cosmetic` (default) preserves slide count + content, fixes chrome / typography / overflow only. See [`references/modes.md`](references/modes.md).
- **critique** — `/deck critique existing.pptx` → read-only defect analysis.

## Pipeline

`ask → intake → commit → ingest → approve → plan → ghost-deck → pick layouts → render → verify → revise`. Full step-by-step: [`references/pipeline.md`](references/pipeline.md).

**MANDATORY artifacts — every one on disk before declaring done:** `deck_brief.yaml` · `commitment.yaml` · `content_plan.json` · `ghost_deck_report.md` · `title_lint_report.md` · `plans.yaml` · `verify_report.md`. **Do NOT print "Verdict: clean" without writing `verify_report.md` to disk first.** Missing artifact → not done; run the gate.

**Render via `feinschliff render-master`** — pass `--brand-pack <path> --plans plans.yaml -o out.pptx [--theme <name>]`. The `plans.yaml` is the list of `FillPlan` / `ClonePlan` entries the planning step composes. Layouts come from `<brand-pack>/layouts.yaml`; clone snippets come from `<brand-pack>/snippets.yaml`. Both are inspectable.

**Images by default.** Any slide that can carry an image SHOULD carry one — pick a layout whose schema accepts `picture` for that placeholder. The `image_style` field in `deck_brief.yaml` (`rich-imagery` / `mixed` / `data-dense` / `concept-text` / `minimal`) governs density.

**Picker** — pick layouts directly from `layouts.yaml` by role (`cover` / `chapter` / `content` / `closing` / `agenda`) + placeholder accept-list. For bespoke designer slides, pick a snippet from `snippets.yaml` by intent and emit a `ClonePlan` with `text_replacements`. See [`references/picking.md`](references/picking.md).

## References

**Recipe:** [`references/pipeline.md`](references/pipeline.md) · [`references/picking.md`](references/picking.md) · [`references/modes.md`](references/modes.md) · [`references/quick-start.md`](references/quick-start.md) · [`references/iteration-loop.md`](references/iteration-loop.md).

**Theory:** [`references/visual-vocabulary.md`](references/visual-vocabulary.md) · [`references/content-best-practices.md`](references/content-best-practices.md) · [`references/narrative-frames.md`](references/narrative-frames.md) · [`references/audience-calibration.md`](references/audience-calibration.md) · [`references/slide-claim-test.md`](references/slide-claim-test.md) · [`references/anti-patterns.md`](references/anti-patterns.md) · [`references/design-brief-schema.md`](references/design-brief-schema.md) · [`references/speaker-notes.md`](references/speaker-notes.md) · [`references/slide-grammar.md`](references/slide-grammar.md).

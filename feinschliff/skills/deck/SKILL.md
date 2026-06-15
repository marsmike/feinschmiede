---
name: deck
description: Build or polish a brand-compliant PowerPoint deck via the v2 DSL pipeline. Use when the user asks to create a deck, make a presentation, or polish a rough .pptx.
---

# deck — Feinschliff DSL deck builder (v2)

Creates / polishes / critiques presentations via the v2 DSL pipeline.
Brand resolves: `--brand` → `FEINSCHLIFF_BRAND` → `feinschliff`.

Brand layouts are additive to the toolkit's 50 (process-flow, excalidraw-diagram, kpi-grid, charts, …). Run `feinschliff-builder brand inspect <brand>` for the full pool. See [`references/pipeline.md`](references/pipeline.md) → *Brand layout inventory*.

## Quick Start

```
/deck "Q1 2026 update: 62k employees, +5.1% revenue, 40 factories"
```

See [`references/quick-start.md`](references/quick-start.md) for examples.

## Modes

- **create** — `/deck "brief"` → new deck.
- **plan** — `/deck plan "brief"` → paper draft, no render.
- **polish** — `/deck polish rough.pptx` → `--mode cosmetic` (default) preserves slide count + content, fixes chrome / typography / overflow only; `--mode redesign` rebuilds arc + layouts + titles (`--refurbish-all` applies here). See [`references/modes.md`](references/modes.md).
- **critique** — `/deck critique existing.pptx` → read-only defect analysis.

## Pipeline

`ask → intake → commit → ingest → approve → plan → ghost-deck → pick layouts → build → verify → revise`.
Full step-by-step: [`references/pipeline.md`](references/pipeline.md).

**MANDATORY artifacts — every one must exist on disk before declaring done:** `deck_brief.yaml` · `commitment.yaml` · `content_plan.json` · `ghost_deck_report.md` · `title_lint_report.md` · `picker_report.json` · `plan.yaml` · `craft_report.md` · `verify_report.md`. **Do NOT print "Verdict: clean" without first writing `verify_report.md` to disk.** If any artifact is missing, the deck is **not done** — go back and run the missing gate.

**All gates ship in `feinschliff` core. `feinschliff-builder` is NOT required.** `deck title-lint`, `deck ghost-deck`, `deck claim-evidence`, `deck commitment-validate`, `deck storyline`, `deck verify-aspect notes-coherence`, `deck pick-deck` — these all run from the `feinschliff` venv alone. **Never tell the user "the builder is missing, so I skipped them"** — that excuse is forbidden because it is wrong. If a gate command crashes, surface the actual error; do not paper over it with a fabricated reason. Only `wireframe`, `polish redesign mode`, `book`, `verify-static`, `apply-fixes` need the builder.

**Images by default.** Any slide that can carry an image SHOULD carry one — pick a `content-with-visual`, `kpi-photo`, `chart-photo`, `picture-full`, `text-picture`, or `picture-text` layout instead of a text-only twin when the content suits it. A no-image deck is the exception (data-only, all-chart), not the norm. The `image_style` field in `deck_brief.yaml` (`rich-imagery` / `mixed` / `process-flow` / `data-dense` / `concept-text` / `minimal`) governs density.

**Picker** — for brand packs with per-layout semantic annotations, pick by progressive disclosure over the brand manifest: see [`references/picking.md`](references/picking.md). The deterministic `pick_layout` is the optional Pass 5 tie-breaker. Every cascade writes `out/pick_trace.md`. `--strict-craft` for Knaflic rules; `--strict-visual` for PIL post-render metrics. **Fan-out is the default at ≥10 slides** (`--no-fanout` to opt out).

## References

**Recipe:** [`references/pipeline.md`](references/pipeline.md) · [`references/picking.md`](references/picking.md) · [`references/modes.md`](references/modes.md) · [`references/quick-start.md`](references/quick-start.md) · [`references/iteration-loop.md`](references/iteration-loop.md). **Slot authoring rules (pgmeta, footer, slide counter):** [`references/pipeline.md`](references/pipeline.md).

**Theory:** [`references/visual-vocabulary.md`](references/visual-vocabulary.md) · [`references/content-best-practices.md`](references/content-best-practices.md) · [`references/narrative-frames.md`](references/narrative-frames.md) · [`references/audience-calibration.md`](references/audience-calibration.md) · [`references/slide-claim-test.md`](references/slide-claim-test.md) · [`references/anti-patterns.md`](references/anti-patterns.md) · [`references/design-brief-schema.md`](references/design-brief-schema.md) · [`references/speaker-notes.md`](references/speaker-notes.md) · [`references/slide-grammar.md`](references/slide-grammar.md).

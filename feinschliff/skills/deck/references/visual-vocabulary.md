# Visual Vocabulary

How to pick the right visual for a concept. This reference is generic (brand-agnostic). Brand-specific layout names come from the active brand's `<brand-root>/layouts.yaml` (the master-template catalog); see `../SKILL.md` for how the active brand resolves.

## Composition principles

These govern how elements are arranged on the canvas, regardless of which layout is chosen.

**C.R.A.P.** — the four rules of slide composition:
- **Contrast:** Make different things look different; make important things obviously important. Size, weight, colour — one element should clearly dominate.
- **Repetition:** Consistent fonts, colours, icon styles, and spacing across all slides. Visual coherence = cognitive relief.
- **Alignment:** Nothing placed arbitrarily. Every element anchors to an invisible grid. Misaligned elements read as mistakes, not choices.
- **Proximity:** Related elements cluster; unrelated elements separate. Proximity implies relationship — use it deliberately.

**Eye flow — Z-pattern vs F-pattern:**
- *Z-pattern* (for low-density, visual-first slides): the eye starts top-left, sweeps to top-right, cuts diagonally to bottom-left, then sweeps to bottom-right. Use for title slides, dividers, full-bleed visuals, and single-stat slides. Place the headline top-left and the primary visual in the sweep path.
- *F-pattern* (for text-heavier slides): the eye reads horizontally across the top, then scans down the left edge. Design for this: front-load headlines, lead key words left, let the right column recede.

**Rule of Thirds:** Divide the slide into a 3×3 grid. The four intersection points are the natural focal points ("power points"). Place charts, key numbers, and primary images at these intersections — not centred, not in corners. Centred layouts feel static; thirds feel balanced and directed.

**Chart-dominant ratio:** When a chart is the primary evidence, it should occupy 70–80% of the slide canvas. Do not shrink it to accommodate decorative elements or extra text boxes. The action title carries the verbal claim; the chart carries the visual proof.

**Full-bleed limit:** Full-bleed image slides sacrifice all functional data space. Cap them at under 10% of any deck. They work for openers, dividers, and emotional beats — not for slides that need to convey information.

## The Process

For each slide you plan to generate:
1. Identify the **concept type** (from the list below).
2. Look up **candidate visual types**.
3. Cross-reference `<brand-root>/layouts.yaml` for the brand's layouts whose placeholders accept that visual type.
4. Prefer layouts whose `role` aligns with the slide's narrative role (cover / chapter / content / closing).

## Concept → Visual-type Mapping

Based on Financial Times Visual Vocabulary (Comparison / Composition / Distribution / Relationship / Change-over-time / Quantity) extended for slides.

### Cover / opener
**Concepts:** deck cover, chapter opener, single-statement slide
**Visual types:** title-primary, title-with-visual, chapter-opener
**Layout ids (feinschliff):** title-orange, title-ink, title-picture, chapter-orange, chapter-ink, full-bleed-cover. Run `feinschliff-builder brand inspect <brand>` for each pack's actual ids.

### Agenda
**Concepts:** table-of-contents, section-list
**Visual types:** agenda
**Layout ids:** agenda

### Quantity / metrics
**Concepts:** 2-4 high-level numbers with units and change indicators
**Visual types:** data-quantity
**Layout ids:** kpi-grid

### Comparison
**Concepts:** before/after, pros/cons, product-A-vs-B, two-track plan
**Visual types:** content-columns (2)
**Layout ids:** two-column-cards
**Fallback:** bar-chart if the comparison is numeric with 2-6 items.

### Composition / parts of a whole
**Concepts:** three pillars, strategy triad, phased plan
**Visual types:** content-columns (3 or 4)
**Layout ids:** three-column, four-column-cards

### Content with supporting visual
**Concepts:** product-detail, story-beat with hero image
**Visual types:** content-with-visual
**Layout ids:** text-picture

### Voice moment
**Concepts:** quote, customer testimonial, leadership principle
**Visual types:** quote
**Layout ids:** quote

### Data comparison (ordinal or ranked)
**Concepts:** revenue by region, survey results
**Visual types:** data-comparison
**Layout ids:** bar-chart

### Diagram — architectural / conceptual / freeform
**Concepts:** diagram, flowchart, architecture overview, architectural overview, system overview, system architecture, layered system, layer diagram, concept map, mind map, block diagram, multi-element flow with callouts
**Trigger words:** if the user's brief says *"diagram"*, *"flowchart"*, *"architecture"*, *"architectural overview"*, *"system overview"*, *"layers"*, *"concept map"*, *"mind map"*, or *"show how X connects to Y"* — pick `diagram`. One rich, hand-authored Excalidraw DSL per slide, rendered + brand-themed (using the active brand pack's tokens) at build time via `slides.add_diagram()`.
**Visual types:** diagram
**Layout ids:** diagram
**Fallback:** if the content fits a parameterized template, prefer that instead — process-flow for pipelines, pyramid for hierarchy, venn for overlap, 2x2-matrix for quadrants, funnel for conversion, gantt for time-phased plans.

### Closer
**Concepts:** thank-you, deck close
**Visual types:** closer
**Layout ids:** end

## Accessibility

Accessibility rules that apply to every slide, regardless of brand pack:

**Color independence.** Never encode meaning through color alone — approximately 8% of men have color vision deficiency. Pair every color-based distinction with a secondary identifier: shape, pattern, label, directional arrow, or line style. This applies to charts (don't rely on red/green alone for good/bad), diagrams (don't use color as the only way to distinguish node types), and status indicators.

**Contrast ratios (WCAG 2.1 Level AA).** At verify time, flag slides where:
- Normal text (under 18pt) has a contrast ratio below **4.5:1** against its background.
- Large text (18pt+ or 14pt bold) has a contrast ratio below **3:1**.
- Graphical elements carrying information (chart bars, icon fills, line strokes used as data encoding) have a contrast ratio below **3:1**.

Brand packs define the palette — but placing light-brand-color text on a white background, or dark text on a dark photo, can still violate these thresholds regardless of the brand token. Check the actual rendered combination, not just the token name.

**Practical implication for slide design:** if the brand's primary color is too low-contrast for body text, use it for decorative elements and eyebrows only; fall back to near-black for all text slots.

## Layout variety — the deck-level constraint

A deck that uses the same layout on three or more consecutive content slides loses the audience's visual attention. Vary the layout even when the content type is constant:

- **Chart-heavy sections**: alternate between `bar-chart`, `line-chart`, `stacked-bar`, and `waterfall` rather than repeating `bar-chart` for every data slide.
- **Content-column sections**: cycle between `two-column-cards`, `three-column`, `horizontal-bullets`, and `vertical-bullets` rather than repeating the same card layout.
- **Break long runs with structure**: insert a `chapter-orange` or `chapter-ink` divider when three or more slides of the same layout are unavoidable — the structural break resets the eye.

The layout picker enforces variety through the `layout_history` signal: pass the list of recently-used layout IDs when calling `pick_layout` and the scorer will penalise the most recent (-0.5) and second-most-recent (-0.25) layouts to bias toward a fresh pick. Structural layouts (title slides, chapter openers, agenda, end) are exempt from this penalty since they don't rotate.

The verify step flags `layout-monotony` when three or more consecutive non-structural slides share a layout — see `iteration-loop.md` defect #27.

**Layout variety target: 3–5 distinct layout types per deck.** More than 5 distinct layouts in a single deck create their own cognitive load — the audience re-orients with every slide. Fewer than 3 signals under-planning. Aim for a core set of 3–4 layouts that recur predictably, with 1–2 special layouts for structural moments (cover, closer, quote).

## What to do when nothing fits

If no layout in the brand's pool fits, prefer the closest generic match with `when_not_to_use` that doesn't apply. If multiple layouts could fit, the tie-breaker is `role` + `when_to_use` phrasing — pick the one whose description most closely matches your content intent.

Never force content into a mismatched layout. If the user's content is genuinely unusual, run `/compile --from-html` with a single-layout HTML fragment to add a new brand-aware layout, then re-pick.

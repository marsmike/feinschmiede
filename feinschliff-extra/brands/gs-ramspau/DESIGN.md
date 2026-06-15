---
version: alpha
name: Grundschule Ramspau
description: "Schule im Grünen — German primary school brand. Wiese green + tief deep-ink + warm papier. Inherits font-size/weight/slide tokens from feinschliff; overrides palette + display font."
colors:
  accent: "#9eb05c"
  accent-hover: "#8a9c50"
  highlight: "#c5d18d"
  ink: "#1f1f1c"
  black: "#3f4b2e"
  graphite: "#9a8f86"
  steel: "#9a8f86"
  silver: "#c8c1b8"
  fog: "#dddcda"
  paper: "#f6f3ec"
  paper-2: "#ece7dc"
  off-white: "#f6f3ec"
  off-white-2: "#d9d3c5"
  rule-dark: "#34362a"
  white: "#ffffff"
typography:
  inherit: feinschliff
---
## Overview

Grundschule Ramspau ("primary school Ramspau") is a small Bavarian
elementary school whose claim is **Die Schule im Grünen** ("the school
in the green"). The brand pack ships **6 bespoke pptx layouts** that
match the school's print identity, plus everything inherited from
`feinschliff` — so a `/deck --brand gs-ramspau` invocation can still
reach for `process-flow`, `excalidraw-diagram`, `svg-infographic`,
`kpi-grid`, etc. when the brief calls for it. The bespoke layouts are
*additive*, not a replacement. Total available pool: 41 inherited +
6 brand-only = **47 layouts**.

## Colors

- **Wiese (`#9EB05C`)** is the only primary accent — used for the claim
  bar, chapter accent rules, and the "01/02/03" numerals on the agenda.
  Sparingly. Never as body text. Nudged ~5% darker than the source HTML
  reference (`#A8B86B`, which lands at 1.95:1 on `papier`) to clear the
  brand-system WCAG 2.0:1 floor for accent-on-paper.
- **Tief (`#3F4B2E`)** is the deep-ink background for chapter slides and
  the body color for display titles on light backgrounds.
- **Papier (`#F6F3EC`)** is the warm-paper canvas. Card surfaces and
  title slide backgrounds use it.
- **Taupe (`#9A8F86`)** is the only muted text color — eyebrows, mono
  tags, footer captions. Never as headline color.
- **Tinte (`#1F1F1C`)** is body text on light backgrounds.

The frontmatter `colors:` map uses the canonical Feinschliff slot names
(accent / ink / paper / etc.) so the brand validates against the shared
schema. The bespoke local names above (Wiese / Tief / Papier / Taupe /
Tinte) appear in `build_templates.py` as Python constants, since they
are the names this school uses internally and they read more naturally
in German design conversation.

## Typography

Open Sans (Google Fonts) for sans, Consolas / SF Mono fallback for the
mono register. The mono is used for eyebrow labels, agenda numbers, page
footers, and quote attribution — it carries the "school-precision" feel
without the corporate register of a tabular monospace.

The frontmatter declares `typography: {inherit: feinschliff}` because
typography tokens are not yet introduced into the schema (the v1 form
only supports `inherit: <base-brand>`). The actual font choices live in
`build_templates.py`.

## Layouts

### Bespoke (6, all 1920 × 1080)

These layouts live in `brands/gs-ramspau/layouts/` and exist only for
this brand. They cover the artefacts that show up in Elternabend /
Schulversammlung / Schulnewsletter decks and have no canonical analogue
in the toolkit pool.

1. `checkliste` — Klassen-Checkliste. Two 5-item lists with empty-square
   markers, claim-bar lockup between title and lists.
2. `leitbild` — Schul-Leitbild. Four values in a 2×2 grid with wiese
   top-accent strip, mono numero, bold title, body.
3. `statistik` — Schul-Statistik. Five horizontal bars (e.g. where
   pupils come from); width proportional to the largest value, one bar
   highlightable in wiese.
4. `stundenplan` — Stundenplan-Raster. Class schedule grid: label
   column + 5 day columns × variable; `stundenplan-cell` compound
   handles plain / accent / dark cells.
5. `team` — Lehrer-Team. Four teachers in a row, each with photo
   placeholder ("PORTRÄT" in mono caps when absent), name, role,
   contact.
6. `termine` — Termin-Liste. Chronological events; five rows via the
   `termin-row` compound, with paper-2 highlight-row treatment.

### Inherited from `feinschliff` (41)

The full toolkit pool is available — title slides, agenda, chapter
openers, kpi-grid, charts, diagrams, frameworks, governance. When the
deck picker selects e.g. `process-flow` or `excalidraw-diagram`, it
renders against the toolkit template using gs-ramspau's tokens (wiese
accent, tief ink, papier canvas, Open Sans). Inheritance is wired via
the `extends: feinschliff` frontmatter and resolved by
`lib/brand_discovery.py`.

To see the full inventory, run:

```
feinschliff brand inspect gs-ramspau
```

## Why bespoke (not baked from feinschliff)

The v2 pipeline derives tokens from hand-authored `tokens.json` (DTCG
format) rather than baking them from `DESIGN.md`. Grundschule Ramspau
differs from feinschliff in typography (Open Sans vs Noto Sans),
component vocabulary (italic claim bar, hatched photo placeholders), and
slide composition (no executive-summary, no kpi-grid, no charts).
Color-swapping feinschliff would produce slides that don't match the
school's visual identity. Authoring 8 bespoke templates via
`build_templates.py` keeps the brand pack faithful to the source design
while still validating against the DESIGN.md schema.

## License

This brand pack is included as a demo / commission example. The "Die
Schule im Grünen" wordmark and the school's logo are property of
Grundschule Ramspau. The layout system and color tokens are MIT.
